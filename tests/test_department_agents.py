from uuid import uuid4
import os
import json
from pathlib import Path
import pytest
from sqlalchemy import select,func

from app.organization_os.department_profiles import FOCUS,ROLE_GUIDANCE,role_profile
from app.organization_os.department_operations import OPERATIONS
from app.models.task import TaskAttempt
from app.models.artifact import Artifact
from app.services.agent_packets import export_prompt
from tests.conftest import OWNER_HEADERS,WORKER_HEADERS
from tests.test_agent_teams import setup,order,delegate
from tests.test_agent_packets import packet,submit,review
from tests.test_local_inference import config_and_no_network


def test_all_twelve_departments_have_six_bounded_role_profiles():
    assert set(FOCUS)==set(OPERATIONS) and len(FOCUS)==12
    for department in FOCUS:
        for role in ROLE_GUIDANCE:
            profile=role_profile(department,role)
            assert profile['version'] and profile['instruction'] and profile['mission']
            assert profile['tools']==[] and not profile['automatic_acceptance']
            assert (profile['runtime_mode']=='coordination_only')==(role in {'manager','reviewer'})
    assert role_profile('custom-department','builder') is None


@pytest.mark.parametrize('department',list(FOCUS))
def test_actual_tasks_use_department_specialization_in_all_four_stages(client,task_repository,department):
    setup(client)
    options=client.get('/api/work-orders/options',headers=OWNER_HEADERS).json()['units']
    unit=next(u for u in options if u['key']==OPERATIONS[department][4])
    payload=dict(request_id=str(uuid4()),title='Test specjalizacji działu',
                 goal='Przygotuj dokument zgodny z dostarczonymi danymi.',audience='Właściciel',constraints='Bez publikacji.',
                 organization_unit_id=unit['id'],acceptance_criteria=['Braki danych są wskazane.'])
    saved=client.post('/api/work-orders',headers=OWNER_HEADERS,json=payload).json()
    assert delegate(client,saved).status_code==200
    for role,task in zip(['analyst','builder','tester','delivery'],saved['tasks']):
        p=packet(client,task['id'])
        profile=p['packet']['department_profile']
        assert profile==role_profile(department,role)
        with task_repository._session_factory() as session:
            prompt=export_prompt(session,task['id'],p['packet_id'])
            assert profile['instruction'] in prompt['messages'][0]['content']
            assert 'Nie używaj narzędzi' in prompt['messages'][0]['content']
        # Synthetic manual output, explicitly accepted only in test DB.
        assert submit(client,p).status_code==200
        assert review(client,task['id'],True).status_code==200


def test_profile_update_stales_old_packet_without_overwrite(client,task_repository,monkeypatch):
    from app.organization_os import department_profiles
    setup(client);saved=order(client);assert delegate(client,saved).status_code==200
    p=packet(client,saved['tasks'][0]['id'])
    with task_repository._session_factory() as s:old=s.get(Artifact,p['packet_id']).content
    monkeypatch.setitem(department_profiles.ROLE_GUIDANCE,'analyst','Nowa instrukcja analityka.')
    r=client.get(f"/api/tasks/{p['task_id']}/agent-packets/{p['packet_id']}/prompt",headers=OWNER_HEADERS)
    assert r.status_code==409
    replacement=packet(client,p['task_id'])
    assert replacement['packet_id']!=p['packet_id'] and replacement['checksum']!=p['checksum']
    with task_repository._session_factory() as s:
        assert s.get(Artifact,p['packet_id']).content==old
        assert s.scalar(select(func.count()).select_from(TaskAttempt))==0


def test_activity_matches_real_inference_and_owner_acceptance(client,config_and_no_network):
    setup(client);saved=order(client);assigned=delegate(client,saved).json()
    task=assigned['tasks'][0]; worker=task['delegation']['worker']['id'];department=task['delegation']['department_id']
    def worker_state():
        teams=client.get('/api/agent-teams',headers=OWNER_HEADERS).json()['teams']
        team=next(t for t in teams if t['department_id']==department)
        return next(a for a in team['agents'] if a['id']==worker),team
    state,_=worker_state();assert state['assigned_tasks']==1 and state['runtime_status']=='not_started'
    p=packet(client,task['id'])
    run=client.post('/api/local-inference',headers=OWNER_HEADERS,json=dict(request_id=str(uuid4()),
        task_id=task['id'],packet_id=p['packet_id'],packet_checksum=p['checksum'])).json()
    state,team=worker_state();assert state['runtime_status']=='queued' and state['latest_run_states']=={'queued':1}
    assert all(a['runtime_status']=='not_started' for a in team['agents'] if a['role'] in {'manager','reviewer'})
    result=client.post(f"/api/local-inference/{run['id']}/run",headers=OWNER_HEADERS)
    assert result.status_code==200 and result.json()['state']=='awaiting_review'
    assert worker_state()[0]['runtime_status']=='awaiting_review'
    data=client.get(f'/api/agent-teams/{department}/work',headers=OWNER_HEADERS)
    assert data.status_code==200 and data.headers['cache-control']=='no-store'
    assert len(data.json()['tasks'])==4 and not data.json()['automatically_started']
    row=next(t for t in data.json()['tasks'] if t['task_id']==task['id'])
    assert row['run']['id']==run['id'] and row['work_url']==f"/os/work?project={saved['project_id']}"
    assert review(client,task['id'],True).status_code==200
    state,_=worker_state();assert state['latest_run_states']=={'accepted':1} and state['runtime_status']=='idle'
    assert config_and_no_network.calls==1


