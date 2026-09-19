import json

import pytest

from app.main import app
from app.api.package_runner import get_runner, get_preview_runner
from app.models.artifact import Artifact
from app.services import application_quality as quality, acceptance_cases, automatic_acceptance, application_preview
from tests.conftest import OWNER_HEADERS
from tests.test_acceptance_cases import plan_body
from tests.test_application_quality import body, result, create, run, isolated_locks
from tests.test_application_revisions import generated
from tests.test_local_inference import config_and_no_network
from tests.test_package_runner import fake_runner, CONFIG


@pytest.fixture
def simulation(monkeypatch):
    profile = CONFIG | {'profile': 'python-web-preview-v1'}
    monkeypatch.setattr(quality, 'preview_configuration', lambda: profile)
    monkeypatch.setattr(application_preview, 'preview_configuration', lambda: profile)
    monkeypatch.setattr(acceptance_cases, 'execution_enabled', lambda: True)
    class TestRunner:
        calls = 0
        def run(self, *args):
            TestRunner.calls += 1
            return result()
    app.dependency_overrides[get_runner] = TestRunner
    class Preview:
        calls = []
        values = [330, 2576]
        fail = False
        callback = None
        def __init__(self, path):
            self.path = path
        def run(self, files, config, name):
            Preview.calls.append(self.path)
            if Preview.fail:
                raise RuntimeError('simulated unavailable runner')
            if Preview.callback:
                Preview.callback()
            value = Preview.values[min(len(Preview.calls) - 1, len(Preview.values) - 1)]
            return {'exit_code': 0, 'cli_exit_code': 0, 'reason': None, 'cleanup_confirmed': True,
                'log': json.dumps({'schema': 'python-web-preview.v1', 'response': {
                    'status': 200, 'body': json.dumps({'total': value}), 'content_type': 'application/json'}})}
    app.dependency_overrides[get_preview_runner] = lambda: Preview
    return TestRunner, Preview


def planned(client, generated, extra_case=False):
    params = body(generated)
    path, payload = plan_body(client, params)
    if extra_case:
        payload['cases'].append(payload['cases'][0] | {'title': 'Drugi przykład', 'path': '/api/estimate?hours=4&rate=644'})
    response = client.post(path, headers=OWNER_HEADERS, json=payload)
    assert response.status_code == 200, response.text
    plan = response.json()
    return params | {'acceptance_plan_id': plan['id'], 'acceptance_plan_checksum': plan['checksum']}


def test_failed_http_expectation_repairs_and_retests_same_plan(client, generated, simulation, task_repository):
    tests, previews = simulation
    params = planned(client, generated)
    cycle = create(client, params)
    done = run(client, cycle['id'])
    assert done['state'] == 'passed', done
    assert [s['kind'] for s in done['steps']] == ['test', 'acceptance', 'repair', 'test', 'acceptance']
    cases = [s['cases'][0] for s in done['steps'] if s['kind'] == 'acceptance']
    assert [c['observed'] for c in cases] == [330, 2576]
    assert all(c['expected'] == 2576 for c in cases)
    assert tests.calls == 2 and len(previews.calls) == 2 and len(generated[2].calls) == 2
    assert '330' in str(generated[2].calls[-1]) and '2576' in str(generated[2].calls[-1])
    assert not done['owner_accepted'] and not done['published']
    assert run(client, cycle['id']) == done and len(previews.calls) == 2
    with task_repository._session_factory() as s:
        assert s.get(Artifact, params['acceptance_plan_id']).checksum == params['acceptance_plan_checksum']
    path = f"/api/tasks/{params['task_id']}/workspace-packages/{done['final_package_id']}/requirements"
    matrix = client.get(path, headers=OWNER_HEADERS).json()
    assert matrix['counts']['passed'] == 0 and not matrix['automatic_coverage_verified']


def test_rental_switch_blocks_all_execution_not_plan_preparation(client, generated, simulation, monkeypatch):
    tests, previews = simulation
    monkeypatch.setattr(acceptance_cases, 'execution_enabled', lambda: False)
    cycle = create(client, planned(client, generated))
    response = client.post(f"/api/application-quality/{cycle['id']}/run", headers=OWNER_HEADERS)
    assert response.status_code == 409, response.text
    assert tests.calls == 0 and previews.calls == [] and len(generated[2].calls) == 1


