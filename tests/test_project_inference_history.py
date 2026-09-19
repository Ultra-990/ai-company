from uuid import uuid4

from app.models.artifact import Artifact
from app.models.local_inference import LocalInference
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS
from tests.test_agent_packets import assigned


def seed_runs(session, saved, states):
    ids=[]
    for state in states:
        task_id=saved['tasks'][0]['id']
        artifact=Artifact(task_id=task_id,project_id=saved['project_id'],name='synthetic-history-packet')
        session.add(artifact);session.flush()
        run=LocalInference(request_id=str(uuid4()),task_id=task_id,packet_id=artifact.id,
                           packet_checksum='a'*64,state=state,model='test-only',model_digest='a'*64,
                           limits={},metrics={})
        session.add(run);session.flush();ids.append(run.id)
    session.commit()
    return ids


def test_history_is_project_scoped_paginated_and_keeps_old_uncertain_visible(client,task_repository):
    one,two=assigned(client),assigned(client)
    with task_repository._session_factory() as session:
        ids=seed_runs(session,one,['uncertain']+['failed']*31)
        foreign=seed_runs(session,two,['running'])
    path=f"/api/local-inference?project_id={one['project_id']}"
    response=client.get(path,headers=OWNER_HEADERS)
    assert response.status_code==200
    assert response.headers['cache-control']=='no-store'
    page=response.json()
    assert page['attention_count']==1
    assert [r['id'] for r in page['runs']]==list(reversed(ids[-30:]))
    assert not set(foreign)&{r['id'] for r in page['runs']}
    older=client.get(path+f"&before={page['next_cursor']}",headers=OWNER_HEADERS).json()
    assert [r['id'] for r in older['runs']]==list(reversed(ids[:2]))
    assert older['next_cursor'] is None
    attention=client.get(path+'&attention_only=true',headers=OWNER_HEADERS).json()
    assert [r['id'] for r in attention['runs']]==[ids[0]]
    assert attention['next_cursor'] is None
    with task_repository._session_factory() as session:
        assert session.get(LocalInference,ids[0]).state=='uncertain'
        assert session.get(LocalInference,foreign[0]).state=='running'


def test_history_authorization_and_filter_validation(client):
    for headers,status in (({},401),(WORKER_HEADERS,403)):
        assert client.get('/api/local-inference?project_id=1',headers=headers).status_code==status
    for query in ('project_id=0','before=-1','attention_only=maybe'):
        assert client.get('/api/local-inference?'+query,headers=OWNER_HEADERS).status_code==422
    assert client.get('/api/local-inference?project_id=999999',headers=OWNER_HEADERS).status_code==404
