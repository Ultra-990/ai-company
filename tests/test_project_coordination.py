import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.models.artifact import Artifact
from app.models.local_inference import LocalInference
from app.models.task import Task, TaskAttempt
from app.models.organization_os import Agent
from app.models.project import Project, ProjectStatus
from app.models.plan import Plan, PlanStatus
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS
from tests.test_agent_packets import assigned, submit, review


def snapshot(client, saved):
    path = f"/api/work-orders/{saved['project_id']}"
    data = client.get(path, headers=OWNER_HEADERS).json()
    c = data['coordination']
    return path, data, {'task_id': c['task_id'], 'expected_revision': c['revision']}


def prepare(client, saved):
    path, data, body = snapshot(client, saved)
    assert data['coordination']['can_prepare']
    response = client.post(path + '/prepare-next', headers=OWNER_HEADERS, json=body)
    assert response.status_code == 200, response.text
    return response.json()['instruction']


def test_resume_reuses_instruction_without_queuing_or_model(client, task_repository):
    saved = assigned(client)
    path, data, body = snapshot(client, saved)
    responses = [client.post(path + '/prepare-next', headers=OWNER_HEADERS, json=body) for _ in range(2)]
    assert all(r.status_code == 200 for r in responses)
    assert responses[0].json() == responses[1].json()
    packet = responses[0].json()['instruction']
    assert packet['task_id'] == saved['tasks'][0]['id']
    assert not responses[0].json()['model_invoked']
    with task_repository._session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Artifact).where(Artifact.id == packet['packet_id'])) == 1
        assert session.scalar(select(func.count()).select_from(TaskAttempt)) == 0
        assert session.scalar(select(func.count()).select_from(LocalInference)) == 0
        assert all(t.queued_at is None for t in session.scalars(select(Task)))
    assert client.get(path, headers=OWNER_HEADERS).json()['coordination'] == data['coordination']


def test_all_four_stages_are_selected_only_after_real_review_records(client):
    saved = assigned(client)
    for task in saved['tasks']:
        packet = prepare(client, saved)
        assert packet['task_id'] == task['id']
        assert submit(client, packet).status_code == 200
        path, data, body = snapshot(client, saved)
        assert data['guidance']['current']['state'] == 'review'
        assert client.post(path + '/prepare-next', headers=OWNER_HEADERS, json=body).status_code == 409
        assert review(client, task['id'], True).status_code == 200
    _, data, _ = snapshot(client, saved)
    assert data['guidance']['accepted_stages'] == 4
    assert not data['coordination']['can_prepare']
    assert not data['guidance']['release_authorized']


def test_rejection_prepares_same_stage_with_feedback_not_next_stage(client):
    saved = assigned(client)
    old = prepare(client, saved)
    assert submit(client, old).status_code == 200
    assert review(client, old['task_id'], False).status_code == 200
    revised = prepare(client, saved)
    assert revised['task_id'] == old['task_id']
    assert revised['packet_id'] != old['packet_id']
    assert revised['packet']['revision']['previous_attempt_id'] is not None
    assert prepare(client, saved)['packet_id'] == revised['packet_id']


def test_stale_view_never_silently_prepares_a_different_stage(client):
    saved = assigned(client)
    path, _, old_body = snapshot(client, saved)
    packet = prepare(client, saved)
    submit(client, packet)
    review(client, packet['task_id'], True)
    response = client.post(path + '/prepare-next', headers=OWNER_HEADERS, json=old_body)
    assert response.status_code == 409
    assert 'zmienił' in response.json()['detail']


@pytest.mark.parametrize('change', ['description', 'agent', 'cancelled', 'blocked', 'plan'])
def test_changed_context_rejects_stale_checkpoint(client, task_repository, change):
    saved = assigned(client)
    path, _, body = snapshot(client, saved)
    with task_repository._session_factory() as session:
        if change == 'description':
            session.get(Task, body['task_id']).description += '\nZmieniony zakres'
        elif change == 'agent':
            worker = saved['tasks'][0]['delegation']['worker']['id']
            session.get(Agent, worker).active = False
        elif change == 'plan':
            session.get(Plan, saved['plan_id']).status = PlanStatus.BLOCKED
        else:
            session.get(Project, saved['project_id']).status = ProjectStatus[change.upper()]
        session.commit()
    assert client.post(path + '/prepare-next', headers=OWNER_HEADERS, json=body).status_code == 409
    assert not snapshot(client, saved)[1]['coordination']['can_prepare']
    assert client.post(f"/api/tasks/{body['task_id']}/agent-packet", headers=OWNER_HEADERS).status_code == 409


def test_cross_project_task_and_non_owner_cannot_prepare(client):
    saved = assigned(client)
    path, _, body = snapshot(client, saved)
    for headers, status in (({}, 401), (WORKER_HEADERS, 403)):
        assert client.post(path + '/prepare-next', headers=headers, json=body).status_code == status
    other = assigned(client)
    body['task_id'] = other['tasks'][0]['id']
    assert client.post(path + '/prepare-next', headers=OWNER_HEADERS, json=body).status_code == 409


def test_failed_commit_rolls_back_instruction_and_can_be_retried(client, task_repository, monkeypatch):
    from app.api import work_orders
    original = work_orders.prepare_packet
    saved = assigned(client)
    path, _, body = snapshot(client, saved)
    with task_repository._session_factory() as session:
        before = session.scalar(select(func.count()).select_from(Artifact))
    def broken(session, task_id):
        original(session, task_id)
        raise SQLAlchemyError('synthetic persistence failure')
    monkeypatch.setattr(work_orders, 'prepare_packet', broken)
    assert client.post(path + '/prepare-next', headers=OWNER_HEADERS, json=body).status_code == 503
    with task_repository._session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Artifact)) == before
    monkeypatch.setattr(work_orders, 'prepare_packet', original)
    assert client.post(path + '/prepare-next', headers=OWNER_HEADERS, json=body).status_code == 200
