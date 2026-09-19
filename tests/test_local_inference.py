from uuid import uuid4
import pytest
from sqlalchemy import select, func
from app.api.local_inference import get_provider_factory, get_idle_check
from app.main import app
from app.models.local_inference import LocalInference
from app.models.task import Task, TaskAttempt, TaskStatus
from app.services import local_inference as service
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS
from tests.test_agent_packets import assigned, packet

CONFIG={'enabled':True,'model':'qwen3.8:27b','digest':'a'*64,'timeout_seconds':30,'num_ctx':8192,'num_predict':512,'num_thread':2}


@pytest.fixture(autouse=True)
def config_and_no_network(monkeypatch):
    monkeypatch.setattr(service,'enabled_config',lambda:dict(CONFIG))
    class Provider:
        calls=0
        def __init__(self,config):pass
        def complete(self,messages):
            Provider.calls+=1
            content='Wynik kontrolowanej atrapy. Nie wykonywano testów produktu.'
            if 'upwork-scope.v1' in messages[0]['content']:
                import json
                content=json.dumps({'fit':'CLARIFY','reason':'Wynik kontrolowanej atrapy, nie wykonano testów.',
                    'questions':['Jaka waluta?'],'scope':['Kalkulator'],'acceptance_cases':['8 * 322 = 2576'],'exclusions':['Hosting']})
            return {'content':content,
                    'model':CONFIG['model'],'digest':CONFIG['digest'],'done_reason':'stop',
                    'elapsed_seconds':.1,'eval_count':12,'prompt_eval_count':30}
    app.dependency_overrides[get_provider_factory]=lambda:Provider
    app.dependency_overrides[get_idle_check]=lambda:lambda:None
    yield Provider
    app.dependency_overrides.pop(get_provider_factory,None)
    app.dependency_overrides.pop(get_idle_check,None)


def enqueue(client):
    task=assigned(client)['tasks'][0]['id'];p=packet(client,task)
    body={'request_id':str(uuid4()),'task_id':task,'packet_id':p['packet_id'],'packet_checksum':p['checksum']}
    r=client.post('/api/local-inference',headers=OWNER_HEADERS,json=body)
    assert r.status_code==200,r.text
    return r.json(),body


def test_real_flow_creates_review_not_completion(client,task_repository,config_and_no_network):
    run,body=enqueue(client)
    assert run['state']=='queued' and not run['model_request_started']
    assert client.post('/api/local-inference',headers=OWNER_HEADERS,json=body).json()==run
    result=client.post(f"/api/local-inference/{run['id']}/run",headers=OWNER_HEADERS)
    assert result.status_code==200,result.text
    data=result.json();assert data['state']=='awaiting_review' and data['attempt_id']
    assert client.post(f"/api/local-inference/{run['id']}/run",headers=OWNER_HEADERS).json()==data
    assert config_and_no_network.calls==1
    with task_repository._session_factory() as s:
        task=s.get(Task,body['task_id']);attempt=s.get(TaskAttempt,data['attempt_id'])
        assert task.status==TaskStatus.IN_PROGRESS and task.progress==0 and task.queued_at is None
        assert attempt.status=='awaiting_review' and attempt.verification_status=='pending'
        assert attempt.worker_id=='local-ollama'
        assert attempt.result_checksum==data['result_checksum']
        assert s.scalar(select(func.count()).select_from(TaskAttempt))==1
    assert client.get('/api/local-inference',headers=OWNER_HEADERS).json()['runs'][0]['id']==run['id']


