import json

import pytest
from sqlalchemy import select, func

from app.models.artifact import Artifact
from app.models.task import Task, TaskAttempt, TaskStatus
from app.models.organization_os import Agent
from app.services.agent_packets import digest, RECEIPT_NAME
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS
from tests.test_agent_teams import setup, order, delegate


def assigned(client):
    setup(client)
    saved = order(client)
    result = delegate(client, saved)
    assert result.status_code == 200
    return result.json()


def packet(client, task):
    response = client.post(f'/api/tasks/{task}/agent-packet', headers=OWNER_HEADERS)
    assert response.status_code == 200, response.text
    assert response.headers['cache-control'] == 'no-store'
    return response.json()


def submit(client, p, **changes):
    body = dict(packet_id=p['packet_id'], packet_checksum=p['checksum'],
                result_content='Rzeczywista specyfikacja. Testów nie uruchamiano.', source_note='Właściciel — praca ręczna')
    return client.post(f"/api/tasks/{p['task_id']}/agent-results", headers=OWNER_HEADERS, json=body | changes)


def review(client, task_id, accepted):
    data = client.get(f'/api/tasks/{task_id}/review', headers=OWNER_HEADERS).json()
    return client.post(f'/api/tasks/{task_id}/review', headers=OWNER_HEADERS, json={
        'attempt_id': data['id'], 'result_checksum': data['result_checksum'], 'accepted': accepted,
        'reason': 'Sprawdzony zakres' if accepted else 'Uzupełnij zakres mobilny',
        'evidence': ['Ręczny przegląd specyfikacji: lista wymagań i wyłączeń'],
    })


def test_manual_result_review_and_next_stage_have_versioned_context(client, task_repository):
    saved = assigned(client)
    first, second = [t['id'] for t in saved['tasks'][:2]]
    assert client.post(f'/api/tasks/{second}/agent-packet', headers=OWNER_HEADERS).status_code == 409
    p = packet(client, first)
    assert packet(client, first) == p
    assert p['packet']['role'] == 'analyst'
    assert p['model_invoked'] is False
    assert p['packet']['accepted_predecessor'] is None
    with task_repository._session_factory() as s:
        assert s.scalar(select(func.count()).select_from(TaskAttempt)) == 0
    response = submit(client, p)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['awaiting_review'] and not result['model_invoked']
    assert submit(client, p).json()['attempt_id'] == result['attempt_id']
    assert submit(client, p, result_content='Inny wynik').status_code == 409
    task = task_repository.get(first)
    assert task.status is TaskStatus.IN_PROGRESS and task.progress == 0 and task.queued_at is None
    with task_repository._session_factory() as s:
        assert s.get(TaskAttempt, result['attempt_id']).worker_id == 'owner-import'
        assert s.scalar(select(func.count()).select_from(TaskAttempt)) == 1
    assert client.post(f'/api/tasks/{second}/agent-packet', headers=OWNER_HEADERS).status_code == 409
    assert review(client, first, True).status_code == 200
    assert task_repository.get(first).progress == 100
    p2 = packet(client, second)
    previous = p2['packet']['accepted_predecessor']
    assert previous['attempt_id'] == result['attempt_id'] and previous['checksum'] == result['result_checksum']
    assert previous['content'].startswith('Rzeczywista specyfikacja')
    assert p2['packet']['role'] == 'builder'
    assert task_repository.list_ready() == []
    assert submit(client, p).json()['replayed'] is True


def test_rejected_result_can_be_corrected_without_queue_and_without_overwriting(client, task_repository):
    first = assigned(client)['tasks'][0]['id']
    p = packet(client, first)
    original = submit(client, p).json()
    assert review(client, first, False).status_code == 200
    revised = packet(client, first)
    assert revised['packet_id'] != p['packet_id']
    assert revised['packet']['revision']['previous_attempt_id'] == original['attempt_id']
    assert revised['packet']['revision']['rejection_reason'] == 'Uzupełnij zakres mobilny'
    corrected = submit(client, revised, result_content='Poprawka: zakres mobilny').json()
    assert corrected['attempt_id'] != original['attempt_id']
    assert review(client, first, True).status_code == 200
    with task_repository._session_factory() as s:
        assert s.get(TaskAttempt, original['attempt_id']).verification_status == 'rejected'
        assert s.get(TaskAttempt, corrected['attempt_id']).verification_status == 'accepted'
        assert s.get(Task, first).queued_at is None


