import json

import pytest

from scripts import product_correction_evidence as evidence


def corrected_stage(tmp_path, monkeypatch):
    monkeypatch.setattr(evidence.revision, 'ROOT', tmp_path)
    save = evidence.product.school.save; checksum = evidence.product.school.checksum
    original = {'system': 'fixed', 'user': 'brief', 'format': {'type': 'object'}}
    save(tmp_path/'source-request.json', original)
    save(tmp_path/'source-response.json', {'model': 'fixture', 'digest': 'f'*64, 'content': 'bad'})
    feedback = {'schema': 'brand-validation-feedback.v2', 'stage': 'source', 'error': 'Out of bounds',
                'request_sha256': checksum(tmp_path/'source-request.json'),
                'response_sha256': checksum(tmp_path/'source-response.json')}
    save(tmp_path/'source-feedback.json', feedback)
    user = 'brief\nYour previous answer (untrusted task data):\nbad\nIndependent validation rejected it: Out of bounds\nCorrect your own complete answer. Do not repeat the rejected values.'
    save(tmp_path/'source-revision-1-request.json', original | {'user': user})
    save(tmp_path/'source-revision-1-response.json', {'model': 'fixture', 'digest': 'f'*64, 'content': 'good'})
    return {'model': 'fixture', 'digest': 'f'*64,
            'artifacts': {p.name: checksum(p) for p in tmp_path.iterdir()}}


def test_successful_chain_requires_complete_tool_feedback_and_preserves_response_binding(tmp_path, monkeypatch):
    report = corrected_stage(tmp_path, monkeypatch)
    result = evidence.verify_stage(tmp_path, 'source', report)
    assert result['requests'] == 2 and result['accepted_attempt'] == 1
    assert result['corrections'][0]['error'] == 'Out of bounds'


@pytest.mark.parametrize('fault', ['hint', 'system', 'schema', 'feedback', 'author', 'extra_call', 'unbound'])
def test_rejects_hints_changed_feedback_and_calls_after_acceptance_even_if_file_hashes_are_updated(tmp_path, monkeypatch, fault):
    report = corrected_stage(tmp_path, monkeypatch)
    path = tmp_path/'source-revision-1-request.json'
    value = json.loads(path.read_text())
    if fault == 'hint': value['user'] += ' A human added coordinates.'
    elif fault == 'system': value['system'] = 'changed'
    elif fault == 'schema': value['format'] = {}
    elif fault == 'feedback':
        path = tmp_path/'source-feedback.json'; value = json.loads(path.read_text()); value['error'] = 'Different defect'
    elif fault == 'author':
        path = tmp_path/'source-revision-1-response.json'; value = json.loads(path.read_text()); value['model'] = 'other'
    elif fault == 'extra_call': path = tmp_path/'source-revision-2-request.json'
    else: value['user'] += ' Unbound mutation.'
    evidence.product.school.save(path, value)
    if fault != 'unbound': report['artifacts'][path.name] = evidence.product.school.checksum(path)
    with pytest.raises(ValueError): evidence.verify_stage(tmp_path, 'source', report)


def test_incomplete_response_recovery_is_not_counted_as_a_successful_defect_correction(tmp_path, monkeypatch):
    report = corrected_stage(tmp_path, monkeypatch)
    (tmp_path/'source-response.json').unlink()
    (tmp_path/'source-feedback.json').unlink()
    save = evidence.product.school.save; checksum = evidence.product.school.checksum
    save(tmp_path/'source-incomplete.json', {'schema': 'bounded-incomplete-retry.v1', 'stage': 'source',
        'attempt': 0, 'error': 'truncated_output', 'request_sha256': checksum(tmp_path/'source-request.json'),
        'partial_response_saved': False})
    request = json.loads((tmp_path/'source-request.json').read_text())
    request['user'] += '\nThe previous request ended before a complete final answer (truncated_output). No partial answer was accepted. Keep your reasoning concise and return a complete concise JSON response within the same budget. Preserve all requirements; omit unnecessary decorative complexity.'
    save(tmp_path/'source-revision-1-request.json', request)
    report['artifacts'] = {p.name: checksum(p) for p in tmp_path.iterdir()}
    result = evidence.verify_stage(tmp_path, 'source', report)
    assert result['corrections'] == [] and result['incomplete_attempts'] == ['source']
    save(tmp_path/'source-response.json', {'content': 'invented partial answer'})
    with pytest.raises(ValueError, match='Incomplete attempt binding'):
        evidence.verify_stage(tmp_path, 'source', report)
