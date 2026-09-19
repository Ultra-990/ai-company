from uuid import uuid4
import os
import json
from pathlib import Path

import pytest
from sqlalchemy import select, func

from app.models.work_order import WorkOrder
from app.models.local_inference import LocalInference
from app.models.task import Task, TaskAttempt
from app.models.delegation import TaskDelegation
from app.services import local_inference
from app.services.agent_packets import export_prompt
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS
from tests.test_local_inference import config_and_no_network


def payload():
    return dict(request_id=str(uuid4()), title='Kalkulator kosztu pracy',
                job_text='Build a simple calculator: enter hours and hourly rate to calculate the total. No accounts or external services.',
                source_url='https://www.upwork.com/jobs/example', notes='Bez hostingu.',
                acceptance_criteria=['8 godzin przy stawce 322 daje 2576.', 'Odrzuć ujemne wartości.'])


def create(client, data=None):
    r=client.post('/api/upwork-orders', json=data or payload(), headers=OWNER_HEADERS)
    assert r.status_code in (200,201), r.text
    return r.json()


def test_intake_replay_and_same_existing_workflow(client, task_repository):
    data=payload(); order=create(client,data); replay=create(client,data)
    assert replay==order
    assert order['analysis'] is None and not order['platform_connected'] and not order['contract_accepted']
    assert len(order['tasks'])==4 and all(t['status']=='pending' and t['progress']==0 for t in order['tasks'])
    assert all(t['delegation'] is None and not t['queued'] for t in order['tasks'])
    assert order['brief']['upwork_intake']['job_text']==data['job_text']
    assert client.get('/api/work-orders',headers=OWNER_HEADERS).json()['orders'][0]['project_id']==order['project_id']
    assert client.get(order['work_url'],headers=OWNER_HEADERS).status_code==200
    assert client.post('/api/upwork-orders',json=data|{'notes':'Inny zakres'},headers=OWNER_HEADERS).status_code==409
    with task_repository._session_factory() as s:
        assert s.scalar(select(func.count()).select_from(WorkOrder))==1
        assert s.scalar(select(func.count()).select_from(LocalInference))==0
        assert s.scalar(select(func.count()).select_from(TaskAttempt))==0


def test_qwen_analysis_once_and_review_gate(client, task_repository, config_and_no_network, monkeypatch):
    # Local model replaced by a deterministic provider; no inference/network here.
    configurations=[]
    monkeypatch.setattr(config_and_no_network,'__init__',lambda self,config:configurations.append(config))
    order=create(client); path=f"/api/upwork-orders/{order['project_id']}/analysis"
    run=client.post(path,headers=OWNER_HEADERS)
    assert run.status_code==200,run.text
    queued=run.json(); assert queued['state']=='queued' and not queued['model_request_started']
    assert client.post(path,headers=OWNER_HEADERS).json()==queued
    with task_repository._session_factory() as s:
        prompt=export_prompt(s,queued['task_id'],queued['packet_id'])
        content='\n'.join(m['content'] for m in prompt['messages'])
        assert 'SUPPORTED / CLARIFY / UNSUPPORTED' in content
        assert 'Bez pip' in content and 'nie zmianą uprawnień' in content
        assert s.scalar(select(func.count()).select_from(TaskDelegation))==4
    result=client.post(f"/api/local-inference/{queued['id']}/run",headers=OWNER_HEADERS)
    assert result.status_code==200,result.text
    assert result.json()['state']=='awaiting_review'
    assert client.post(path,headers=OWNER_HEADERS).json()['state']=='awaiting_review'
    client.post(f"/api/local-inference/{queued['id']}/run",headers=OWNER_HEADERS)
    assert config_and_no_network.calls==1
    from app.services.upwork_scope import ScopeResult
    assert configurations[0]['format']==ScopeResult.model_json_schema()
    assert queued['limits']['scope_decoder']=='json-schema.v1'
    saved=client.get(f"/api/upwork-orders/{order['project_id']}",headers=OWNER_HEADERS).json()
    assert saved['analysis']['result_content']==result.json()['result_content']
    assert saved['tasks'][0]['progress']==0 and saved['tasks'][0]['status']=='in_progress'
    builder=saved['tasks'][1]
    assert builder['delegation']['planning_blockers']
    assert client.post(f"/api/tasks/{builder['id']}/agent-packet",headers=OWNER_HEADERS).status_code==409


