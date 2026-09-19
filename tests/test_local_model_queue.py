from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.models.artifact import Artifact
from app.models.local_model_job import LocalModelJob
from app.models.task import Task, TaskAttempt
from app.services.local_model_queue import run_next, FixtureProvider
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS
from tests.test_agent_packets import assigned, packet


def queued(client):
    task_id = assigned(client)['tasks'][0]['id']
    p = packet(client, task_id)
    body = dict(request_id=str(uuid4()), task_id=task_id, packet_id=p['packet_id'], packet_checksum=p['checksum'])
    response = client.post('/api/local-model-queue', headers=OWNER_HEADERS, json=body)
    assert response.status_code == 200, response.text
    return response.json(), body


def test_queue_replay_cancel_and_read_only_simulation(client, task_repository):
    job, body = queued(client)
    assert job['state'] == 'queued' and job['mode'] == 'simulation'
    assert client.post('/api/local-model-queue', headers=OWNER_HEADERS, json=body).json()['id'] == job['id']
    assert client.post('/api/local-model-queue', headers=OWNER_HEADERS, json=body | {'request_id': str(uuid4())}).json()['id'] == job['id']
    assert client.post('/api/local-model-queue', headers=OWNER_HEADERS, json=body | {'packet_checksum': '0'*64}).status_code == 409
    with task_repository._session_factory() as s:
        before = s.get(Task, body['task_id'])
        baseline = (before.status, before.progress, before.queued_at)
        count = s.scalar(select(func.count()).select_from(Artifact))
    result = client.post('/api/local-model-queue/simulate-next', headers=OWNER_HEADERS).json()
    assert result['job']['state'] == 'simulation_complete' and not result['model_invoked']
    assert 'SYMULACJA' in result['job']['result_content']
    assert result['job']['attempts'] == 1
    assert client.post('/api/local-model-queue/simulate-next', headers=OWNER_HEADERS).json()['job'] is None
    with task_repository._session_factory() as s:
        after = s.get(Task, body['task_id'])
        assert (after.status, after.progress, after.queued_at) == baseline
        assert s.scalar(select(func.count()).select_from(TaskAttempt)) == 0
        assert s.scalar(select(func.count()).select_from(Artifact)) == count
    assert client.post(f'/api/local-model-queue/{job["id"]}/cancel', headers=OWNER_HEADERS).status_code == 409
    next_job, _ = queued(client)
    path = f'/api/local-model-queue/{next_job["id"]}/cancel'
    assert client.post(path, headers=OWNER_HEADERS).json()['state'] == 'cancelled'
    assert client.post(path, headers=OWNER_HEADERS).status_code == 200
    listing = client.get('/api/local-model-queue', headers=OWNER_HEADERS)
    assert listing.headers['cache-control'] == 'no-store'
    assert listing.json()['live_enabled'] is False


@pytest.mark.parametrize('during', [False, True])
def test_stale_instruction_before_or_during_response(client, task_repository, during):
    job, body = queued(client)
    def change():
        with task_repository._session_factory() as s:
            s.get(Task, body['task_id']).title = 'Nowy zakres'
            s.commit()
    class ChangingProvider:
        simulation_only = True
        calls = 0
        def complete(self, messages):
            self.calls += 1
            change()
            return 'Nie zapisywać po zmianie kontekstu'
    provider = ChangingProvider()
    if not during: change()
    with task_repository._session_factory() as s:
        result = run_next(s, provider)
    assert result['job']['state'] == 'stale'
    assert result['job']['result_content'] is None
    assert provider.calls == int(during)


@pytest.mark.parametrize('output', [None, '', 'x'*32001, '\x00', '\ud800', TimeoutError('secret'), RuntimeError('secret')])
def test_failures_have_no_retry_or_private_error_text(client, task_repository, output):
    queued(client)
    class Provider:
        simulation_only = True
        calls = 0
        def complete(self, messages):
            self.calls += 1
            if isinstance(output, Exception): raise output
            return output
    provider = Provider()
    with task_repository._session_factory() as s:
        result = run_next(s, provider)
        assert run_next(s, provider)['job'] is None
    assert result['job']['state'] == 'failed'
    assert result['job']['result_content'] is None
    assert 'secret' not in str(result)
    assert provider.calls == 1


def test_single_slot_fifo_and_no_db_write_lock_during_call(client, task_repository):
    first, _ = queued(client)
    second, _ = queued(client)
    class Provider:
        simulation_only = True
        def complete(self, messages):
            with task_repository._session_factory() as s:
                with pytest.raises(ValueError, match='już wykonywana'):
                    run_next(s, FixtureProvider())
            return 'Odpowiedź próbna'
    with task_repository._session_factory() as s:
        assert run_next(s, Provider())['job']['id'] == first['id']
        assert run_next(s, FixtureProvider())['job']['id'] == second['id']


def test_running_job_not_reclaimed_after_restart_and_live_adapter_refused(client, task_repository):
    job, _ = queued(client)
    with task_repository._session_factory() as s:
        with pytest.raises(ValueError, match='Inferencja jest wyłączona'):
            run_next(s, object())
        s.get(LocalModelJob, job['id']).state = 'running'
        s.commit()
    with task_repository._session_factory() as s:
        with pytest.raises(ValueError, match='już wykonywana'):
            run_next(s, FixtureProvider())


@pytest.mark.parametrize('headers,status', [({}, 401), (WORKER_HEADERS, 403)])
def test_owner_only(client, headers, status):
    for method, path in [('get',''), ('post',''), ('post','/simulate-next'), ('post','/1/cancel')]:
        assert getattr(client, method)('/api/local-model-queue'+path, headers=headers).status_code == status


def test_cannot_request_live_or_arbitrary_model_and_client_surface_excluded(client):
    from app.client_main import app as client_app
    from fastapi.testclient import TestClient
    _, body = queued(client)
    for extra in ({'mode':'live'}, {'model':'other'}, {'base_url':'http://example.com'}, {'tools':['shell']}):
        assert client.post('/api/local-model-queue', headers=OWNER_HEADERS, json=body | extra).status_code == 422
    with TestClient(client_app) as external:
        assert external.get('/api/local-model-queue', headers=OWNER_HEADERS).status_code == 404
    page = client.get('/os/work').text
    for id_ in ('agent-queue', 'local-queue-next', 'local-queue-refresh', 'local-queue-jobs'):
        assert f'id="{id_}"' in page
