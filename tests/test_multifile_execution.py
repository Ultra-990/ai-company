import io
import json
import os
from uuid import uuid4
from zipfile import ZipFile

import pytest
from sqlalchemy import func, select

from app.main import app
from app.api.package_runner import get_runner
from app.models.artifact import Artifact
from app.models.package_run import PackageRun
from app.services import package_runner as service
from app.services import execution_profiles
from scripts.check_multifile_isolation import sources
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS

FLAT = {'profile': 'python-web-v1', 'image': 'sha256:' + 'a' * 64, 'harness_checksum': 'b' * 64}
MULTI = FLAT | {'profile': 'python-web-multifile-v1', 'harness_checksum': 'c' * 64}


def package(client, repository, files=None):
    task = repository.create(title='Synthetic multi-module API pilot')
    response = client.post(f'/api/tasks/{task.id}/workspace-packages', headers=OWNER_HEADERS,
                           json={'purpose': 'Synthetic test, not customer delivery', 'files': files or sources('success')})
    assert response.status_code == 201, response.text
    saved = response.json()
    assert saved['execution_profile'] == 'python-web-multifile-v1'
    assert saved['capabilities']['test'] and saved['capabilities']['package_review']
    return dict(task_id=task.id, package_id=saved['artifact_id'], package_checksum=saved['checksum'],
                request_id=str(uuid4()), confirm_execution=True)


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.setattr(service, 'configuration', lambda: dict(FLAT))
    monkeypatch.setattr(service, 'multifile_configuration', lambda: dict(MULTI))
    class Fake:
        calls = 0
        expected_files = sources('success')
        schema = 'python-web-multifile-test.v1'
        cleanup_confirmed = True
        after = lambda self: None
        def run(self, files, config, name):
            Fake.calls += 1
            assert config == MULTI and files == self.expected_files
            self.after()
            return {'exit_code': 0, 'cli_exit_code': 0, 'cleanup_confirmed': self.cleanup_confirmed, 'reason': None,
                    'log': json.dumps({'schema': self.schema, 'tests_ok': True, 'http_ok': True,
                        'source_not_exposed': True, 'isolation': {k: True for k in service.ISOLATION_KEYS}, 'errors': []})}
    previous = app.dependency_overrides.get(get_runner)
    app.dependency_overrides[get_runner] = Fake
    yield Fake
    if previous is None:
        app.dependency_overrides.pop(get_runner, None)
    else:
        app.dependency_overrides[get_runner] = previous


def test_multifile_run_report_replay_candidate_and_release_limits(client, task_repository, fake):
    body = package(client, task_repository)
    result = client.post('/api/package-runs', headers=OWNER_HEADERS, json=body)
    assert result.status_code == 200, result.text
    run = result.json()
    assert run['state'] == 'passed' and run['profile'] == MULTI
    assert not run['accepted'] and not run['deployed']
    assert run['capabilities']['preview'] and not run['capabilities']['automatic_repair']
    assert client.post('/api/package-runs', headers=OWNER_HEADERS, json=body).json() == run
    assert fake.calls == 1
    assert task_repository.get_required(body['task_id']).progress == 0
    archive = client.get(f"/api/package-runs/{run['id']}/candidate.zip", headers=OWNER_HEADERS)
    assert archive.status_code == 200
    with ZipFile(io.BytesIO(archive.content)) as zipfile:
        assert zipfile.read('sources/modules/logic.py').decode() == sources('success')['modules/logic.py']
        report = json.loads(zipfile.read('test-report.json'))
        assert report['source_checksum'] == body['package_checksum'] and report['profile'] == MULTI
        assert 'unittest discover -s tests -t .' in zipfile.read('READ-ME-FIRST.md').decode()
        assert not json.loads(zipfile.read('delivery.json'))['accepted']
    readiness = client.get(f"/api/package-runs/{run['id']}/delivery-readiness", headers=OWNER_HEADERS).json()
    assert not readiness['ready'] and readiness['checks'][-1]['key'] == 'package_review'
    assert client.post(f"/api/package-runs/{run['id']}/release", headers=OWNER_HEADERS).status_code == 409
    assert client.get(f"/api/package-runs/{run['id']}/released.zip", headers=OWNER_HEADERS).status_code == 409
    assert client.get(f"/api/package-runs/{run['id']}/handoff", headers=OWNER_HEADERS).status_code == 409
    with task_repository._session_factory() as session:
        assert session.scalar(select(func.count()).select_from(PackageRun)) == 1
        assert session.scalar(select(func.count()).select_from(Artifact)) == 2


def test_multifile_rejects_wrong_schema_and_uncertain_cleanup(client, task_repository, fake):
    body = package(client, task_repository)
    fake.schema = 'python-web-test.v1'
    run = client.post('/api/package-runs', headers=OWNER_HEADERS, json=body).json()
    assert run['state'] == 'failed'
    assert client.get(f"/api/package-runs/{run['id']}/candidate.zip", headers=OWNER_HEADERS).status_code == 409
    fake.schema = 'python-web-multifile-test.v1'
    fake.cleanup_confirmed = False
    run = client.post('/api/package-runs', headers=OWNER_HEADERS, json=body | {'request_id': str(uuid4())}).json()
    assert run['state'] == 'uncertain'
    assert client.post('/api/package-runs', headers=OWNER_HEADERS, json=body | {'request_id': str(uuid4())}).status_code == 409
    assert fake.calls == 2


