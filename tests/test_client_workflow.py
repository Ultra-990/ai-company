import json
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, func

from app.models.client_portal import ClientShare, ClientActivity, ClientPublicationRevision
from tests.test_client_portal import project_id, content, issue
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS


def workflow():
    return [{"key":"scope", "title":"Zakres", "status":"completed", "description":"Ustalenie odbiorców",
             "deliverable":"Specyfikacja — wersja 1", "acceptance_criteria":["Potwierdzony zakres"], "review_note":"Uzgodniono"},
            {"key":"build", "title":"Budowa", "status":"in_progress", "description":"Powstają widoki"}]


def access(client, share):
    headers={"Authorization":"Bearer "+share['token']}
    return headers, client.get('/api/client/overview', headers=headers).json()


def test_workflow_fields_are_explicitly_published_and_legacy_snapshots_still_work(client, task_repository, project_id):
    share=issue(client,project_id,milestones=workflow()).json()
    headers,data=access(client,share)
    assert data['project']['milestones'][0]['deliverable']=='Specyfikacja — wersja 1'
    assert 'INTERNAL' not in json.dumps(data)
    assert client.get(f'/api/client-shares/{share["id"]}',headers=headers).status_code==401
    owner=client.get(f'/api/client-shares/{share["id"]}',headers=OWNER_HEADERS)
    assert owner.status_code==200 and 'token' not in owner.text
    with task_repository._session_factory() as s:
        record=s.get(ClientShare,share['id']);record.public_content=json.dumps(content());s.commit()
    legacy=client.get('/api/client/overview',headers=headers).json()
    assert legacy['project']['milestones'][0]['deliverable']==''


@pytest.mark.parametrize('stages',[
    [{'title':'X','key':'same'},{'title':'Y','key':'same'}],
    [{'title':'X','key':'/private'}],
    [{'title':'X','deliverable':'x'*6001}],
    [{'title':'X','acceptance_criteria':[''] }],
    [{'title':'X','acceptance_criteria':[' '] }],
    [{'title':'X','acceptance_criteria':['x']*13}],
    [{'title':'X','internal_task_id':1}],
    [{'title':'X','html':'<script>bad()</script>'}],
])
def test_bad_workflow_rejected(client,project_id,stages):
    assert issue(client,project_id,milestones=stages).status_code==422


def test_versions_persist_and_revoke_is_idempotent(client,task_repository,project_id):
    share=issue(client,project_id,milestones=workflow()).json();path=f'/api/client-shares/{share["id"]}'
    assert client.put(path,headers=OWNER_HEADERS,json=content('Nowa wersja')).status_code==200
    assert client.post(path+'/revoke',headers=OWNER_HEADERS).status_code==200
    assert client.post(path+'/revoke',headers=OWNER_HEADERS).status_code==200
    history=client.get(path+'/history',headers=OWNER_HEADERS)
    assert history.status_code==200 and history.headers['cache-control']=='no-store'
    data=history.json()
    assert [r['kind'] for r in data['revisions']]==['revoked','updated','created']
    assert data['revisions'][-1]['project']['milestones'][0]['deliverable']=='Specyfikacja — wersja 1'
    assert 'token' not in history.text
    with task_repository._session_factory() as s:
        assert s.scalar(select(func.count()).select_from(ClientActivity))==0
    older=client.get(path+f'/history?before_revision={data["revisions"][1]["id"]}',headers=OWNER_HEADERS).json()
    assert [r['kind'] for r in older['revisions']]==['created']
    index=client.get('/api/client-history',headers=OWNER_HEADERS).json()
    assert index['shares'][0]['revoked'] and index['shares'][0]['last_activity_at'] is None


def test_old_publication_gets_baseline_not_invented_history(client,task_repository,project_id):
    with task_repository._session_factory() as s:
        row=ClientShare(project_id=project_id,token_digest='a'*64,public_content=json.dumps(content()),expires_at=datetime.now(timezone.utc)+timedelta(days=1))
        s.add(row);s.commit();id_=row.id
    assert client.get(f'/api/client-shares/{id_}/history',headers=OWNER_HEADERS).json()['revisions']==[]
    assert client.put(f'/api/client-shares/{id_}',headers=OWNER_HEADERS,json=content('Aktualizacja')).status_code==200
    result=client.get(f'/api/client-shares/{id_}/history',headers=OWNER_HEADERS).json()
    assert [r['kind'] for r in result['revisions']]==['updated','baseline']
    assert result['revisions'][1]['project']['title']==content()['title']


