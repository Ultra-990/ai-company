import json
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.models.artifact import Artifact
from app.models.work_order import WorkOrder
from app.services import acceptance_cases as service
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS
from tests.test_package_runner import package, fake_runner, FILES


EXAMPLE = dict(criterion_id='a' * 64, title='Godziny razy stawka',
               path='/api/estimate?hours=8&rate=322', status=200, json_field='total', expected=2576)


def plan_body(client, package_body):
    base = f"/api/tasks/{package_body['task_id']}/workspace-packages/{package_body['package_id']}"
    r = client.get(base + '/requirements', headers=OWNER_HEADERS)
    assert r.status_code == 200, r.text
    data = r.json()
    return base + '/acceptance-plans', dict(request_id=str(uuid4()),
        source_checksum=data['source_checksum'], scope_checksum=data['scope_checksum'],
        cases=[EXAMPLE | {'criterion_id': data['criteria'][0]['id']}])


@pytest.mark.parametrize('change', [dict(path='http://localhost:8000/'), dict(path='/etc/passwd'),
    dict(path='/api/../x'), dict(path='/api/x\n'), dict(status=True), dict(status='200'),
    dict(status=500), dict(expected=10**1000), dict(expected=float('inf')),
    dict(expected=float('nan')), dict(expected='a' * 501), dict(expected={'nested': 1}),
    dict(json_field='a[0]'), dict(json_field=None), dict(method='POST'), dict(title='   ')])
def test_case_refuses_arbitrary_code_urls_and_unbounded_input(change):
    with pytest.raises(ValidationError):
        service.Case.model_validate(EXAMPLE | change)


@pytest.mark.parametrize('body,passed,reason', [
    ('{"total":2576}', True, 'value_matches'), ('{"total":2576.0}', True, 'value_matches'),
    ('{"total":330}', False, 'value_mismatch'), ('{"total":"2576"}', False, 'value_mismatch'),
    ('{"total":true}', False, 'value_mismatch'), ('{}', False, 'missing_json_field'),
    ('{"total":2576,"total":2576}', False, 'invalid_json_response'),
    ('{"total":NaN}', False, 'invalid_json_response'), ('<html>error</html>', False, 'invalid_json_response'),
    (' ' * 12001, False, 'invalid_json_response')])
def test_evaluator_uses_strict_expected_values(body, passed, reason):
    result = service.evaluate(EXAMPLE, {'status': 200, 'body': body})
    assert result['passed'] is passed and result['reason'] == reason


def test_json_null_boolean_nested_values_and_status_only():
    assert service.evaluate(EXAMPLE | {'json_field': 'data.total'}, {'status': 200, 'body': '{"data":{"total":2576}}'})['passed']
    null = EXAMPLE | {'expected': None}
    assert service.evaluate(null, {'status': 200, 'body': '{"total":null}'})['passed']
    assert not service.evaluate(null, {'status': 200, 'body': '{}'})['passed']
    assert not service.evaluate(EXAMPLE | {'expected': True}, {'status': 200, 'body': '{"total":1}'})['passed']
    assert service.evaluate(EXAMPLE | {'json_field': None, 'expected': None}, {'status': 200})['passed']
    assert service.evaluate(EXAMPLE, {'status': 400})['reason'] == 'status_mismatch'
    assert service.evaluate(EXAMPLE, [])['reason'] == 'invalid_http_response'


def test_owner_can_prepare_immutable_plan_without_execution(client, fake_runner):
    p = package(client)
    path, body = plan_body(client, p)
    for headers, status in (({}, 401), (WORKER_HEADERS, 403)):
        assert client.get(path, headers=headers).status_code == status
        assert client.post(path, headers=headers, json=body).status_code == status
    first = client.post(path, headers=OWNER_HEADERS, json=body)
    assert first.status_code == 200, first.text
    assert not first.json()['is_test_result'] and not first.json()['execution_enabled']
    assert client.post(path, headers=OWNER_HEADERS, json=body).json() == first.json()
    assert client.post(path, headers=OWNER_HEADERS, json=body | {'cases': [body['cases'][0] | {'expected': 330}]}).status_code == 409
    listing = client.get(path, headers=OWNER_HEADERS)
    assert listing.headers['cache-control'] == 'no-store'
    assert listing.json()['plans'] == [first.json()] and fake_runner.calls == 0
    for cases in ([], body['cases'] * 5):
        assert client.post(path, headers=OWNER_HEADERS, json=body | {'cases': cases}).status_code == 422
    assert client.post(path, headers=OWNER_HEADERS, json=body | {'cases': body['cases'] * 2}).status_code == 409


def test_plan_survives_source_revision_but_not_scope_changes(client, task_repository):
    p = package(client)
    path, body = plan_body(client, p)
    plan = client.post(path, headers=OWNER_HEADERS, json=body).json()
    fresh = client.post(f"/api/tasks/{p['task_id']}/workspace-packages", headers=OWNER_HEADERS,
        json={'purpose': 'Poprawiona wersja', 'files': FILES | {'README.md': 'Nowa instrukcja'}}).json()
    fresh_path = path.replace(f"packages/{p['package_id']}/", f"packages/{fresh['artifact_id']}/")
    assert client.get(fresh_path, headers=OWNER_HEADERS).json()['plans'][0]['checksum'] == plan['checksum']
    with task_repository._session_factory() as s:
        source = s.get(Artifact, p['package_id'])
        order = s.scalar(select(WorkOrder).where(WorkOrder.project_id == source.project_id))
        order.brief = order.brief | {'goal': 'Zmiana zakresu wymaga nowego planu.'}
        s.commit()
    assert client.get(path, headers=OWNER_HEADERS).json()['plans'] == [{'id': plan['id'], 'invalid': True}]
    assert client.post(path, headers=OWNER_HEADERS, json=body).status_code == 409


def test_execution_configuration_fails_closed(tmp_path, monkeypatch):
    path = tmp_path / 'acceptance.json'
    monkeypatch.setattr(service, 'EXECUTION_CONFIG', path)
    assert not service.execution_enabled()
    for value in ([], None, {'enabled': 'true'}, {'enabled': 1}, {'enabled': False}):
        path.write_text(json.dumps(value))
        assert not service.execution_enabled()
    path.write_text('{"enabled":true}')
    assert service.execution_enabled()
