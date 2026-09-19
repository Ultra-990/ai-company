"""Small fixture-only diagnostics; never call a model, external service or runner."""
import json

import pytest
from sqlalchemy import func, select

from app.models.artifact import Artifact
from app.models.work_order import WorkOrder
from app.models.local_inference import LocalInference
from app.services.api_contract_probe import inspect, resolve, tokens
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS

URL = '/api/upwork-orders/contract-probe'


def fixture(body=None, **overrides):
    return dict(response_text=json.dumps(body if body is not None else {'data': {'items': [{'name': 'Synthetic', 'total': 2576}]}}),
                observed_status=200, expected_status=200,
                bindings=[dict(name='total', pointer='/data/items/0/total', expected_type='number')]) | overrides


def test_example_is_fixture_evidence_only_without_project_mutations(client, task_repository):
    with task_repository._session_factory() as s:
        before = [s.scalar(select(func.count()).select_from(m)) for m in (Artifact, WorkOrder, LocalInference)]
    response = client.post(URL, json=fixture(), headers=OWNER_HEADERS)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['outcome'] == 'passed'
    assert all(data[k] is False for k in ('network_used', 'model_used', 'application_executed', 'release_evidence'))
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert 'Synthetic' not in response.text and '2576' not in response.text
    with task_repository._session_factory() as s:
        assert before == [s.scalar(select(func.count()).select_from(m)) for m in (Artifact, WorkOrder, LocalInference)]


@pytest.mark.parametrize('body,pointer,kind,required,nonempty,code,outcome', [
    ({'data': []}, '/data/0/name', 'string', True, False, 'missing_field', 'failed'),
    ({'data': []}, '/data/0/name', 'string', False, False, 'missing_field', 'warning'),
    ({'x': None}, '/x', 'string', True, False, 'type_mismatch', 'failed'),
    ({'x': None}, '/x', 'null', True, False, 'binding_matches', 'passed'),
    ({'x': True}, '/x', 'integer', True, False, 'type_mismatch', 'failed'),
    ({'x': '2576'}, '/x', 'number', True, False, 'type_mismatch', 'failed'),
    ({'x': []}, '/x', 'array', True, True, 'empty_value', 'failed'),
    ({'x': ''}, '/x', 'string', True, True, 'empty_value', 'failed'),
    ({'x': 0}, '/x', 'number', True, True, 'binding_matches', 'passed'),
    ({'x': False}, '/x', 'boolean', True, True, 'binding_matches', 'passed'),
])
def test_binding_semantics(body, pointer, kind, required, nonempty, code, outcome):
    data = inspect(fixture(body, bindings=[dict(name='field', pointer=pointer, expected_type=kind,
                                               required=required, nonempty=nonempty)]))
    assert data['outcome'] == outcome and data['checks'][-1]['code'] == code


def test_pointer_object_array_and_escaping():
    data = {'': 0, 'a/b': {'m~n': [3]}, '~1': 'escape', '01': 'key'}
    assert resolve(data, '') == (True, data)
    assert resolve(data, '/') == (True, 0)
    assert resolve(data, '/a~1b/m~0n/0') == (True, 3)
    assert resolve(data, '/~01') == (True, 'escape')
    assert resolve(data, '/01') == (True, 'key')
    for bad in ('/01', '/-1', '/-', '/99', '/١'):
        assert resolve([3], bad) == (False, None)


@pytest.mark.parametrize('pointer', ['$.data', '#/data', 'https://example.com', '/x~2', '/x~', '/' * 17, '/\x00'])
def test_invalid_pointers(pointer):
    with pytest.raises(ValueError):
        tokens(pointer)


@pytest.mark.parametrize('body', ['<html>PRIVATE-login</html>', '{"x":1,"x":2}', '{"x":NaN}',
    '{"x":1e999}', '{"x":9007199254740993}', '[' * 129 + '0' + ']' * 129, 'not-json'])
def test_invalid_json_is_diagnostic_not_exception_or_data_echo(client, body):
    r = client.post(URL, headers=OWNER_HEADERS, json=fixture(response_text=body))
    assert r.status_code == 200, r.text
    assert r.json()['outcome'] == 'failed' and r.json()['checks'][-1]['code'] == 'invalid_json'
    assert 'PRIVATE' not in r.text


def test_status_failure_remains_failure_even_when_fields_match():
    result = inspect(fixture(observed_status=401))
    assert result['outcome'] == 'failed' and result['checks'][0]['code'] == 'status_mismatch'
    assert result['checks'][1]['outcome'] == 'passed'


@pytest.mark.parametrize('changes', [dict(response_text='ą' * 17000), dict(url='http://localhost'),
    dict(headers={'Authorization': 'PRIVATE-SECRET'}), dict(bindings=[]), dict(observed_status=True),
    dict(bindings=[dict(name='x', pointer='', expected_type='object')] * 2),
    dict(response_text='\ud800'), dict(bindings=[dict(name='x', pointer='', expected_type='object')] * 13)])
def test_invalid_requests_never_echo_data(client, changes):
    raw = json.dumps(fixture(**changes), ensure_ascii=False).encode('utf-8', 'backslashreplace')
    r = client.post(URL, headers=OWNER_HEADERS, content=raw)
    assert r.status_code == 422, r.text
    assert 'PRIVATE-SECRET' not in r.text and 'response_text":"' not in r.text


def test_body_limits_duplicate_envelope_keys_and_rbac(client):
    assert client.post(URL, headers=OWNER_HEADERS, content='x' * (96 * 1024 + 1)).status_code == 413
    assert client.post(URL, headers=OWNER_HEADERS, content='{"bindings":[],"bindings":[]}').status_code == 422
    for headers, code in (({}, 401), (WORKER_HEADERS, 403)):
        assert client.post(URL, headers=headers, json=fixture()).status_code == code


def test_upwork_page_exposes_probe(client):
    page = client.get('/os/upwork').text
    assert 'id="contract-probe"' in page and 'api-contract-probe.js?v=1' in page


def test_openapi_has_resolvable_inline_request_schema(client):
    schema = client.get('/openapi.json').json()['paths'][URL]['post']['requestBody']['content']['application/json']['schema']
    assert '$ref' not in json.dumps(schema)
    assert schema['properties']['bindings']['items']['properties']['pointer']['maxLength'] == 256
    assert 'api-contract' in client.get('/os/help').text
