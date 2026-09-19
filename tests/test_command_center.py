from uuid import uuid4

from sqlalchemy import select

from app.models.task import TaskAttempt
from app.organization_os.department_operations import OPERATIONS, workflow_for
from tests.conftest import OWNER_HEADERS


def test_new_center_and_archived_views_are_separate(client):
    page = client.get('/os')
    assert page.status_code == 200
    assert 'command.js?v=1' in page.text
    assert 'command-owner' in page.text and 'command-brain' in page.text
    assert '/os/legacy' in page.text and '/os/publishing' in page.text
    assert 'data-media-slot="command-hero"' in page.text
    assert 'organization-os.js?' in client.get('/os/legacy').text
    publisher = client.get('/os/publishing')
    assert publisher.status_code == 200 and 'publishing-token' in publisher.text
    assert 'href="/os" data-home' in publisher.text
    assert publisher.headers['cache-control'] == 'no-store'
    review = client.get('/os/review')
    assert review.status_code == 200 and 'delivery-load' in review.text
    assert 'href="/os" data-home' in review.text
    build = client.get('/os/build')
    assert build.status_code == 200 and 'id="run-form"' in build.text
    assert '/os/build' in page.text
    for response in (page, publisher, review, build):
        assert "form-action 'none'" in response.headers['content-security-policy']
        assert "frame-ancestors 'none'" in response.headers['content-security-policy']


def test_department_actions_target_real_leaves_without_creating_tasks(client):
    units = {u['key']: u for u in client.get('/api/work-orders/options', headers=OWNER_HEADERS).json()['units']}
    before = client.get('/api/organization-os/overview').json()['tasks']
    departments = client.get('/api/organization-os/tree').json()['nodes'][0]['children']
    assert {d['key'] for d in departments} == set(OPERATIONS)
    for d in departments:
        model = d['operating_model']
        assert model['target_key'] in units
        assert model['execution'] == 'planned_human_review'
        assert model['inputs'] and model['outputs'] and model['action_title']
    assert client.get('/api/organization-os/overview').json()['tasks'] == before


def test_department_workflows_persist_real_criteria_and_keep_execution_off(client, task_repository):
    assert client.post('/api/agent-teams/initialize', headers=OWNER_HEADERS).status_code == 200
    options = {u['key']: u['id'] for u in client.get('/api/work-orders/options', headers=OWNER_HEADERS).json()['units']}
    for key, model in OPERATIONS.items():
        payload = dict(request_id=str(uuid4()), title='Izolowana praca działu', goal='Sprawdzić przepływ planowania konkretnego działu.',
                       audience='Właściciel firmy', constraints='Bez modeli, publikacji i operacji na hoście.',
                       organization_unit_id=options[model[4]], acceptance_criteria=['Raport ma źródło i opis ograniczeń.'])
        response = client.post('/api/work-orders', headers=OWNER_HEADERS, json=payload)
        assert response.status_code == 201, response.text
        result = response.json()
        expected = workflow_for(key)
        for index, task in enumerate(result['tasks']):
            assert expected[index][0] in task['title']
            assert task['assigned_role'] == expected[index][1]
            assert task['completion_criterion'] == expected[index][2]
            assert task['status'] == 'pending' and task['progress'] == 0 and not task['queued']
        replay = client.post('/api/work-orders', headers=OWNER_HEADERS, json=payload)
        assert replay.status_code == 200 and replay.json() == result
        assert client.get(f"/api/work-orders/{result['project_id']}", headers=OWNER_HEADERS).json() == result
        delegated = client.post(f"/api/work-orders/{result['project_id']}/delegate", headers=OWNER_HEADERS)
        assert delegated.status_code == 200, delegated.text
        for index, task in enumerate(delegated.json()['tasks']):
            assert task['delegation']['completion_criterion'] == expected[index][2]
            assert task['delegation']['worker']['id'] != task['delegation']['reviewer']['id']
            assert task['delegation']['execution_enabled'] is False
    with task_repository._session_factory() as session:
        assert session.scalar(select(TaskAttempt.id)) is None
