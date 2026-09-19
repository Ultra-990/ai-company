from uuid import uuid4
import pytest
from sqlalchemy import select,func
from app.models.client_portal import ClientFeedback, ClientShare
from tests.test_client_portal import project_id, issue, content
from tests.conftest import OWNER_HEADERS,WORKER_HEADERS


def setup_review(client,project_id):
    share=issue(client,project_id,milestones=[{'title':'Makieta','key':'design','status':'review','deliverable':'Udostępniona makieta v1'}]).json()
    headers={'Authorization':'Bearer '+share['token']}
    overview=client.get('/api/client/overview',headers=headers).json()
    body={'request_id':str(uuid4()),'publication_checksum':overview['publication_checksum'],'stage_index':0,'decision':'changes_requested','comment':'Proszę zwiększyć czytelność menu.','confirmed':True}
    return share,headers,body


def test_decision_replay_and_owner_reply_never_change_task_or_publication(client,task_repository,project_id):
    share,headers,body=setup_review(client,project_id)
    task=task_repository.create(title='Nie zmieniać zadania technicznego')
    before=client.get('/api/client/overview',headers=headers).json()['project']
    result=client.post('/api/client/feedback',headers=headers,json=body)
    assert result.status_code==200,result.text
    saved=result.json()
    assert saved['identity']=='access_code_not_verified_person' and not saved['replayed']
    replay=client.post('/api/client/feedback',headers=headers,json=body).json()
    assert replay['id']==saved['id'] and replay['replayed']
    assert client.post('/api/client/feedback',headers=headers,json=body|{'comment':'Zmienione uwagi'}).status_code==409
    assert client.post('/api/client/feedback',headers=headers,json=body|{'request_id':str(uuid4())}).status_code==409
    ack=f'/api/client-feedback/{saved["id"]}/acknowledge'
    assert client.post(ack,headers=headers,json={'reply':'Nie może wykonać tego klient'}).status_code==401
    assert client.post(ack,headers=WORKER_HEADERS,json={'reply':'Nie może wykonać tego agent'}).status_code==403
    assert client.post(ack,headers=OWNER_HEADERS,json={'reply':'Otrzymałem uwagi. Przygotuję nową wersję.'}).status_code==200
    assert client.post(ack,headers=OWNER_HEADERS,json={'reply':'Otrzymałem uwagi. Przygotuję nową wersję.'}).status_code==200
    assert client.post(ack,headers=OWNER_HEADERS,json={'reply':'Nadpisanie'}).status_code==409
    overview=client.get('/api/client/overview',headers=headers).json()
    assert overview['project']==before and overview['client_decisions'][0]['acknowledged_at']
    assert task_repository.get(task.id).progress==0
    assert task_repository.get(task.id).status==task.status
    with task_repository._session_factory() as s:
        assert s.scalar(select(func.count()).select_from(ClientFeedback))==1
    history=client.get('/api/client/feedback',headers=headers).json()
    assert history['feedback'][0]['stage_snapshot']['deliverable']=='Udostępniona makieta v1'
    assert 'share_id' not in history['feedback'][0] and 'token' not in str(history)


def test_changed_publication_stale_submission_and_repeat_after_republication(client,project_id):
    share,headers,body=setup_review(client,project_id)
    assert client.post('/api/client/feedback',headers=headers,json=body).status_code==200
    updated=content()|{'milestones':[{'title':'Makieta v2','status':'review','deliverable':'Poprawiona makieta'}]}
    assert client.put(f'/api/client-shares/{share["id"]}',headers=OWNER_HEADERS,json=updated).status_code==200
    fresh=client.get('/api/client/overview',headers=headers).json()
    assert fresh['client_decisions']==[] and fresh['publication_checksum']!=body['publication_checksum']
    assert client.post('/api/client/feedback',headers=headers,json=body|{'request_id':str(uuid4())}).status_code==409
    assert client.post('/api/client/feedback',headers=headers,json=body).json()['replayed']
    assert client.post('/api/client/feedback',headers=headers,json=body|{'request_id':str(uuid4()),'publication_checksum':fresh['publication_checksum'],'decision':'accepted'}).status_code==200
    history=client.get('/api/client/feedback',headers=headers).json()
    assert len(history['feedback'])==2
    assert client.get(f'/api/client/feedback?before={history["feedback"][0]["id"]}',headers=headers).json()['feedback'][0]['stage_title']=='Makieta'


@pytest.mark.parametrize('change,status',[
    ({'confirmed':False},422),({'confirmed':'true'},422),({'comment':' '},422),({'comment':'x'*4001},422),
    ({'comment':'a\x00b'},422),({'stage_index':True},422),({'stage_index':1},422),
    ({'decision':'completed'},422),({'share_id':2},422),({'publication_checksum':'0'*64},409),
])
def test_bad_decisions_rejected(client,project_id,change,status):
    _,headers,body=setup_review(client,project_id)
    assert client.post('/api/client/feedback',headers=headers,json=body|change).status_code==status


def test_only_review_stage_can_be_decided_and_empty_result_cannot_be_accepted(client,project_id):
    share,headers,body=setup_review(client,project_id)
    for state,decision,expected in [('planned','changes_requested',409),('completed','accepted',409),('review','accepted',409),('review','changes_requested',200)]:
        updated=content()|{'milestones':[{'title':'Etap','status':state}]}
        client.put(f'/api/client-shares/{share["id"]}',headers=OWNER_HEADERS,json=updated)
        checksum=client.get('/api/client/overview',headers=headers).json()['publication_checksum']
        assert client.post('/api/client/feedback',headers=headers,json=body|{'request_id':str(uuid4()),'decision':decision,'publication_checksum':checksum}).status_code==expected


def test_access_scopes_revocation_and_separate_client_surface(client,project_id):
    from fastapi.testclient import TestClient
    from app.client_main import app as portal
    from app.main import app as internal
    from app.api.organization_os import get_organization_session
    share,headers,body=setup_review(client,project_id)
    other=issue(client,project_id).json();other_headers={'Authorization':'Bearer '+other['token']}
    for h in ({},OWNER_HEADERS,WORKER_HEADERS):
        assert client.post('/api/client/feedback',headers=h,json=body).status_code==401
    assert client.post('/api/client/feedback',headers=other_headers,json=body).status_code==409
    portal.dependency_overrides[get_organization_session]=internal.dependency_overrides[get_organization_session]
    try:
        with TestClient(portal) as p:
            assert p.post('/api/client/feedback',headers=headers,json=body).status_code==200
            assert p.get('/api/client/feedback',headers=headers).status_code==200
            assert p.get('/os/client-preview').status_code==404
            assert p.get(f'/api/client-shares/{share["id"]}/feedback',headers=headers).status_code==404
    finally: portal.dependency_overrides.clear()
    assert client.get('/api/client/feedback',headers=other_headers).json()['feedback']==[]
    assert client.get(f'/api/client-shares/{share["id"]}/feedback',headers=OWNER_HEADERS).status_code==200
    client.post(f'/api/client-shares/{share["id"]}/revoke',headers=OWNER_HEADERS)
    assert client.post('/api/client/feedback',headers=headers,json=body).status_code==401
    assert client.get('/api/client/feedback',headers=headers).status_code==401


def test_owner_preview_shell_and_spatial_shortcuts(client):
    page=client.get('/os/client-preview')
    assert page.status_code==200 and 'data-owner-preview="true"' in page.text
    spatial=client.get('/os/spatial').text
    assert 'href="/os/clients"' in spatial and 'href="/os/client-preview"' in spatial
