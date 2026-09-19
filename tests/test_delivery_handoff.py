"""Small isolated tests. Every model and container call is a controlled fake."""
import io
import json
from hashlib import sha256
from uuid import uuid4
from zipfile import ZipFile

import pytest
from sqlalchemy import func, select

from app.main import app
from app.api.local_inference import get_provider_factory
from app.models.artifact import Artifact
from app.models.audit import AuditEvent
from app.models.package_run import PackageRun
from app.models.task import Task, TaskAttempt
from app.services.workspace_packages import canonical_json
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS
from tests.test_application_generation import builder_packet
from tests.test_agent_packets import review
from tests.test_local_inference import config_and_no_network, CONFIG
from tests.test_package_runner import fake_runner, FILES


@pytest.fixture
def tested(client):
    packet = builder_packet(client)

    class Provider:
        def __init__(self, config):
            pass

        def complete(self, messages):
            return {'content': json.dumps({'files': FILES}), 'model': CONFIG['model'],
                    'digest': CONFIG['digest'], 'done_reason': 'stop'}

    app.dependency_overrides[get_provider_factory] = lambda: Provider
    queued = client.post('/api/local-inference', headers=OWNER_HEADERS, json={
        'request_id': str(uuid4()), 'task_id': packet['task_id'],
        'packet_id': packet['packet_id'], 'packet_checksum': packet['checksum'],
        'output_profile': 'python-web-v1'})
    assert queued.status_code == 200, queued.text
    generated = client.post(f"/api/local-inference/{queued.json()['id']}/run", headers=OWNER_HEADERS)
    assert generated.status_code == 200, generated.text
    data = generated.json()
    run = client.post('/api/package-runs', headers=OWNER_HEADERS, json={
        'request_id': str(uuid4()), 'task_id': packet['task_id'],
        'package_id': data['metrics']['package_id'],
        'package_checksum': data['metrics']['package_checksum'], 'confirm_execution': True})
    assert run.status_code == 200, run.text
    return run.json()


@pytest.fixture
def released(client, tested):
    assert review(client, tested['task_id'], True).status_code == 200
    response = client.post(f"/api/package-runs/{tested['id']}/release", headers=OWNER_HEADERS)
    assert response.status_code == 200, response.text
    return tested | {'release_id': response.json()['release_id']}


def test_documents_require_current_owner_release(client, tested):
    url = f"/api/package-runs/{tested['id']}/handoff"
    assert client.get(url, headers=OWNER_HEADERS).status_code == 409
    assert review(client, tested['task_id'], True).status_code == 200
    assert client.get(url, headers=OWNER_HEADERS).status_code == 409  # no saved release
    assert client.get('/api/package-runs/99999/handoff', headers=OWNER_HEADERS).status_code == 404
    for headers, status in (({}, 401), (WORKER_HEADERS, 403)):
        assert client.get(url, headers=headers).status_code == status


