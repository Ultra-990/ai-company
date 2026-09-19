from hashlib import sha256
from types import SimpleNamespace as Row
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.models.audit import AuditEvent
from app.models.artifact import Artifact
from app.models.local_inference import LocalInference
from app.models.task import Task, TaskAttempt
from app.models.work_order import WorkOrder
from app.services.project_guidance import project_guidance
from tests.conftest import OWNER_HEADERS
from tests.test_work_orders import payload


def task(id=1, **changes):
    return dict(id=id, title=f'Etap {id}', status='pending',
                delegation={'planning_blockers': []}) | changes


def attempt(**changes):
    return Row(**(dict(status='completed', verification_status='accepted',
                       verified_at=True, result_content='Wynik',
                       result_checksum=sha256('Wynik'.encode()).hexdigest()) | changes))


def guide(tasks=None, attempts=None, runs=(), ids=None, status='planned'):
    tasks = tasks if tasks is not None else [task()]
    return project_guidance(ids if ids is not None else [t['id'] for t in tasks],
                            tasks, attempts or {}, runs, status)


@pytest.mark.parametrize('tasks,attempts,expected', [
    ([task(delegation=None)], {}, 'assignment'),
    ([task()], {}, 'instruction'),
    ([task(delegation={'planning_blockers':['Najpierw poprzedni etap']})], {}, 'blocked'),
    ([task(status='completed')], {}, 'unverified'),
    ([task(status='completed')], {1:attempt(result_checksum='bad')}, 'unverified'),
    ([task(status='completed')], {1:attempt(verification_status='verified')}, 'unverified'),
    ([task(status='completed')], {1:attempt(verified_at=None)}, 'unverified'),
    ([task(status='in_progress')], {1:attempt(status='awaiting_review')}, 'review'),
    ([task(status='blocked')], {1:attempt(verification_status='rejected')}, 'repair'),
    ([task(status='cancelled')], {}, 'cancelled'),
    ([task(status='in_progress')], {}, 'inspect'),
])
def test_state_is_derived_not_guessed_from_progress(tasks, attempts, expected):
    result = guide(tasks, attempts)
    assert result['current']['state'] == expected
    assert result['execution_authorized'] is False
    assert result['release_authorized'] is False


def test_all_accepted_requires_separate_delivery_checks():
    result = guide([task(status='completed')], {1:attempt()})
    assert result['accepted_stages'] == 1
    assert result['current']['state'] == 'stages_accepted'
    assert result['current']['action'] == 'artifacts'
    assert not result['release_authorized']


def test_order_and_missing_stage_are_preserved():
    result = guide([task(1)], ids=[2, 1])
    assert [stage['task_id'] for stage in result['stages']] == [2, 1]
    assert result['current']['state'] == 'inconsistent'
    assert guide([])['current']['state'] == 'inconsistent'


@pytest.mark.parametrize('state', ['queued', 'running', 'uncertain'])
def test_any_unsettled_run_takes_priority_over_starting_other_stages(state):
    result = guide([task(1), task(2, status='completed')], {2:attempt()},
                   [Row(id=1, task_id=2, state=state), Row(id=2, task_id=2, state='failed')])
    assert result['current']['task_id'] == 2
    assert result['current']['state'] == 'execution_hold'
    assert result['current']['action'] == 'history'


def test_failed_run_is_not_restarted_by_the_guide():
    result = guide(runs=[Row(id=1, task_id=1, state='failed')])
    assert result['current']['action'] == 'history'
    assert guide(status='cancelled')['current']['state'] == 'cancelled'


def test_owner_detail_is_read_only_and_reflects_delegation(client, task_repository):
    saved = client.post('/api/work-orders', json=payload(client), headers=OWNER_HEADERS).json()
    path = f"/api/work-orders/{saved['project_id']}"
    assert saved['guidance']['current']['state'] == 'assignment'
    client.post('/api/agent-teams/initialize', headers=OWNER_HEADERS)
    response = client.post(path + '/delegate', headers=OWNER_HEADERS)
    assert response.status_code == 200, response.text
    assert response.json()['guidance']['current']['state'] == 'instruction'
    models = (Task, TaskAttempt, Artifact, WorkOrder, AuditEvent, LocalInference)
    with task_repository._session_factory() as session:
        before = {model:session.scalar(select(func.count()).select_from(model)) for model in models}
        statuses = [(t.id, t.status, t.progress, t.queued_at) for t in session.scalars(select(Task))]
    for _ in range(2):
        result = client.get(path, headers=OWNER_HEADERS)
        assert result.headers['cache-control'] == 'no-store'
        assert result.json() == response.json()
    with task_repository._session_factory() as session:
        assert before == {model:session.scalar(select(func.count()).select_from(model)) for model in models}
        assert statuses == [(t.id, t.status, t.progress, t.queued_at) for t in session.scalars(select(Task))]


def test_foreign_task_is_not_exposed_by_corrupt_order_binding(client, task_repository):
    first = client.post('/api/work-orders', json=payload(client), headers=OWNER_HEADERS).json()
    second = client.post('/api/work-orders', json=payload(client), headers=OWNER_HEADERS).json()
    foreign_id = second['tasks'][0]['id']
    with task_repository._session_factory() as session:
        order = session.get(WorkOrder, first['request_id'])
        order.task_ids = [foreign_id, *order.task_ids]
        session.commit()
    result = client.get(f"/api/work-orders/{first['project_id']}", headers=OWNER_HEADERS).json()
    assert foreign_id not in [t['id'] for t in result['tasks']]
    assert result['guidance']['current']['state'] == 'inconsistent'


def test_detail_exposes_uncertain_run_as_hold_without_contacting_model(client, task_repository):
    saved = client.post('/api/work-orders', json=payload(client), headers=OWNER_HEADERS).json()
    path = f"/api/work-orders/{saved['project_id']}"
    package = client.post(path + '/website-starter', headers=OWNER_HEADERS).json()
    task_id = saved['tasks'][1]['id']
    with task_repository._session_factory() as session:
        session.add(LocalInference(request_id=str(uuid4()), task_id=task_id,
                                   packet_id=package['artifact_id'], packet_checksum='0' * 64,
                                   state='uncertain', model='test-only', model_digest='0' * 64,
                                   limits={}, metrics={}))
        session.commit()
    result = client.get(path, headers=OWNER_HEADERS).json()
    assert result['guidance']['current']['task_id'] == task_id
    assert result['guidance']['current']['state'] == 'execution_hold'
    assert result['guidance']['current']['action'] == 'history'