def test_comfy_slot_blocks_qwen_and_qwen_slot_blocks_comfy(client, task_repository, config_and_no_network, monkeypatch):
    from app.models.media_generation import MediaGeneration
    from app.services import media_generation
    from tests.test_media_generation import Provider
    run, body = enqueue(client)
    with task_repository._session_factory() as s:
        media = MediaGeneration(request_id=str(uuid4()), task_id=body['task_id'], prompt_id=str(uuid4()),
            state='uncertain', inputs={}, context_checksum='a'*64, workflow_checksum='b'*64)
        s.add(media); s.commit(); media_id = media.id
    assert client.post(f"/api/local-inference/{run['id']}/run", headers=OWNER_HEADERS).status_code == 409
    assert config_and_no_network.calls == 0
    with task_repository._session_factory() as s:
        s.get(MediaGeneration, media_id).state = 'failed'
        from app.models.task import ApprovalStatus
        s.get(Task, body['task_id']).approval_status = ApprovalStatus.APPROVED
        s.get(LocalInference, run['id']).state = 'running'; s.commit()
    monkeypatch.setattr(media_generation, 'assert_enabled', lambda: None)
    provider = Provider()
    with task_repository._session_factory() as s:
        with pytest.raises(ValueError, match='Slot lokalnego'):
            media_generation.submit(s, body['task_id'], str(uuid4()), 'Blue sphere', 42, provider)
        s.rollback()
    assert provider.calls == 0


def test_auth_cancel_and_no_unexpected_controls(client,config_and_no_network):
    run,body=enqueue(client)
    for headers,status in (({},401),(WORKER_HEADERS,403)):
        assert client.get('/api/local-inference',headers=headers).status_code==status
        assert client.post('/api/local-inference',json=body,headers=headers).status_code==status
        assert client.post(f"/api/local-inference/{run['id']}/run",headers=headers).status_code==status
    assert client.post('/api/local-inference',json=body|{'base_url':'https://example.com'},headers=OWNER_HEADERS).status_code==422
    cancelled=client.post(f"/api/local-inference/{run['id']}/cancel",headers=OWNER_HEADERS)
    assert cancelled.json()['state']=='cancelled'
    assert client.post(f"/api/local-inference/{run['id']}/run",headers=OWNER_HEADERS).json()['state']=='cancelled'
    assert config_and_no_network.calls==0


@pytest.mark.parametrize('error',[TimeoutError('private'),ValueError('private'),None])
def test_failure_never_completes_or_retries(client,task_repository,error):
    run,body=enqueue(client)
    class Bad:
        def __init__(self,c):pass
        def complete(self,m):
            if error:raise error
            return {'content':'','model':CONFIG['model'],'digest':CONFIG['digest'],'done_reason':'length'}
    with task_repository._session_factory() as s:
        result=service.execute(s,run['id'],Bad)
        assert result['state']==('uncertain' if error else 'failed') and result['attempt_id'] is None
        assert 'private' not in str(result)
        assert s.get(Task,body['task_id']).status==TaskStatus.PENDING
        s.rollback()
        assert service.execute(s,run['id'],Bad)['state']==result['state']


def test_single_slot_and_stale_response(client,task_repository):
    first,body=enqueue(client);second,_=enqueue(client)
    class Changing:
        def __init__(self,c):pass
        def complete(self,m):
            with task_repository._session_factory() as other:
                with pytest.raises(ValueError,match='już wykonywany'):
                    service.execute(other,second['id'],Changing)
            with task_repository._session_factory() as other:
                other.get(Task,body['task_id']).title='Zmieniony zakres';other.commit()
            return {'content':'Nie zapisywać','model':CONFIG['model'],'digest':CONFIG['digest'],'done_reason':'stop'}
    with task_repository._session_factory() as s:
        result=service.execute(s,first['id'],Changing)
        assert result['state']=='stale' and result['attempt_id'] is None
        assert s.scalar(select(func.count()).select_from(TaskAttempt))==0


def test_gate_and_context_limit(client,monkeypatch):
    task=assigned(client)['tasks'][0]['id'];p=packet(client,task)
    body={'request_id':str(uuid4()),'task_id':task,'packet_id':p['packet_id'],'packet_checksum':p['checksum']}
    monkeypatch.setattr(service,'enabled_config',lambda:dict(CONFIG,num_ctx=512))
    assert client.post('/api/local-inference',headers=OWNER_HEADERS,json=body).status_code==409
    def disabled():raise ValueError('Wyłączone')
    monkeypatch.setattr(service,'enabled_config',disabled)
    assert client.post('/api/local-inference',headers=OWNER_HEADERS,json=body).status_code==409