def test_old_decoder_requires_explicit_new_run(client,task_repository,config_and_no_network):
    order=create(client)
    run=client.post(f"/api/upwork-orders/{order['project_id']}/analysis",headers=OWNER_HEADERS).json()
    with task_repository._session_factory() as s:
        saved=s.get(LocalInference,run['id'])
        saved.limits={k:v for k,v in saved.limits.items() if k!='scope_decoder'}
        s.commit()
    result=client.post(f"/api/local-inference/{run['id']}/run",headers=OWNER_HEADERS).json()
    assert result['state']=='stale' and result['error_code']=='configuration_changed'
    assert config_and_no_network.calls==0


def test_disabled_model_rolls_back_delegation_not_saved_order(client,task_repository,monkeypatch):
    order=create(client)
    def disabled():raise ValueError('Emergency Stop')
    monkeypatch.setattr(local_inference,'enabled_config',disabled)
    r=client.post(f"/api/upwork-orders/{order['project_id']}/analysis",headers=OWNER_HEADERS)
    assert r.status_code==409
    with task_repository._session_factory() as s:
        assert s.scalar(select(func.count()).select_from(WorkOrder))==1
        assert s.scalar(select(func.count()).select_from(TaskDelegation))==0
        assert s.scalar(select(func.count()).select_from(LocalInference))==0


def test_scope_policy_is_versioned_with_packet(client,task_repository,config_and_no_network,monkeypatch):
    from app.services import upwork_scope
    order=create(client)
    run=client.post(f"/api/upwork-orders/{order['project_id']}/analysis",headers=OWNER_HEADERS).json()
    monkeypatch.setattr(upwork_scope,'INSTRUCTION',upwork_scope.INSTRUCTION+' Changed policy.')
    response=client.post(f"/api/local-inference/{run['id']}/run",headers=OWNER_HEADERS)
    assert response.status_code==200 and response.json()['state']=='stale'
    assert config_and_no_network.calls==0


@pytest.mark.parametrize('change',[
    {'source_url':'https://upwork.com.evil.invalid/job'}, {'source_url':'http://upwork.com/job'},
    {'source_url':'https://user@upwork.com/job'}, {'source_url':'https://upwork.com:443/job'},
    {'source_url':'https://upwork.com/\njob'}, {'source_url':'file:///etc/passwd'},
    {'title':' '}, {'job_text':'x'*3001}, {'job_text':'ą'*2600},
    {'acceptance_criteria':['same','same']}, {'acceptance_criteria':[]},
    {'acceptance_criteria':['x'*241]}, {'notes':'\x00'}, {'run':True},
])
def test_invalid_request_has_no_writes(client,task_repository,change):
    r=client.post('/api/upwork-orders',json=payload()|change,headers=OWNER_HEADERS)
    assert r.status_code==422,r.text
    with task_repository._session_factory() as s:
        assert s.scalar(select(func.count()).select_from(WorkOrder))==0


def test_owner_only_and_scoped_listing(client):
    for headers,status in [({},401),(WORKER_HEADERS,403)]:
        for path in ['/api/upwork-orders','/api/upwork-orders/1']:
            assert client.get(path,headers=headers).status_code==status
        assert client.post('/api/upwork-orders',json=payload(),headers=headers).status_code==status
        assert client.post('/api/upwork-orders/1/analysis',headers=headers).status_code==status
    from tests.test_work_orders import payload as regular
    other=client.post('/api/work-orders',json=regular(client),headers=OWNER_HEADERS).json()
    assert client.get(f"/api/upwork-orders/{other['project_id']}",headers=OWNER_HEADERS).status_code==404
    assert client.post(f"/api/upwork-orders/{other['project_id']}/analysis",headers=OWNER_HEADERS).status_code==404
    assert client.get('/api/upwork-orders',headers=OWNER_HEADERS).json()['orders']==[]