def test_healthy_http_does_not_request_model_repair(client, generated, simulation):
    tests, previews = simulation
    previews.values = [2576]
    done = run(client, create(client, planned(client, generated))['id'])
    assert done['state'] == 'passed' and tests.calls == 1 and len(generated[2].calls) == 1


def test_infrastructure_uncertainty_never_requests_code_repair(client, generated, simulation):
    tests, previews = simulation
    previews.fail = True
    done = run(client, create(client, planned(client, generated))['id'])
    assert done['state'] == 'needs_attention', done
    assert tests.calls == 1 and len(previews.calls) == 1 and len(generated[2].calls) == 1


@pytest.mark.parametrize('change', ['plan', 'profile'])
def test_changed_plan_or_runner_profile_stops_before_execution(client, generated, simulation, task_repository, monkeypatch, change):
    tests, previews = simulation
    params = planned(client, generated)
    cycle = create(client, params)
    if change == 'plan':
        with task_repository._session_factory() as s:
            s.get(Artifact, params['acceptance_plan_id']).content = 'tampered'
            s.commit()
    else:
        monkeypatch.setattr(quality, 'preview_configuration', lambda: {'changed': True})
    done = run(client, cycle['id'])
    assert done['state'] == 'needs_attention' and tests.calls == 0 and previews.calls == []


def test_stop_during_http_prevents_next_case_and_model(client, generated, simulation):
    tests, previews = simulation
    cycle = create(client, planned(client, generated, extra_case=True))
    def stop():
        r = client.post(f"/api/application-quality/{cycle['id']}/stop", headers=OWNER_HEADERS)
        assert r.status_code == 200
    previews.callback = stop
    done = run(client, cycle['id'])
    assert done['state'] == 'stopped', done
    assert len(previews.calls) == 1 and len(generated[2].calls) == 1


def test_incomplete_plan_binding_is_rejected(client, generated):
    for addition in ({'acceptance_plan_id': 5}, {'acceptance_plan_checksum': 'a' * 64},
                     {'acceptance_plan_id': True, 'acceptance_plan_checksum': 'a' * 64}):
        assert client.post('/api/application-quality', headers=OWNER_HEADERS, json=body(generated) | addition).status_code == 422


@pytest.mark.parametrize('tamper', [False, True])
def test_resume_revalidates_saved_evidence_without_running_again(client, generated, simulation, task_repository, monkeypatch, tamper):
    tests, previews = simulation
    previews.values = [2576]
    cycle = create(client, planned(client, generated))
    original = quality.finish
    def crash(*args, **kwargs):
        raise RuntimeError('simulated crash after durable cases before final receipt')
    monkeypatch.setattr(quality, 'finish', crash)
    with pytest.raises(RuntimeError):
        run(client, cycle['id'])
    monkeypatch.setattr(quality, 'finish', original)
    if tamper:
        with task_repository._session_factory() as s:
            report = automatic_acceptance.named(s, cycle['id'], 0)
            case_report = json.loads(report.content)['cases'][0]['report_id']
            s.get(Artifact, case_report).content = 'changed'
            s.commit()
    done = run(client, cycle['id'])
    assert done['state'] == ('needs_attention' if tamper else 'passed'), done
    assert tests.calls == 1 and len(previews.calls) == 1 and len(generated[2].calls) == 1


def test_persistent_http_failure_reaches_bounded_repair_limit(client, generated, simulation):
    tests, previews = simulation
    previews.values = [330]
    params = planned(client, generated) | {'max_repairs': 1}
    done = run(client, create(client, params)['id'])
    assert done['state'] == 'limit_reached', done
    assert tests.calls == 2 and len(previews.calls) == 2 and len(generated[2].calls) == 2
    assert all(s['state'] == 'failed' for s in done['steps'] if s['kind'] == 'acceptance')
    assert not done['owner_accepted']