def test_read_only_documents_zip_and_no_private_context(client, released, task_repository, fake_runner):
    with task_repository._session_factory() as session:
        # These are owner-internal fields and must never enter the new client documents.
        task = session.get(Task, released['task_id'])
        task.description = 'PRIVATE-NOTE-DO-NOT-SHARE'
        task.title = '<script>PRIVATE-TITLE</script>'
        session.commit()
        counts = [session.scalar(select(func.count()).select_from(model)) for model in (Artifact, AuditEvent, TaskAttempt)]
        task_state = (task.status, task.progress)
    runner_calls = fake_runner.calls
    path = f"/api/package-runs/{released['id']}"
    response = client.get(path + '/handoff', headers=OWNER_HEADERS)
    assert response.status_code == 200, response.text
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-content-type-options'] == 'nosniff'
    result = response.json()
    assert client.get(path + '/handoff', headers=OWNER_HEADERS).json() == result
    assert result['owner_accepted'] and not result['sent_to_client']
    assert not result['client_accepted'] and not result['deployed']
    assert result['source_checksum'] == released['package_checksum']
    assert 'PRIVATE-' not in response.text
    assert 'test_app -v' in result['guides']['CLIENT-START-HERE.md']
    assert 'Do not double-click' in result['guides']['CLIENT-START-HERE.md']
    assert 'http://127.0.0.1:8080' in result['message_en']
    assert all('content' not in file for file in result['files'])
    with ZipFile(io.BytesIO(client.get(path + '/released.zip', headers=OWNER_HEADERS).content)) as archive:
        for name, guide in result['guides'].items():
            assert archive.read(name).decode() == guide
            assert sha256(guide.encode()).hexdigest() == result['document_checksums'][name]
            assert '/os/' not in guide and 'PRIVATE-' not in guide
        assert json.loads(archive.read('handoff.json'))['document_checksums'] == result['document_checksums']
        assert archive.read('sources/app.py').decode() == FILES['app.py']
        assert '/os/build' not in archive.read('READ-ME-FIRST.md').decode()
        assert 'message_en' not in archive.namelist()
    with ZipFile(io.BytesIO(client.get(path + '/candidate.zip', headers=OWNER_HEADERS).content)) as archive:
        assert 'CLIENT-START-HERE.md' not in archive.namelist()
    with task_repository._session_factory() as session:
        assert [session.scalar(select(func.count()).select_from(model)) for model in (Artifact, AuditEvent, TaskAttempt)] == counts
        task = session.get(Task, released['task_id'])
        assert (task.status, task.progress) == task_state
    assert fake_runner.calls == runner_calls


@pytest.mark.parametrize('damage', ['source', 'report', 'release', 'wrong_report_shape',
                                   'wrong_release_run', 'wrong_release_attempt', 'new_failed_test', 'review'])
def test_stale_or_tampered_evidence_blocks_documents_and_zip(client, released, task_repository, damage):
    with task_repository._session_factory() as session:
        run = session.get(PackageRun, released['id'])
        if damage in {'source', 'report', 'release'}:
            artifact_id = {'source': run.package_id, 'report': run.report_id, 'release': released['release_id']}[damage]
            session.get(Artifact, artifact_id).content = 'corrupted'
        elif damage == 'wrong_report_shape':
            artifact = session.get(Artifact, run.report_id)
            artifact.content = '[]'
            artifact.checksum = sha256(artifact.content.encode()).hexdigest()
        elif damage == 'wrong_release_run':
            artifact = session.get(Artifact, released['release_id'])
            payload = json.loads(artifact.content)
            payload['run_id'] += 100
            artifact.content = canonical_json(payload)
            artifact.checksum = sha256(artifact.content.encode()).hexdigest()
        elif damage == 'wrong_release_attempt':
            session.get(Artifact, released['release_id']).task_attempt_id = None
        elif damage == 'review':
            attempt = session.get(TaskAttempt, session.get(Artifact, released['release_id']).task_attempt_id)
            attempt.verification_status = 'rejected'
        else:
            session.add(PackageRun(request_id=str(uuid4()), task_id=run.task_id,
                package_id=run.package_id, package_checksum=run.package_checksum,
                container_name='aic-package-' + uuid4().hex, state='failed', profile=run.profile, result={}))
        session.commit()
    for suffix in ('handoff', 'released.zip'):
        response = client.get(f"/api/package-runs/{released['id']}/{suffix}", headers=OWNER_HEADERS)
        assert response.status_code == 409, response.text
    assert client.get(f"/api/package-runs/{released['id']}/delivery-readiness", headers=OWNER_HEADERS).json()['ready'] is False
    assert client.post(f"/api/package-runs/{released['id']}/release", headers=OWNER_HEADERS).status_code == 409


def test_help_and_build_expose_handoff(client):
    page = client.get('/os/build')
    assert 'delivery-handoff.js?v=2' in page.text
    assert client.get('/os/help').status_code == 200
    assert 'id="handoff"' in client.get('/os/help').text