def test_multifile_rejects_syntax_and_private_preview_path_before_execution(client, task_repository, fake):
    invalid = package(client, task_repository, sources('success') | {'modules/logic.py': 'def invalid(:'})
    assert client.post('/api/package-runs', headers=OWNER_HEADERS, json=invalid).status_code == 409
    valid = package(client, task_repository)
    assert client.post('/api/package-runs/preview', headers=OWNER_HEADERS, json=valid | {'path':'/app.py'}).status_code == 409
    assert fake.calls == 0
    with task_repository._session_factory() as session:
        assert session.scalar(select(func.count()).select_from(PackageRun)) == 0


def test_authorization_bindings_limits_and_profile_not_client_controlled(client, task_repository, fake):
    body = package(client, task_repository)
    for headers, status in (({}, 401), (WORKER_HEADERS, 403)):
        assert client.post('/api/package-runs', headers=headers, json=body).status_code == status
    for field in ('profile', 'image', 'command'):
        assert client.post('/api/package-runs', headers=OWNER_HEADERS, json=body | {field: 'anything'}).status_code == 422
    assert client.post('/api/package-runs', headers=OWNER_HEADERS, json=body | {'package_checksum': 'f' * 64}).status_code == 409
    for _ in range(3):
        response = client.post('/api/package-runs', headers=OWNER_HEADERS, json=body | {'request_id': str(uuid4())})
        assert response.status_code == 200
    assert client.post('/api/package-runs', headers=OWNER_HEADERS, json=body).status_code == 409
    assert fake.calls == 3


def test_policy_change_during_run_prevents_pass(client, task_repository, fake, monkeypatch):
    body = package(client, task_repository)
    active = dict(MULTI)
    monkeypatch.setattr(service, 'multifile_configuration', lambda: dict(active))
    fake.after = lambda self: active.update(harness_checksum='d' * 64)
    run = client.post('/api/package-runs', headers=OWNER_HEADERS, json=body).json()
    assert run['state'] == 'failed' and run['result']['reason'] == 'source_or_policy_changed'


def test_changed_harness_not_certified(monkeypatch):
    monkeypatch.setattr(execution_profiles, 'pilot_configuration', lambda: dict(MULTI))
    with pytest.raises(ValueError, match='pilot'):
        execution_profiles.multifile_configuration()


@pytest.mark.skipif(os.environ.get('AIC_MULTIFILE_API_PILOT') != '1', reason='Explicit real Docker pilot only after resource confirmation')
def test_real_multifile_api_pilot(client, task_repository):
    """Synthetic isolated DB + own limited container; never a customer package."""
    from tests.test_multifile_preview import preview_sources
    body = package(client, task_repository, preview_sources())
    response = client.post('/api/package-runs', headers=OWNER_HEADERS, json=body)
    assert response.status_code == 200, response.text
    run = response.json()
    assert run['state'] == 'passed', run
    from tests.test_package_acceptance import decision, post
    reviewed = post(client, run, decision(client, run))
    assert reviewed.status_code == 200, reviewed.text
    released = client.post(f"/api/package-runs/{run['id']}/release", headers=OWNER_HEADERS)
    assert released.status_code == 200, released.text
    handoff = client.get(f"/api/package-runs/{run['id']}/handoff", headers=OWNER_HEADERS)
    assert handoff.status_code == 200, handoff.text
    assert 'unittest discover' in handoff.json()['guides']['CLIENT-START-HERE.md']
    assert client.get(f"/api/package-runs/{run['id']}/released.zip", headers=OWNER_HEADERS).status_code == 200
    assert run['result']['cleanup_confirmed'] is True
    assert client.post('/api/package-runs', headers=OWNER_HEADERS, json=body).json() == run
    candidate = client.get(f"/api/package-runs/{run['id']}/candidate.zip", headers=OWNER_HEADERS)
    assert candidate.status_code == 200
    with ZipFile(io.BytesIO(candidate.content)) as archive:
        report = json.loads(archive.read('test-report.json'))
        assert report['source_checksum'] == body['package_checksum']
        assert report['profile']['profile'] == 'python-web-multifile-v1'
    assert task_repository.get_required(body['task_id']).progress == 0
    opened = client.post('/api/package-runs/preview', headers=OWNER_HEADERS,
                         json=body | {'request_id':str(uuid4()),'path':'/'})
    assert opened.status_code == 200, opened.text
    assert 'static/app.js' in opened.json()['assets'] and 'modules/logic.py' not in opened.json()['assets']
    calculated = client.post('/api/package-runs/preview', headers=OWNER_HEADERS,
                             json=body | {'request_id':str(uuid4()),'path':'/api/total'})
    assert calculated.status_code == 200, calculated.text
    assert json.loads(calculated.json()['response']['body']) == {'total':2576}
    assert task_repository.get_required(body['task_id']).progress == 0
