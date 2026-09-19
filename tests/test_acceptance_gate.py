"""Read-only acceptance/release gates, isolated SQLite and fake model/runner only."""
import io
import json
from uuid import uuid4
from zipfile import ZipFile

import pytest
from sqlalchemy import func, select

from app.models.artifact import Artifact
from app.models.audit import AuditEvent
from app.models.package_run import PackageRun
from app.models.task import Task, TaskAttempt, TaskStatus
from app.models.work_order import WorkOrder
from app.services import acceptance_cases, acceptance_gate, automatic_acceptance, application_preview
from app.services.workspace_packages import canonical_json
from tests.conftest import OWNER_HEADERS
from tests.test_acceptance_cases import plan_body
from tests.test_automatic_acceptance import simulation, planned
from tests.test_application_quality import body, create, run, isolated_locks
from tests.test_application_revisions import generated
from tests.test_agent_packets import review
from tests.test_local_inference import config_and_no_network
from tests.test_package_runner import fake_runner


def cycle_passed(client, generated, simulation):
    simulation[1].values = [2576]
    params = planned(client, generated)
    cycle = create(client, params)
    done = run(client, cycle['id'])
    assert done['state'] == 'passed', done
    return params, done


def test_draft_plan_does_not_block_legacy_review(client, generated, simulation):
    params = body(generated)
    path, data = plan_body(client, params)
    assert client.post(path, headers=OWNER_HEADERS, json=data).status_code == 200
    assert review(client, params['task_id'], True).status_code == 200
    assert simulation[0].calls == 0 and simulation[1].calls == []


def test_selected_but_unexecuted_plan_blocks_approval_without_mutating_task(client, generated, simulation, task_repository):
    params = planned(client, generated)
    create(client, params)
    with task_repository._session_factory() as s:
        before = [s.scalar(select(func.count()).select_from(model)) for model in (Artifact, AuditEvent)]
    response = review(client, params['task_id'], True)
    assert response.status_code == 409, response.text
    assert 'nie ma zakończonego wyniku' in response.json()['detail']
    with task_repository._session_factory() as s:
        assert before == [s.scalar(select(func.count()).select_from(model)) for model in (Artifact, AuditEvent)]
        task = s.get(Task, params['task_id'])
        assert task.status == TaskStatus.IN_PROGRESS and task.progress == 0
        assert s.get(TaskAttempt, generated[1]['attempt_id']).status == 'awaiting_review'
    # Refusing the result is still possible: no deadlock for corrections.
    assert review(client, params['task_id'], False).status_code == 200
    assert simulation[0].calls == 0 and simulation[1].calls == []


def test_failed_cases_block_owner_approval_and_release_but_leave_candidate_available(client, generated, simulation):
    simulation[1].values = [330]
    params = planned(client, generated) | {'max_repairs': 1}
    done = run(client, create(client, params)['id'])
    assert done['state'] == 'limit_reached'
    assert review(client, params['task_id'], True).status_code == 409
    path = f"/api/package-runs/{done['test_run_id']}"
    readiness = client.get(path + '/delivery-readiness', headers=OWNER_HEADERS).json()
    assert not readiness['ready'] and readiness['checks'][-1]['key'] == 'acceptance_plan'
    assert client.post(path + '/release', headers=OWNER_HEADERS).status_code == 409
    assert client.get(path + '/candidate.zip', headers=OWNER_HEADERS).status_code == 200
    assert client.get(path + '/released.zip', headers=OWNER_HEADERS).status_code == 409