def test_department_work_is_owner_scoped_and_paginated(client):
    setup(client);saved=order(client);assigned=delegate(client,saved).json()
    department=assigned['tasks'][0]['delegation']['department_id']
    for _ in range(5):assert delegate(client,order(client)).status_code==200
    path=f'/api/agent-teams/{department}/work'
    first=client.get(path,headers=OWNER_HEADERS).json()
    assert len(first['tasks'])==20 and first['next_cursor']
    second=client.get(path+'?before='+str(first['next_cursor']),headers=OWNER_HEADERS).json()
    assert len(second['tasks'])==4 and second['next_cursor'] is None
    assert not set(t['task_id'] for t in first['tasks']) & set(t['task_id'] for t in second['tasks'])
    other=next(t for t in client.get('/api/agent-teams',headers=OWNER_HEADERS).json()['teams'] if t['department_id']!=department)
    assert client.get(f"/api/agent-teams/{other['department_id']}/work",headers=OWNER_HEADERS).json()['tasks']==[]
    for headers,status in [({},401),(WORKER_HEADERS,403)]:
        assert client.get(path,headers=headers).status_code==status
    assert client.get('/api/agent-teams/999999/work',headers=OWNER_HEADERS).status_code==404
    assert client.get(path+'?before=0',headers=OWNER_HEADERS).status_code==422


@pytest.mark.skipif(os.environ.get('AIC_DEPARTMENT_PILOT')!='1',reason='Opt-in real Qwen on synthetic department task')
def test_real_department_analyst_without_invented_finances(client,task_repository,monkeypatch):
    from app.main import app
    from app.api.local_inference import get_provider_factory
    from app.services import local_inference
    from app.services.local_ollama import configuration,OllamaProvider,ensure_idle
    ensure_idle()
    monkeypatch.setattr(local_inference,'enabled_config',configuration)
    app.dependency_overrides[get_provider_factory]=lambda:OllamaProvider
    setup(client)
    units=client.get('/api/work-orders/options',headers=OWNER_HEADERS).json()['units']
    unit=next(u for u in units if u['key']=='finance-legal.budget')
    body=dict(request_id=str(uuid4()),title='Test analityka finansów — brak danych',
              goal='Przygotuj wyłącznie listę brakujących danych potrzebnych do budżetu pierwszego zlecenia. Maksymalnie 120 słów. Nie podano żadnych kwot, waluty, czasu pracy ani kraju. Nie proponuj przykładowych liczb.',
              audience='Właściciel',constraints='Bez zgadywania liczb, stawek podatkowych lub jurysdykcji. Bez porady prawnej i płatności.',
              organization_unit_id=unit['id'],acceptance_criteria=['Każde brakujące dane są pytaniem, nie założonym faktem.'])
    saved=client.post('/api/work-orders',headers=OWNER_HEADERS,json=body).json()
    assert delegate(client,saved).status_code==200
    p=packet(client,saved['tasks'][0]['id'])
    run=client.post('/api/local-inference',headers=OWNER_HEADERS,json=dict(request_id=str(uuid4()),task_id=p['task_id'],
        packet_id=p['packet_id'],packet_checksum=p['checksum'])).json()
    response=client.post(f"/api/local-inference/{run['id']}/run",headers=OWNER_HEADERS)
    assert response.status_code==200,response.text
    report=response.json()
    destination=Path(os.environ['AIC_DEPARTMENT_PILOT_OUTPUT'])
    (destination/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    assert report['state']=='awaiting_review',report.get('error_code')
    content=report['result_content'].lower()
    assert len(content.split())<=120, 'Qwen przekroczył limit — wynik nie spełnia kryteriów.'
    assert len([line for line in content.splitlines() if line.strip()])<=6, 'Qwen przekroczył limit sześciu pytań z instrukcji.'
    assert all(line.rstrip().endswith('?') for line in content.splitlines() if line.strip()), 'Wymagana sama lista pytań.'
    assert 'walut' in content and '?' in content
    assert '23%' not in content and '25%' not in content and 'nok' not in content and 'pln' not in content
    with task_repository._session_factory() as s:
        from app.models.task import Task
        task=s.get(Task,p['task_id'])
        assert task.progress==0 and task.status.value=='in_progress'
    # Semantic judgment still needs a human reading the saved report.
