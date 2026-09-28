import json

import pytest

from scripts import product_stream_probe as probe


def fixture_input(tmp_path, monkeypatch):
    p = probe.product
    monkeypatch.setattr(p, 'ROOT', tmp_path)
    monkeypatch.setattr(probe.revision, 'ROOT', tmp_path)
    config = {'model': 'qwen3.8:27b', 'digest': 'a'*64, 'sampling_profile': 'qwen-deliberate-trial.v1',
              'think': True, 'num_ctx': 16384, 'num_predict': 8192, 'num_thread': 4, 'timeout_seconds': 180}
    monkeypatch.setattr(p, 'configuration', lambda: {'model': 'qwen3.8:27b', 'digest': 'a'*64})
    request = tmp_path/'dimensions-request.json'; p.school.save(request, {'system': 'fixture', 'user': 'fixture', 'format': {}})
    report = probe.exam.definition(probe.exam.LEGACY_CASES[2]) | {'status': 'failed', 'error': 'invalid_stream', 'config': config,
              'artifacts': {request.name: p.school.checksum(request)}}
    p.school.save(tmp_path/'report.json', report)
    return report, request


def test_probe_requires_exact_frozen_failed_request_and_preserves_original_files(tmp_path, monkeypatch):
    _, request = fixture_input(tmp_path, monkeypatch)
    before = request.read_bytes()
    report, path, value = probe.probe_input(tmp_path)
    assert path == request and value['user'] == 'fixture' and report['error'] == 'invalid_stream'
    assert request.read_bytes() == before and not (tmp_path/'dimensions-response.json').exists()


@pytest.mark.parametrize('fault', ['client_brief', 'unrelated_failure', 'oversized_budget', 'wrong_model',
                                  'completed_response', 'multiple_pending', 'changed_request'])
def test_probe_rejects_unbound_or_out_of_scope_replays(tmp_path, monkeypatch, fault):
    report, request = fixture_input(tmp_path, monkeypatch)
    if fault == 'client_brief': report['brief']['family'] = 'private-client'
    elif fault == 'unrelated_failure': report['error'] = 'model_changed'
    elif fault == 'oversized_budget': report['config']['num_predict'] = 8193
    elif fault == 'wrong_model': report['config']['digest'] = 'b'*64
    elif fault == 'completed_response': (tmp_path/'dimensions-response.json').write_text('{}')
    elif fault == 'multiple_pending': (tmp_path/'materials-request.json').write_text('{}')
    else: request.write_text('{}')
    probe.product.school.save(tmp_path/'report.json', report)
    with pytest.raises(ValueError): probe.probe_input(tmp_path)