def test_list_pagination_and_shell(client):
    ids=[create(client)['project_id'] for _ in range(21)]
    r=client.get('/api/upwork-orders',headers=OWNER_HEADERS)
    assert r.headers['cache-control']=='no-store'
    assert [o['project_id'] for o in r.json()['orders']]==list(reversed(ids[1:]))
    rest=client.get('/api/upwork-orders?before='+str(r.json()['next_cursor']),headers=OWNER_HEADERS).json()
    assert [o['project_id'] for o in rest['orders']]==ids[:1] and rest['next_cursor'] is None
    page=client.get('/os/upwork')
    assert page.status_code==200 and "script-src 'self'" in page.headers['content-security-policy']
    assert 'owner-session.js' in page.text and 'id="upwork-intake"' in page.text
    for route in ('/os','/os/spatial'):
        assert 'href="/os/upwork"' in client.get(route).text


@pytest.mark.skipif(os.environ.get('AIC_UPWORK_PILOT') != '1', reason='Opt-in real local Qwen, synthetic scope only')
def test_real_qwen_rejects_unsupported_scope(client,task_repository,monkeypatch):
    from app.main import app
    from app.api.local_inference import get_provider_factory
    from app.services.local_ollama import OllamaProvider, configuration, ensure_idle
    ensure_idle()
    monkeypatch.setattr(local_inference,'enabled_config',configuration)
    app.dependency_overrides[get_provider_factory]=lambda:OllamaProvider
    data=payload() | {'title':'Syntetyczny test zakresu poza profilem',
                     'job_text':'Build a production multi-user CRM. Must have password login, PostgreSQL persistent data, Stripe subscription payments, outgoing email and production hosting. All features mandatory; do not substitute a static mockup.',
                     'acceptance_criteria':['Dwa konta widzą wyłącznie własne dane po ponownym uruchomieniu.', 'Płatność subskrypcji jest rozliczana przez Stripe.']}
    order=create(client,data)
    response=client.post(f"/api/upwork-orders/{order['project_id']}/analysis",headers=OWNER_HEADERS)
    assert response.status_code==200,response.text
    run=response.json()
    result=client.post(f"/api/local-inference/{run['id']}/run",headers=OWNER_HEADERS)
    assert result.status_code==200,result.text
    report=result.json()
    destination=Path(os.environ['AIC_UPWORK_PILOT_OUTPUT'])
    (destination/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    assert report['state']=='awaiting_review',report['error_code']
    content=report['result_content'].upper()
    assert 'UNSUPPORTED' in content
    assert 'POSTGRES' in content and 'STRIPE' in content
    from app.services.upwork_scope import validate_result
    validate_result(report['result_content'])
    assert json.loads(report['result_content'])['questions']==[]
    assert report['limits']['num_predict']<=1536
    with task_repository._session_factory() as s:
        assert s.get(Task,order['tasks'][0]['id']).progress==0
        assert s.scalar(select(func.count()).select_from(TaskAttempt))==1
    # This intentionally does NOT accept the proposal or generate/run code.


@pytest.mark.parametrize('result',[
    'Repeated prose '*400, '{"fit":"SUPPORTED","fit":"UNSUPPORTED"}',
    json.dumps(dict(fit='SUPPORTED',reason='Brak potwierdzonego zakresu.',questions=['Jak?'],scope=['CRM'],acceptance_cases=['Test'],exclusions=[])),
    json.dumps(dict(fit='UNSUPPORTED',reason='Poza wspieranym profilem.',questions=[],scope=['Makieta zamiast CRM'],acceptance_cases=[],exclusions=[])),
])
def test_bad_qwen_scope_never_becomes_task_result(client,task_repository,config_and_no_network,result,monkeypatch):
    from tests.test_local_inference import CONFIG
    def bad(self,messages):
        return dict(content=result,model=CONFIG['model'],digest=CONFIG['digest'],done_reason='stop')
    monkeypatch.setattr(config_and_no_network,'complete',bad)
    order=create(client)
    run=client.post(f"/api/upwork-orders/{order['project_id']}/analysis",headers=OWNER_HEADERS).json()
    response=client.post(f"/api/local-inference/{run['id']}/run",headers=OWNER_HEADERS)
    assert response.status_code==200,response.text
    assert response.json()['state']=='failed' and response.json()['result_content'] is None
    assert response.json()['error_code']=='scope_contract_invalid'
    with task_repository._session_factory() as s:
        assert s.scalar(select(func.count()).select_from(TaskAttempt))==0
        assert s.get(Task,order['tasks'][0]['id']).status.value=='pending'
