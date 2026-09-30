from copy import deepcopy
import json

import pytest

from scripts import technical_review_holdout as holdout
from scripts import technical_review_protocol as protocol


def content():
    return json.dumps({'comments': [
        {'line': line, 'quote': holdout.ARTICLE.splitlines()[line-1],
         'severity': 'major', 'issue': issue, 'recommendation': issue,
         'source_ids': ['pilot']} for line, issue in (
             (3, 'future change RAG'), (4, 'QLoRA base adapter'),
             (5, 'checkpoint test leakage'), (6, 'cost retrieval comparison'))],
        'top_fixes': ['fix'], 'citation_needs': [], 'additions': ['example'],
        'verdict': 'needs_technical_revision', 'reader_intent': 'intent', 'uncertainty': 'limits'})


def run_fixture(tmp_path, monkeypatch, outputs, fail_preflight=None):
    calls = []
    checks = []
    config = {'model': 'qwen3.8:27b', 'digest': 'a'*64,
              'num_ctx': 8192, 'num_predict': 3500, 'num_thread': 4,
              'timeout_seconds': 180, 'format': protocol.lab.Review.model_json_schema()}

    class Provider:
        def complete(self, messages):
            calls.append(deepcopy(messages))
            return {'model': config['model'], 'digest': config['digest'],
                    'content': outputs[len(calls)-1], 'elapsed_seconds': .1, 'eval_count': 10}

    def preflight():
        checks.append(True)
        if len(checks) == fail_preflight:
            raise ValueError('active_containers')
        return {'docker': 'empty'}

    path, report = protocol.run(holdout.ARTICLE, holdout.SOURCES, config, root=tmp_path,
                                provider=Provider(), preflight=preflight)
    return path, report, calls, checks


def test_holdout_expectations_are_not_in_model_request():
    request = json.dumps({'article': holdout.ARTICLE, 'sources': holdout.SOURCES})
    assert 'EXPECTED' not in request and str(sorted(holdout.EXPECTED)) not in request
    assert 'EDITORIAL TRAP' in request


def test_last_bounded_correction_is_validated_and_exported(tmp_path, monkeypatch):
    path, report, calls, checks = run_fixture(tmp_path, monkeypatch, ['{}', '{}', content()])
    assert len(calls) == len(checks) == 3
    assert report['status'] == 'structurally_valid'
    assert report['final_response'] == 'response-2.json'
    assert protocol.verify(path)[1].model_dump() == json.loads(content())
    assert protocol.load(path/'response-0.json')['content'] == '{}'
    assert calls[2][-2] == {'role': 'assistant', 'content': '{}'}
    assert len(calls[2]) == 4  # no expanding conversation or examiner rubric
    assert 'expected_issue_lines' not in json.dumps(calls)


def test_exhaustion_is_an_explicit_terminal_record(tmp_path, monkeypatch):
    path, report, calls, checks = run_fixture(tmp_path, monkeypatch, ['{}']*3)
    assert report['status'] == 'exhausted'
    assert len(calls) == len(checks) == 3
    assert protocol.verify(path)[1] is None
    assert not (path/'review.md').exists()


def test_first_valid_answer_stops_and_preserves_literal_export(tmp_path, monkeypatch):
    path, report, calls, checks = run_fixture(tmp_path, monkeypatch, [content()])
    assert len(calls) == len(checks) == 1
    assert protocol.verify(path)[1].model_dump() == json.loads(content())
    (path/'review.md').write_text('Changed editorial text')
    with pytest.raises(ValueError, match='literal model review'):
        protocol.verify(path)


def test_each_correction_rechecks_resources_and_stops_without_retry(tmp_path, monkeypatch):
    path, report, calls, checks = run_fixture(tmp_path, monkeypatch, ['{}'], fail_preflight=2)
    assert report['status'] == 'infrastructure_error'
    assert len(calls) == 1 and len(checks) == 2
    assert protocol.verify(path)[1] is None


def test_verifier_rejects_unrecorded_extra_model_call(tmp_path, monkeypatch):
    path, _, _, _ = run_fixture(tmp_path, monkeypatch, [content()])
    (path/'response-1.json').write_text((path/'response-0.json').read_text())
    with pytest.raises(ValueError, match='Unrecorded'):
        protocol.verify(path)


def test_verifier_rejects_changed_model_even_with_updated_file_hash(tmp_path, monkeypatch):
    path, report, _, _ = run_fixture(tmp_path, monkeypatch, [content()])
    response = protocol.load(path/'response-0.json')
    response['digest'] = 'b'*64
    protocol.lab.save(path/'response-0.json', response)
    report['attempts'][0]['response_sha256'] = protocol.digest(path/'response-0.json')
    protocol.lab.save(path/'report.json', report)
    with pytest.raises(ValueError, match='model'):
        protocol.verify(path)


@pytest.mark.parametrize('mutation', ['accepted_attempt', 'feedback', 'request', 'rejected_response', 'parity'])
def test_verifier_rejects_changed_correction_chain(tmp_path, monkeypatch, mutation):
    path, report, _, _ = run_fixture(tmp_path, monkeypatch, ['{}', content()])
    if mutation == 'accepted_attempt':
        report['final_response'] = 'response-0.json'
        protocol.lab.save(path/'report.json', report)
    elif mutation == 'parity':
        report['parity_proven'] = True
        protocol.lab.save(path/'report.json', report)
    elif mutation == 'feedback':
        protocol.lab.save(path/'feedback-0.json', {'error': 'An examiner supplied a new answer'})
    elif mutation == 'request':
        request = protocol.load(path/'request-1.json')
        request[-1]['content'] += '\nUse the examiner answer.'
        protocol.lab.save(path/'request-1.json', request)
        report['attempts'][1]['request_sha256'] = protocol.digest(path/'request-1.json')
        protocol.lab.save(path/'report.json', report)
    else:
        response = protocol.load(path/'response-0.json')
        response['content'] = content()
        protocol.lab.save(path/'response-0.json', response)
    with pytest.raises(ValueError):
        protocol.verify(path)
