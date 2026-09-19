from hashlib import sha256

import pytest
from sqlalchemy import func, select

from app.models.audit import AuditEvent
from app.models.delegation import TaskDelegation
from app.models.organization import OrganizationUnit
from app.models.organization_os import Agent
from app.models.task import Task, TaskAttempt, TaskStatus
from app.models.project import utc_now
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS
from tests.test_work_orders import payload


def order(client):
    response = client.post('/api/work-orders', headers=OWNER_HEADERS, json=payload(client))
    assert response.status_code == 201, response.text
    return response.json()


def setup(client):
    response = client.post('/api/agent-teams/initialize', headers=OWNER_HEADERS)
    assert response.status_code == 200, response.text
    return response.json()


def delegate(client, saved):
    return client.post(f"/api/work-orders/{saved['project_id']}/delegate", headers=OWNER_HEADERS)


def test_registry_has_twelve_managers_and_independent_reviewers_and_is_idempotent(client, task_repository):
    first = setup(client)
    assert len(first['teams']) == 12
    assert first['created'] == 72
    assert first['policy']['execution_enabled'] is False
    for team in first['teams']:
        by_role = {a['role']: a for a in team['agents']}
        assert len(by_role) == 6
        assert by_role['builder']['supervisor_id'] == by_role['manager']['id']
        assert by_role['reviewer']['supervisor_id'] == by_role['manager']['supervisor_id']
        assert all(a['runtime_status'] == 'not_started' for a in team['agents'])
    again = setup(client)
    assert again['created'] == 0 and again['teams'] == first['teams']
    with task_repository._session_factory() as s:
        agent = s.get(Agent, first['teams'][0]['agents'][0]['id'])
        agent.active = False
        agent.description = 'Zachować opis właściciela'
        s.commit()
    setup(client)
    with task_repository._session_factory() as s:
        agent = s.get(Agent, first['teams'][0]['agents'][0]['id'])
        assert not agent.active and agent.description == 'Zachować opis właściciela'
        assert s.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.event_type == 'agent_team')) == 1


def test_order_assigns_existing_tasks_without_approval_execution_or_duplicates(client, task_repository):
    setup(client)
    saved = order(client)
    response = delegate(client, saved)
    assert response.status_code == 200, response.text
    assigned = response.json()
    assert [t['id'] for t in assigned['tasks']] == [t['id'] for t in saved['tasks']]
    for index, task in enumerate(assigned['tasks']):
        d = task['delegation']
        assert len({d['manager']['id'], d['worker']['id'], d['reviewer']['id']}) == 3
        assert d['predecessor_id'] == (saved['tasks'][index-1]['id'] if index else None)
        assert d['planning_ready'] is (index == 0)
        assert not d['execution_enabled'] and d['policy']['allowed_tools'] == []
        assert task['status'] == 'pending' and task['approval_status'] == 'pending'
        assert not task['queued'] and task['progress'] == 0
        assert task['assigned_role'] == d['worker']['key']
        assert saved['brief']['goal'] in d['execution_brief']
    assert delegate(client, saved).json() == assigned
    assert client.get(f"/api/work-orders/{saved['project_id']}", headers=OWNER_HEADERS).json() == assigned
    assert task_repository.list_ready() == []
    with task_repository._session_factory() as s:
        assert s.scalar(select(func.count()).select_from(TaskDelegation)) == 4
        assert s.scalar(select(func.count()).select_from(TaskAttempt)) == 0
        assert s.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.event_type == 'task_delegation')) == 1


def test_no_team_no_assignment_and_partial_conflicts_roll_back_all_tasks(client, task_repository):
    saved = order(client)
    assert delegate(client, saved).status_code == 409
    setup(client)
    with task_repository._session_factory() as s:
        s.get(Task, saved['tasks'][-1]['id']).queued_at = utc_now()
        s.commit()
    assert delegate(client, saved).status_code == 409
    with task_repository._session_factory() as s:
        assert s.scalar(select(func.count()).select_from(TaskDelegation)) == 0
        assert s.get(Task, saved['tasks'][0]['id']).assigned_agent == saved['tasks'][0]['assigned_role']


def test_completed_status_alone_does_not_satisfy_predecessor_gate(client, task_repository):
    setup(client)
    saved = order(client)
    assert delegate(client, saved).status_code == 200
    path = f"/api/work-orders/{saved['project_id']}"
    first_id = saved['tasks'][0]['id']
    with task_repository._session_factory() as s:
        s.get(Task, first_id).status = TaskStatus.COMPLETED
        s.commit()
    assert not client.get(path, headers=OWNER_HEADERS).json()['tasks'][1]['delegation']['planning_ready']
    with task_repository._session_factory() as s:
        s.add(TaskAttempt(task_id=first_id, worker_id='fixture', status='completed',
                          verification_status='accepted', verified_at=utc_now(),
                          result_content='Specyfikacja', result_checksum=sha256('Specyfikacja'.encode()).hexdigest()))
        s.commit()
    ready = client.get(path, headers=OWNER_HEADERS).json()['tasks'][1]['delegation']
    assert ready['planning_ready'] and not ready['execution_enabled']
    with task_repository._session_factory() as s:
        attempt = s.scalar(select(TaskAttempt).where(TaskAttempt.task_id == first_id))
        attempt.result_content = 'Zmieniona treść'
        s.commit()
    assert not client.get(path, headers=OWNER_HEADERS).json()['tasks'][1]['delegation']['planning_ready']


def test_disabled_actor_and_changed_brief_are_reported_as_blockers(client, task_repository):
    setup(client)
    saved = order(client)
    assigned = delegate(client, saved).json()
    with task_repository._session_factory() as s:
        s.get(Agent, assigned['tasks'][0]['delegation']['worker']['id']).active = False
        s.get(Task, saved['tasks'][0]['id']).description = 'Zmiana zakresu'
        s.commit()
    changed = client.get(f"/api/work-orders/{saved['project_id']}", headers=OWNER_HEADERS).json()
    reasons = changed['tasks'][0]['delegation']['planning_blockers']
    assert len(reasons) == 2
    assert not changed['tasks'][0]['delegation']['planning_ready']


def test_legacy_approval_and_enqueue_cannot_bypass_team_execution_hold(client, task_repository):
    from app.models.task import TaskTransitionError
    setup(client)
    saved = order(client)
    assert delegate(client, saved).status_code == 200
    task_id = saved['tasks'][0]['id']
    task_repository.approve(task_id)
    with task_repository._session_factory() as s:
        s.get(Task, task_id).queued_at = utc_now()
        s.commit()
    assert task_repository.list_ready() == []
    with pytest.raises(TaskTransitionError, match='środowiska'):
        task_repository.claim(task_id, worker_id='legacy-worker')
    assert task_repository.get(task_id).status == TaskStatus.PENDING


@pytest.mark.parametrize('headers,status', [({},401),(WORKER_HEADERS,403)])
def test_teams_and_assignments_are_owner_only(client, headers, status):
    assert client.get('/api/agent-teams', headers=headers).status_code == status
    assert client.post('/api/agent-teams/initialize', headers=headers).status_code == status
    assert client.post('/api/work-orders/1/delegate', headers=headers).status_code == status


def test_missing_order_and_no_store(client):
    assert client.post('/api/work-orders/99999/delegate', headers=OWNER_HEADERS).status_code == 404
    assert client.get('/api/agent-teams', headers=OWNER_HEADERS).headers['cache-control'] == 'no-store'
    page = client.get('/os/work').text
    for id_ in ('initialize-teams', 'refresh-teams', 'delegate', 'teams'):
        assert f'id="{id_}"' in page