def test_explicit_retry_preserves_history_and_is_idempotent(client,task_repository,config_and_no_network):
    run,_=enqueue(client)
    with task_repository._session_factory() as s:
        row=s.get(LocalInference,run['id']);row.state='failed';row.error_code='truncated_output';s.commit()
    path=f"/api/local-inference/{run['id']}/retry"
    body={'request_id':str(uuid4()),'confirm':True}
    assert client.post(path,headers=WORKER_HEADERS,json=body).status_code==403
    assert client.post(path,headers=OWNER_HEADERS,json=body|{'confirm':False}).status_code==422
    def busy():raise ValueError('Ollama zajęta')
    app.dependency_overrides[get_idle_check]=lambda:busy
    assert client.post(path,headers=OWNER_HEADERS,json=body).status_code==409
    app.dependency_overrides[get_idle_check]=lambda:lambda:None
    result=client.post(path,headers=OWNER_HEADERS,json=body)
    assert result.status_code==200,result.text
    assert result.json()['state']=='queued' and config_and_no_network.calls==0
    assert client.post(path,headers=OWNER_HEADERS,json=body).json()==result.json()
    ready=client.post(f"/api/local-inference/{run['id']}/run",headers=OWNER_HEADERS).json()
    assert ready['state']=='awaiting_review'
    assert ready['metrics']['retry_history'][0]['error_code']=='truncated_output'
    assert client.post(path,headers=OWNER_HEADERS,json=body|{'request_id':str(uuid4())}).status_code==409


def test_retry_limit_and_uncertain_slot(client,task_repository):
    first,_=enqueue(client);second,_=enqueue(client)
    with task_repository._session_factory() as s:
        row=s.get(LocalInference,first['id']);row.state='uncertain';s.commit()
        with pytest.raises(ValueError,match='już wykonywany'):
            service.execute(s,second['id'],lambda c:None)
        for _ in range(2):
            service.requeue(s,first['id'],str(uuid4()));s.commit()
            row.state='failed';s.commit()
        with pytest.raises(ValueError,match='Limit trzech'):
            service.requeue(s,first['id'],str(uuid4()))


def test_crash_recovery_requires_deadline_and_idle_confirmation(client,task_repository):
    from datetime import timedelta
    from app.models.task import utc_now
    run,_=enqueue(client)
    with task_repository._session_factory() as s:
        row=s.get(LocalInference,run['id']);row.state='running';row.started_at=utc_now();s.commit()
    path=f"/api/local-inference/{run['id']}/retry";body={'request_id':str(uuid4()),'confirm':True}
    assert client.post(path,headers=OWNER_HEADERS,json=body).status_code==409
    with task_repository._session_factory() as s:
        s.get(LocalInference,run['id']).started_at=utc_now()-timedelta(seconds=60);s.commit()
    result=client.post(path,headers=OWNER_HEADERS,json=body)
    assert result.status_code==200 and result.json()['state']=='queued'
    assert result.json()['metrics']['retry_history'][0]['state']=='running'


def test_late_old_transport_cannot_finish_new_execution(client,task_repository):
    run,_=enqueue(client)
    class Late:
        def __init__(self,c):pass
        def complete(self,m):
            with task_repository._session_factory() as other:
                row=other.get(LocalInference,run['id'])
                row.metrics={'execution_token':'newer-execution'};other.commit()
            return {'content':'Stary wynik','model':CONFIG['model'],'digest':CONFIG['digest'],'done_reason':'stop'}
    with task_repository._session_factory() as s:
        with pytest.raises(ValueError,match='Stan wykonania zmienił się'):
            service.execute(s,run['id'],Late)
        assert s.scalar(select(func.count()).select_from(TaskAttempt))==0
        assert s.get(LocalInference,run['id']).state=='running'
