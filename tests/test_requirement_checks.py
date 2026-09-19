import json
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.models.artifact import Artifact
from app.models.audit import AuditEvent
from app.models.task import Task, TaskAttempt
from app.models.work_order import WorkOrder
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS
from tests.test_package_runner import package, fake_runner, FILES


@pytest.fixture
def case(client):
    p = package(client)
    path = f"/api/tasks/{p['task_id']}/workspace-packages/{p['package_id']}/requirements"
    response = client.get(path, headers=OWNER_HEADERS)
    assert response.status_code == 200, response.text
    matrix = response.json()
    body = dict(criterion_id=matrix['criteria'][0]['id'], source_checksum=matrix['source_checksum'],
        scope_checksum=matrix['scope_checksum'], previous_id=None, state='passed',
        observed_result='Przy szerokości 390 px sprawdzono tekst i menu: całość czytelna.',
        test_report_id=None, confirm_observation=True)
    return p, path, body


def test_test_pass_is_not_automatic_coverage(client, case, fake_runner):
    p, path, body = case
    run = client.post('/api/package-runs', headers=OWNER_HEADERS, json=p)
    assert run.status_code == 200, run.text
    result = client.get(path, headers=OWNER_HEADERS).json()
    assert result['counts']['not_checked'] == 2 and result['counts']['passed'] == 0
    assert not result['all_manually_confirmed'] and not result['automatic_coverage_verified']
    assert result['available_reports'][0]['id'] == run.json()['report_id']
    body['test_report_id'] = run.json()['report_id']
    assert client.post(path, headers=OWNER_HEADERS, json=body).status_code == 200
    result = client.get(path, headers=OWNER_HEADERS).json()
    assert result['counts']['passed'] == 1 and result['counts']['not_checked'] == 1
    assert result['criteria'][0]['test_report']['state'] == 'passed'
    assert not result['automatic_coverage_verified'] and fake_runner.calls == 1


def test_observation_is_append_only_idempotent_and_does_not_complete_task(client, case, task_repository):
    p, path, body = case
    task = task_repository.get(p['task_id'])
    with task_repository._session_factory() as session:
        before = session.scalar(select(func.count()).select_from(TaskAttempt))
    result = client.post(path, headers=OWNER_HEADERS, json=body)
    assert result.status_code == 200, result.text
    assert result.headers['cache-control'] == 'no-store'
    original = result.json()['assessment_id']
    assert client.post(path, headers=OWNER_HEADERS, json=body).json() == {'assessment_id': original, 'replayed': True}
    assert client.post(path, headers=OWNER_HEADERS, json=body | {'state': 'failed'}).status_code == 409
    correction = body | {'previous_id': original, 'state': 'failed', 'observed_result': 'Po dokładnym sprawdzeniu tekst na telefonie wychodzi poza ekran.'}
    response = client.post(path, headers=OWNER_HEADERS, json=correction)
    assert response.status_code == 200, response.text
    latest = response.json()['assessment_id']
    assert latest != original
    assert client.post(path, headers=OWNER_HEADERS, json=body).status_code == 409  # old replay cannot supersede correction
    data = client.get(path, headers=OWNER_HEADERS).json()
    assert data['counts']['failed'] == 1 and data['criteria'][0]['previous_id'] == original
    history_path = f"{path}/{body['criterion_id']}/history"
    history = client.get(history_path, headers=OWNER_HEADERS).json()
    assert [e['id'] for e in history['entries']] == [latest, original]
    assert [e['state'] for e in history['entries']] == ['failed', 'passed']
    assert client.get(history_path + f'?before={latest}', headers=OWNER_HEADERS).json()['entries'][0]['id'] == original
    assert client.get(history_path, headers=WORKER_HEADERS).status_code == 403
    with task_repository._session_factory() as session:
        assert json.loads(session.get(Artifact, original).content)['state'] == 'passed'
        assert json.loads(session.get(Artifact, latest).content)['state'] == 'failed'
        assert session.scalar(select(func.count()).select_from(TaskAttempt)) == before
        assert session.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.event_type == 'requirement_check')) == 2
    fresh = task_repository.get(p['task_id'])
    assert (fresh.status, fresh.progress) == (task.status, task.progress)


def test_new_package_has_no_inherited_confirmation(client, case):
    p, path, body = case
    assert client.post(path, headers=OWNER_HEADERS, json=body).status_code == 200
    fresh = client.post(f"/api/tasks/{p['task_id']}/workspace-packages", headers=OWNER_HEADERS,
        json={'purpose': 'Nowa wersja', 'files': FILES | {'README.md': 'Nowa instrukcja'}}).json()
    new_path = f"/api/tasks/{p['task_id']}/workspace-packages/{fresh['artifact_id']}/requirements"
    result = client.get(new_path, headers=OWNER_HEADERS).json()
    assert result['counts']['not_checked'] == 2
    assert client.post(new_path, headers=OWNER_HEADERS, json=body).status_code == 409