def test_passing_plan_is_bound_to_review_release_and_zip_without_further_execution(client, generated, simulation, task_repository, monkeypatch):
    params, done = cycle_passed(client, generated, simulation)
    before_calls = (simulation[0].calls, len(simulation[1].calls), len(generated[2].calls))
    # Read-only evidence checks must work even when new execution is disabled.
    monkeypatch.setattr(acceptance_cases, 'execution_enabled', lambda: False)
    assert review(client, params['task_id'], True).status_code == 200
    path = f"/api/package-runs/{done['test_run_id']}"
    readiness = client.get(path + '/delivery-readiness', headers=OWNER_HEADERS).json()
    assert readiness['ready'], readiness
    proof = readiness['acceptance_proof']
    assert proof['plan_id'] == params['acceptance_plan_id'] and proof['case_count'] == 1
    release = client.post(path + '/release', headers=OWNER_HEADERS)
    assert release.status_code == 200, release.text
    assert release.json()['acceptance_proof'] == proof
    assert client.post(path + '/release', headers=OWNER_HEADERS).status_code == 200
    assert client.get(path + '/handoff', headers=OWNER_HEADERS).status_code == 200
    with ZipFile(io.BytesIO(client.get(path + '/released.zip', headers=OWNER_HEADERS).content)) as archive:
        manifest = json.loads(archive.read('delivery.json'))
        assert manifest['owner_review']['acceptance_proof'] == proof
        assert manifest['client_accepted'] is False
    with task_repository._session_factory() as s:
        receipt = s.scalar(select(Artifact).where(Artifact.task_id == params['task_id'],
            Artifact.name == 'Odbiór wyniku zadania').order_by(Artifact.id.desc()))
        assert json.loads(receipt.content)['acceptance_proof'] == proof
        counts = [s.scalar(select(func.count()).select_from(model)) for model in (Artifact, AuditEvent, PackageRun)]
    assert client.get(path + '/delivery-readiness', headers=OWNER_HEADERS).json()['ready']
    assert client.get(path + '/released.zip', headers=OWNER_HEADERS).status_code == 200
    with task_repository._session_factory() as s:
        assert counts == [s.scalar(select(func.count()).select_from(model)) for model in (Artifact, AuditEvent, PackageRun)]
    assert before_calls == (simulation[0].calls, len(simulation[1].calls), len(generated[2].calls))


@pytest.mark.parametrize('damage', ['plan', 'case_report', 'aggregate', 'final', 'scope', 'profile', 'release', 'response', 'foreign_case_run'])
def test_changed_evidence_blocks_existing_release_download_and_handoff(client, generated, simulation, task_repository, monkeypatch, damage):
    params, done = cycle_passed(client, generated, simulation)
    assert review(client, params['task_id'], True).status_code == 200
    path = f"/api/package-runs/{done['test_run_id']}"
    release = client.post(path + '/release', headers=OWNER_HEADERS).json()
    with task_repository._session_factory() as s:
        aggregate = automatic_acceptance.named(s, done['id'], 0)
        cases = json.loads(aggregate.content)['cases']
        if damage == 'plan':
            s.get(Artifact, params['acceptance_plan_id']).content = 'damaged'
        if damage == 'case_report':
            s.get(Artifact, cases[0]['report_id']).content = 'damaged'
        if damage == 'aggregate':
            aggregate.content = 'damaged'
        if damage == 'final':
            from app.services import application_quality as quality
            quality.named(s, quality.NAME + f":result:{done['id']}").content = 'damaged'
        if damage == 'scope':
            task = s.get(Task, params['task_id'])
            order = s.scalar(select(WorkOrder).where(WorkOrder.project_id == task.project_id))
            order.brief = order.brief | {'goal': 'Zmieniony zakres po poprzedniej kontroli.'}
        if damage == 'profile':
            monkeypatch.setattr(application_preview, 'preview_configuration', lambda: {'changed': True})
        if damage == 'release':
            row = s.get(Artifact, release['release_id'])
            payload = json.loads(row.content)
            payload.pop('acceptance_proof')
            row.content = canonical_json(payload)
            row.checksum = acceptance_cases.digest(row.content)
        if damage == 'response':
            # Even internally consistent changed run/report cannot override the
            # saved evaluation or make the gate trust aggregate state='passed'.
            execution = s.get(PackageRun, cases[0]['run_id'])
            changed = json.loads(execution.result['log'])
            changed['response']['body'] = '{"total":330}'
            execution.result = execution.result | {'log': json.dumps(changed)}
            report = s.get(Artifact, cases[0]['report_id'])
            payload = json.loads(report.content) | {'result': execution.result}
            report.content = canonical_json(payload)
            report.checksum = acceptance_cases.digest(report.content)
        if damage == 'foreign_case_run':
            s.get(PackageRun, cases[0]['run_id']).request_id = str(uuid4())
        s.commit()
    readiness = client.get(path + '/delivery-readiness', headers=OWNER_HEADERS)
    assert readiness.status_code == 200 and not readiness.json()['ready'], readiness.text
    assert client.post(path + '/release', headers=OWNER_HEADERS).status_code == 409
    assert client.get(path + '/released.zip', headers=OWNER_HEADERS).status_code == 409
    assert client.get(path + '/handoff', headers=OWNER_HEADERS).status_code == 409


