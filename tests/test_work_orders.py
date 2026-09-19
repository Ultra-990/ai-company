import io
import json
from uuid import uuid4
from zipfile import ZipFile

import pytest
from sqlalchemy import select, func

from app.models.work_order import WorkOrder
from app.models.project import Project
from app.models.plan import Plan
from app.models.task import Task, TaskAttempt, ApprovalStatus
from app.models.audit import AuditEvent
from app.services.work_orders import create_order, website_starter
from app.services.workspace_packages import validate_files
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS


def payload(client):
    options = client.get('/api/work-orders/options', headers=OWNER_HEADERS).json()
    unit = next(u for u in options['units'] if u['key'] == 'digital-experience.websites')
    return dict(request_id=str(uuid4()), title='Strona pracowni', goal='Przedstawić ofertę i portfolio pracowni.',
                audience='Właściciele mieszkań', constraints='Bez publikacji i usług płatnych.',
                organization_unit_id=unit['id'], acceptance_criteria=['Czytelna na telefonie', 'Nawigacja klawiaturą'])


def test_intake_persists_once_and_never_queues(client, task_repository):
    data = payload(client)
    first = client.post('/api/work-orders', json=data, headers=OWNER_HEADERS)
    assert first.status_code == 201, first.text
    saved = first.json()
    again = client.post('/api/work-orders', json=data, headers=OWNER_HEADERS)
    assert again.status_code == 200
    assert again.json() == saved
    assert len(saved['tasks']) == 4
    assert all(t['status'] == 'pending' and t['progress'] == 0 and not t['queued'] and t['approval_status'] == 'pending' for t in saved['tasks'])
    assert all(t['completion_criterion'] for t in saved['tasks'])
    assert task_repository.list_ready() == []
    with task_repository._session_factory() as s:
        assert s.scalar(select(func.count()).select_from(WorkOrder)) == 1
        p = s.get(Project, saved['project_id'])
        assert p.organization_unit_id == data['organization_unit_id']
        assert s.get(Plan, saved['plan_id']).project_id == p.id
        assert all(s.get(Task, t['id']).project_id == p.id for t in saved['tasks'])
        assert len(list(s.scalars(select(AuditEvent).where(AuditEvent.event_type == 'work_order')))) == 1
        assert s.scalar(select(func.count()).select_from(TaskAttempt)) == 0
    conflict = client.post('/api/work-orders', json=data | {'goal':'Inny cel i zakres prac.'}, headers=OWNER_HEADERS)
    assert conflict.status_code == 409
    assert client.get(f"/api/work-orders/{saved['project_id']}", headers=OWNER_HEADERS).json() == saved
    assert client.get('/api/work-orders', headers=OWNER_HEADERS).json()['orders'][0]['project_id'] == saved['project_id']


def test_auth_for_all_workbench_operations(client):
    data = payload(client)
    for headers, status in (({},401),(WORKER_HEADERS,403)):
        for path in ('/api/work-orders', '/api/work-orders/options', '/api/work-orders/1'):
            assert client.get(path, headers=headers).status_code == status
        assert client.post('/api/work-orders', json=data, headers=headers).status_code == status
        assert client.post('/api/work-orders/1/website-starter', headers=headers).status_code == status
    assert client.get('/api/work-orders/99999', headers=OWNER_HEADERS).status_code == 404
    assert client.post('/api/work-orders/99999/website-starter', headers=OWNER_HEADERS).status_code == 404


@pytest.mark.parametrize('change', [dict(title=' '),dict(goal='short'),dict(acceptance_criteria=[' ']),
                                  dict(acceptance_criteria=['same','same']),dict(acceptance_criteria=['x']*21),
                                  dict(organization_unit_id=999999),dict(request_id='bad'),dict(run=True)])
def test_invalid_briefs_never_create_orders(client, task_repository, change):
    response = client.post('/api/work-orders', json=payload(client)|change, headers=OWNER_HEADERS)
    assert response.status_code == 422, response.text
    with task_repository._session_factory() as s:
        assert s.scalar(select(func.count()).select_from(WorkOrder)) == 0