def test_activity_requires_valid_access_and_binds_stage_to_published_version(client,task_repository,project_id):
    share=issue(client,project_id,milestones=workflow()).json();headers,data=access(client,share)
    payload={'kind':'view_stage','stage_index':1,'publication_updated_at':data['updated_at']}
    for h in ({},OWNER_HEADERS,WORKER_HEADERS):
        assert client.post('/api/client/activity',headers=h,json=payload).status_code==401
    assert client.post('/api/client/activity',headers=headers,json=payload|{'stage_index':29}).status_code==422
    assert client.post('/api/client/activity',headers=headers,json=payload|{'text':'DO NOT LOG'}).status_code==422
    assert client.post('/api/client/activity',headers=headers,json=payload|{'kind':'view_materials'}).status_code==422
    assert client.post('/api/client/activity',headers=headers,json=payload|{'publication_updated_at':'2000-01-01T00:00:00Z'}).status_code==409
    assert client.post('/api/client/activity',headers=headers,json=payload).json()=={'recorded':True}
    assert client.post('/api/client/activity',headers=headers,json=payload).json()['recorded'] is False
    history=client.get(f'/api/client-shares/{share["id"]}/history',headers=OWNER_HEADERS).json()
    assert len(history['activities'])==1 and history['activities'][0]['stage_title']=='Budowa'
    assert history['activity_identity']=='access_code_not_verified_person'
    # A read/poll never logs activity. An event does not complete or accept a task.
    access(client,share);access(client,share)
    with task_repository._session_factory() as s:
        assert s.scalar(select(func.count()).select_from(ClientActivity))==1
        a=s.scalar(select(ClientActivity));a.created_at=datetime.now(timezone.utc)-timedelta(seconds=5);s.commit()
    assert client.post('/api/client/activity',headers=headers,json=payload|{'kind':'view_materials','stage_index':None}).json()['recorded']
    assert client.post(f'/api/client-shares/{share["id"]}/revoke',headers=OWNER_HEADERS).status_code==200
    assert client.post('/api/client/activity',headers=headers,json=payload).status_code==401


def test_activity_is_never_selected_by_client_supplied_share_id(client,project_id):
    a=issue(client,project_id,title='A',milestones=workflow()).json();b=issue(client,project_id,title='B').json()
    headers,data=access(client,a)
    payload={'kind':'open_project','publication_updated_at':data['updated_at']}
    assert client.post('/api/client/activity',headers=headers,json=payload|{'share_id':b['id']}).status_code==422
    assert client.post(f'/api/client/activity?share_id={b["id"]}',headers=headers,json=payload).json()['recorded']
    assert client.get(f'/api/client-shares/{b["id"]}/history',headers=OWNER_HEADERS).json()['activities']==[]
    for path in ('/api/client-history',f'/api/client-shares/{a["id"]}/history'):
        for h,status in (({},401),(WORKER_HEADERS,403),(headers,401)):
            assert client.get(path,headers=h).status_code==status


def test_owner_shell_and_navigation(client):
    page=client.get('/os/clients')
    assert page.status_code==200 and 'history-projects' in page.text
    assert 'INTERNAL' not in page.text
    assert '/os/clients' in client.get('/os/work').text
    assert 'client-stage-menu' in client.get('/client').text


def test_history_is_paginated_and_activity_storage_bounded(client,task_repository,project_id):
    share=issue(client,project_id).json();headers,data=access(client,share)
    with task_repository._session_factory() as s:
        old=datetime.now(timezone.utc)-timedelta(minutes=5)
        for _ in range(1000):
            s.add(ClientActivity(share_id=share['id'],kind='view_workflow',publication_updated_at=old,created_at=old))
        s.commit()
    assert client.post('/api/client/activity',headers=headers,json={'kind':'view_reviews','publication_updated_at':data['updated_at']}).json()['recorded']
    with task_repository._session_factory() as s:
        assert s.scalar(select(func.count()).select_from(ClientActivity))==1000
    path=f'/api/client-shares/{share["id"]}/history'
    page=client.get(path,headers=OWNER_HEADERS).json()
    assert len(page['activities'])==50 and page['next_activity']
    next_page=client.get(path+f'?before_activity={page["next_activity"]}',headers=OWNER_HEADERS).json()
    assert not {a['id'] for a in page['activities']} & {a['id'] for a in next_page['activities']}


def test_publication_and_history_write_roll_back_together(client,task_repository,project_id,monkeypatch):
    from app.api import client_portal
    from sqlalchemy.exc import SQLAlchemyError
    from fastapi import HTTPException
    share=issue(client,project_id).json()
    def fail_commit(session):
        session.rollback()
        raise HTTPException(503,'Simulated storage failure')
    monkeypatch.setattr(client_portal,'commit',fail_commit)
    assert client.put(f'/api/client-shares/{share["id"]}',headers=OWNER_HEADERS,json=content('Must not persist')).status_code==503
    with task_repository._session_factory() as s:
        assert 'Must not persist' not in s.get(ClientShare,share['id']).public_content
        assert s.scalar(select(func.count()).select_from(ClientPublicationRevision))==1