@pytest.mark.parametrize('change', ['content','brief','actor','title'])
def test_stale_or_tampered_packet_never_creates_attempt(client, task_repository, change):
    saved = assigned(client)
    first = saved['tasks'][0]['id']
    p = packet(client, first)
    with task_repository._session_factory() as s:
        if change == 'content':
            s.get(Artifact, p['packet_id']).content = '{}'
        elif change == 'brief':
            s.get(Task, first).description = 'Zmieniony cel'
        elif change == 'title':
            s.get(Task, first).title = 'Inny tytuł'
        else:
            s.get(Agent, saved['tasks'][0]['delegation']['worker']['id']).active = False
        s.commit()
    assert submit(client, p).status_code == 409
    with task_repository._session_factory() as s:
        assert s.scalar(select(func.count()).select_from(TaskAttempt)) == 0
        assert s.get(Task, first).status is TaskStatus.PENDING


def test_binding_validation_and_receipt_integrity(client, task_repository):
    saved = assigned(client)
    first, second = [t['id'] for t in saved['tasks'][:2]]
    p = packet(client, first)
    assert client.get(f"/api/tasks/{second}/agent-packets/{p['packet_id']}", headers=OWNER_HEADERS).status_code == 404
    assert submit(client, p, packet_checksum='0'*64).status_code == 409
    assert submit(client, p, result_content='\x00').status_code == 422
    assert submit(client, p, result_content='x'*32001).status_code == 422
    assert submit(client, p, source_note=' ').status_code == 422
    assert submit(client, p, approved=True).status_code == 422
    assert submit(client, p).status_code == 200
    with task_repository._session_factory() as s:
        receipt = s.scalar(select(Artifact).where(Artifact.name == f"{RECEIPT_NAME}:{p['packet_id']}"))
        receipt.content = '{}'
        receipt.checksum = digest(receipt.content)
        s.commit()
    assert submit(client, p).status_code == 409


@pytest.mark.parametrize('headers,status', [({},401),(WORKER_HEADERS,403)])
def test_owner_only(client, headers, status):
    assert client.post('/api/tasks/1/agent-packet', headers=headers).status_code == status
    assert client.get('/api/tasks/1/agent-packets/1', headers=headers).status_code == status
    assert client.post('/api/tasks/1/agent-results', headers=headers, json={}).status_code == status
    assert client.get('/api/tasks/1/agent-packets/1/prompt', headers=headers).status_code == status


def test_workbench_exposes_handoff_and_review_without_extra_login(client):
    page = client.get('/os/work').text
    for id_ in ('agent-session','agent-result-form','agent-review-form','agent-close','agent-prompt'):
        assert f'id="{id_}"' in page


def test_local_prompt_is_bound_read_only_and_rejects_stale_context(client, task_repository):
    task_id = assigned(client)['tasks'][0]['id']
    saved = packet(client, task_id)
    path = f'/api/tasks/{task_id}/agent-packets/{saved["packet_id"]}/prompt'
    with task_repository._session_factory() as session:
        attempts_before = session.scalar(select(func.count()).select_from(TaskAttempt))
        artifacts_before = session.scalar(select(func.count()).select_from(Artifact))
    response = client.get(path, headers=OWNER_HEADERS)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['model_invoked'] is False
    assert result['packet_checksum'] == saved['checksum']
    assert [m['role'] for m in result['messages']] == ['system','user']
    assert saved['packet']['task_context']['title'] in result['text']
    assert '32000' in result['messages'][0]['content']
    assert response.headers['cache-control'] == 'no-store'
    assert client.get(path, headers=OWNER_HEADERS).json() == result
    with task_repository._session_factory() as session:
        assert session.scalar(select(func.count()).select_from(TaskAttempt)) == attempts_before
        assert session.scalar(select(func.count()).select_from(Artifact)) == artifacts_before
        session.get(Task, task_id).title = 'Zmieniony zakres'
        session.commit()
    assert client.get(path, headers=OWNER_HEADERS).status_code == 409
    assert client.get(f'/api/tasks/{task_id+1000}/agent-packets/{saved["packet_id"]}/prompt', headers=OWNER_HEADERS).status_code == 404


def test_desktop_and_spatial_have_same_primary_business_entries(client):
    from html.parser import HTMLParser
    class Links(HTMLParser):
        def __init__(self):
            super().__init__(); self.urls=set()
        def handle_starttag(self, tag, attrs):
            if tag=='a': self.urls.add(dict(attrs).get('href'))
    for route in ('/os','/os/spatial'):
        links=Links();links.feed(client.get(route).text)
        assert {'/os/work','/os/clients','/os/client-preview'} <= links.urls