def test_parent_or_disabled_node_rejected(client, task_repository):
    from app.models.organization import OrganizationUnit
    data=payload(client)
    with task_repository._session_factory() as s:
        u=s.get(OrganizationUnit,data['organization_unit_id'])
        parent=u.parent_id
        u.active=False
        s.commit()
    for id_ in (data['organization_unit_id'],parent):
        assert client.post('/api/work-orders',json=data|{'organization_unit_id':id_},headers=OWNER_HEADERS).status_code == 422


def test_service_transaction_can_roll_back_all_entities(client, task_repository):
    data=payload(client); key=data.pop('request_id')
    with task_repository._session_factory() as s:
        initial={model:s.scalar(select(func.count()).select_from(model)) for model in (Project,Plan,Task,WorkOrder)}
        create_order(s,key,data)
        s.rollback()
        for model,count in initial.items():
            assert s.scalar(select(func.count()).select_from(model)) == count


def test_real_intake_to_source_zip_without_model_or_status_change(client, task_repository):
    data=payload(client)
    data['title']='<script>alert(1)</script>'
    saved=client.post('/api/work-orders',json=data,headers=OWNER_HEADERS).json()
    path=f"/api/work-orders/{saved['project_id']}"
    starter=client.post(path+'/website-starter',headers=OWNER_HEADERS)
    assert starter.status_code == 201, starter.text
    pkg=starter.json()
    assert pkg['execution_status']=='not_executed'
    assert pkg['review_status']=='not_reviewed'
    assert pkg['task_id']==saved['tasks'][1]['id']
    assert pkg['file_count']==4
    response=client.get(f"/api/tasks/{pkg['task_id']}/workspace-packages/{pkg['artifact_id']}/download",headers=OWNER_HEADERS)
    assert response.status_code==200
    with ZipFile(io.BytesIO(response.content)) as z:
        assert set(z.namelist())=={'index.html','styles.css','README.md','brief.json'}
        html=z.read('index.html').decode()
        assert '<script>' not in html and '&lt;script&gt;' in html
        assert 'https://' not in html and 'http://' not in html
        assert json.loads(z.read('brief.json'))['title']==data['title']
        assert 'nie wynik modelu AI' in z.read('README.md').decode()
    detail=client.get(path,headers=OWNER_HEADERS).json()
    assert detail['tasks']==saved['tasks']
    assert detail['artifacts'][0]['id']==pkg['artifact_id']
    second=client.post(path+'/website-starter',headers=OWNER_HEADERS).json()
    assert second['artifact_id']!=pkg['artifact_id']
    assert second['checksum']==pkg['checksum']
    # Even an approval does not enqueue held intake tasks; this is not a runner.
    task_repository.approve(saved['tasks'][0]['id'])
    from app.db.migrations import migrate_task_queue_schema
    migrate_task_queue_schema(task_repository._engine)
    migrate_task_queue_schema(task_repository._engine)
    assert task_repository.list_ready()==[]


def test_list_pagination(client):
    data=payload(client)
    ids=[]
    for _ in range(21):
        saved=client.post('/api/work-orders',json=data|{'request_id':str(uuid4())},headers=OWNER_HEADERS).json()
        ids.append(saved['project_id'])
    first=client.get('/api/work-orders',headers=OWNER_HEADERS)
    assert first.headers['cache-control']=='no-store'
    assert len(first.json()['orders'])==20
    cursor=first.json()['next_cursor']
    last=client.get(f'/api/work-orders?before={cursor}',headers=OWNER_HEADERS).json()
    assert [o['project_id'] for o in last['orders']]==ids[:1]
    assert last['next_cursor'] is None


def test_workbench_shell_and_local_assets(client):
    r=client.get('/os/work')
    assert r.status_code==200
    assert "script-src 'self'" in r.headers['content-security-policy']
    for id_ in ('intake','token','starter','logout','tasks'):
        assert f'id="{id_}"' in r.text
    assert 'test-owner-token' not in r.text
    assert client.get('/static/organization-os/work.js').status_code==200
    assert '/os/work' in client.get('/static/spatial/spatial.js').text
    assert '/os/work' in client.get('/os').text


def test_generated_files_with_maximum_brief_are_valid():
    files=website_starter(dict(title='ą'*160,goal='<'*6000,audience='&'*1000,constraints='x'*3000,acceptance_criteria=['x'*500]*20))
    assert len(validate_files(files))==4