def test_planless_cycle_cannot_bypass_selected_plan_and_new_selection_supersedes_old(client, generated, simulation):
    params, done = cycle_passed(client, generated, simulation)
    plain = body(generated) | {'request_id': str(uuid4())}
    assert client.post('/api/application-quality', headers=OWNER_HEADERS, json=plain).status_code == 409
    path, definition = plan_body(client, plain)
    definition['cases'][0]['expected'] = 330
    new = client.post(path, headers=OWNER_HEADERS, json=definition).json()
    # Draft does not supersede the explicitly selected plan.
    before = client.get(f"/api/package-runs/{done['test_run_id']}/delivery-readiness", headers=OWNER_HEADERS).json()
    assert before['acceptance_proof']['plan_id'] == params['acceptance_plan_id']
    create(client, params | {'request_id': str(uuid4()), 'acceptance_plan_id': new['id'], 'acceptance_plan_checksum': new['checksum']})
    assert review(client, params['task_id'], True).status_code == 409


def test_success_of_previous_version_does_not_validate_another_package(client, generated, simulation, task_repository):
    params, done = cycle_passed(client, generated, simulation)
    from tests.test_package_runner import FILES
    fresh = client.post(f"/api/tasks/{params['task_id']}/workspace-packages", headers=OWNER_HEADERS,
        json={'purpose': 'Inna wersja źródeł', 'files': FILES | {'README.md': 'Inna wersja'}}).json()
    with task_repository._session_factory() as s:
        with pytest.raises(ValueError, match='nie potwierdza'):
            acceptance_gate.require_current(s, params['task_id'], fresh['artifact_id'], fresh['checksum'])


def test_repaired_version_uses_final_cases_not_the_initial_failed_ones(client, generated, simulation):
    params = planned(client, generated)
    done = run(client, create(client, params)['id'])  # 330 -> one fake repair -> 2576
    assert done['state'] == 'passed' and done['final_package_id'] != params['package_id']
    assert review(client, params['task_id'], True).status_code == 200
    release = client.post(f"/api/package-runs/{done['test_run_id']}/release", headers=OWNER_HEADERS)
    assert release.status_code == 200, release.text
    last = [step for step in done['steps'] if step['kind'] == 'acceptance'][-1]
    assert release.json()['acceptance_proof']['result_id'] == last['id']


@pytest.mark.parametrize('damage', ['missing_plan_id', 'invalid_input', 'wrong_attempt_sources'])
def test_corrupt_selection_or_attempt_cannot_turn_into_legacy_approval(client, generated, simulation, task_repository, damage):
    params, done = cycle_passed(client, generated, simulation)
    with task_repository._session_factory() as s:
        if damage == 'wrong_attempt_sources':
            attempt = s.get(TaskAttempt, generated[1]['attempt_id'])
            files = json.loads(attempt.result_content)
            files['files']['app.py'] = 'print("different sources")'
            attempt.result_content = json.dumps(files)
            attempt.result_checksum = acceptance_cases.digest(attempt.result_content)
        else:
            row = s.get(Artifact, done['id'])
            payload = json.loads(row.content)
            if damage == 'missing_plan_id':
                payload['input'].pop('acceptance_plan_id')
            else:
                payload['input'] = None
            row.content = canonical_json(payload)
            row.checksum = acceptance_cases.digest(row.content)
        s.commit()
    assert review(client, params['task_id'], True).status_code == 409