def test_changed_scope_and_task_assignment_fail_closed(client, case, task_repository):
    p, path, body = case
    assert client.post(path, headers=OWNER_HEADERS, json=body).status_code == 200
    with task_repository._session_factory() as session:
        task = session.get(Task, p['task_id'])
        order = session.scalar(select(WorkOrder).where(WorkOrder.project_id == task.project_id))
        order.brief = order.brief | {'goal': 'Zmieniony zakres celu, kryteria pozostają te same.'}
        session.commit()
    result = client.get(path, headers=OWNER_HEADERS).json()
    assert result['counts']['stale'] == 1 and not result['all_manually_confirmed']
    assert client.post(path, headers=OWNER_HEADERS, json=body).status_code == 409
    with task_repository._session_factory() as session:
        session.get(Task, p['task_id']).project_id = None
        session.commit()
    assert client.get(path, headers=OWNER_HEADERS).status_code == 409


def test_report_of_other_package_is_rejected_and_changed_report_invalidates_observation(client, case, task_repository):
    p, path, body = case
    other = package(client)
    other_run = client.post('/api/package-runs', headers=OWNER_HEADERS, json=other).json()
    assert client.post(path, headers=OWNER_HEADERS, json=body | {'test_report_id': other_run['report_id']}).status_code == 409
    run = client.post('/api/package-runs', headers=OWNER_HEADERS, json=p).json()
    body['test_report_id'] = run['report_id']
    assert client.post(path, headers=OWNER_HEADERS, json=body).status_code == 200
    with task_repository._session_factory() as session:
        session.get(Artifact, run['report_id']).content = 'damaged'
        session.commit()
    result = client.get(path, headers=OWNER_HEADERS).json()
    assert result['counts']['invalid'] == 1 and not result['all_manually_confirmed']
    assert result['available_reports'] == []


def test_corrupt_assessment_is_visible_but_never_overwritten(client, case, task_repository):
    _, path, body = case
    saved = client.post(path, headers=OWNER_HEADERS, json=body).json()['assessment_id']
    with task_repository._session_factory() as session:
        session.get(Artifact, saved).content = 'corrupt'
        session.commit()
    assert client.get(path, headers=OWNER_HEADERS).json()['counts']['invalid'] == 1
    assert client.post(path, headers=OWNER_HEADERS, json=body | {'previous_id': saved}).status_code == 409
    history = client.get(f"{path}/{body['criterion_id']}/history", headers=OWNER_HEADERS).json()
    assert history['entries'][0]['state'] == 'invalid' and history['entries'][0]['observed_result'] == ''


def test_corrupt_source_blocks_reads_and_writes_without_server_error(client, case, task_repository):
    p, path, body = case
    with task_repository._session_factory() as session:
        session.get(Artifact, p['package_id']).content = 'corrupt'
        session.commit()
    assert client.get(path, headers=OWNER_HEADERS).status_code == 409
    assert client.post(path, headers=OWNER_HEADERS, json=body).status_code == 409
    assert client.get(f"{path}/{body['criterion_id']}/history", headers=OWNER_HEADERS).status_code == 409


@pytest.mark.parametrize('change', [{'confirm_observation': False}, {'confirm_observation': 1},
    {'confirm_observation': 'true'}, {'state': 'completed'}, {'observed_result': ' '},
    {'observed_result': 'Niedozwolony tekst\x00'}, {'observed_result': 'a' * 2001},
    {'previous_id': True}, {'test_report_id': False}, {'unknown': 'field'}])
def test_invalid_input_rejected(client, case, change):
    _, path, body = case
    assert client.post(path, headers=OWNER_HEADERS, json=body | change).status_code == 422


def test_auth_binding_and_reads_without_writes(client, case, task_repository):
    p, path, body = case
    for headers, status in (({}, 401), (WORKER_HEADERS, 403)):
        assert client.get(path, headers=headers).status_code == status
        assert client.post(path, headers=headers, json=body).status_code == status
    assert client.post(path, headers=OWNER_HEADERS, json=body | {'criterion_id': 'a' * 64}).status_code == 409
    assert client.get(path.replace(f"tasks/{p['task_id']}/", 'tasks/99999/'), headers=OWNER_HEADERS).status_code == 404
    with task_repository._session_factory() as session:
        before = session.scalar(select(func.count()).select_from(Artifact))
    first = client.get(path, headers=OWNER_HEADERS)
    assert first.headers['cache-control'] == 'no-store'
    assert client.get(path, headers=OWNER_HEADERS).json() == first.json()
    with task_repository._session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Artifact)) == before


def test_all_manual_confirmations_still_do_not_mean_automatic_tests_or_client_acceptance(client, case, fake_runner):
    _, path, body = case
    result = client.get(path, headers=OWNER_HEADERS).json()
    for criterion in result['criteria']:
        assert client.post(path, headers=OWNER_HEADERS, json=body | {'criterion_id': criterion['id']}).status_code == 200
    result = client.get(path, headers=OWNER_HEADERS).json()
    assert result['all_manually_confirmed'] is True
    assert result['automatic_coverage_verified'] is False and result['client_accepted'] is False
    assert fake_runner.calls == 0
