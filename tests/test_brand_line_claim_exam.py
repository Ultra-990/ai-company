import json
from pathlib import Path

import pytest
from scripts import brand_line_claim_exam as exam


def test_frozen_cases_are_contrastive_and_expectations_never_enter_requests():
    assert len(exam.CASES) == 10
    assert {row[2] for row in exam.CASES} == {'single', 'multiple', 'unspecified', 'uncertain'}
    for pair in exam.pairs():
        _, request = exam.request(pair)
        assert 'expected' not in request['user']


def test_equal_profile_budgets_and_no_generation_exam_cases():
    frozen = exam.manifest({'model': 'fixture', 'digest': 'f'*64})
    assert frozen['budget'] == exam.BUDGET and len(frozen['profiles']) == 2
    from scripts import brand_generation_exam as generation
    names = {row['name'].lower() for row in generation.LITERAL_CASES}
    assert all(not any(name in text.lower() for name in names) for _, text, _ in exam.CASES)


def test_run_and_verify_replay_real_v13_validation(tmp_path, monkeypatch):
    monkeypatch.setattr(exam.brand, 'ROOT', tmp_path)
    monkeypatch.setattr(exam.brand.school, 'check_idle', lambda: {})
    monkeypatch.setattr(exam, 'configuration', lambda: {'model': 'fixture', 'digest': 'f'*64})
    class Provider:
        def __init__(self, config): self.config = config
        def complete(self, messages):
            payload = json.loads(messages[-1]['content']); concepts = []
            for key in ('a', 'b'):
                line = payload[key]['line_options'][0]
                concepts.append({'id': key, 'claim_ids': [payload[key]['options'][0]['id']],
                                 'wordmark_line_id': line['id']})
            return {'model': 'fixture', 'digest': 'f'*64, 'content': json.dumps({'concepts': concepts})}
    monkeypatch.setattr(exam, 'OllamaProvider', Provider)
    out, report = exam.run()
    assert report['status'] == 'completed'
    assert len(report['call_preflights']) == 10
    checked = exam.verify(out)
    assert checked['cases_per_arm'] == 10 and checked['scores'] == {'bounded': 10, 'deliberate': 10}
    value = json.loads((out/'bounded-0-request.json').read_text())
    value['user'] += ' expected=multiple'
    exam.brand.school.save(out/'bounded-0-request.json', value)
    report['artifacts']['bounded-0-request.json'] = exam.brand.school.checksum(out/'bounded-0-request.json')
    exam.brand.school.save(out/'report.json', report)
    with pytest.raises(ValueError, match='Prompt includes changed data'): exam.verify(out)


def test_verify_rejects_extra_unbound_or_missing_exam_artifact(tmp_path, monkeypatch):
    monkeypatch.setattr(exam.brand, 'ROOT', tmp_path)
    monkeypatch.setattr(exam.brand.school, 'check_idle', lambda: {})
    monkeypatch.setattr(exam, 'configuration', lambda: {'model': 'fixture', 'digest': 'f'*64})
    class Provider:
        def __init__(self, config): pass
        def complete(self, messages):
            payload = json.loads(messages[-1]['content'])
            return {'model': 'fixture', 'digest': 'f'*64, 'content': json.dumps({'concepts': [
                {'id': key, 'claim_ids': [payload[key]['options'][0]['id']],
                 'wordmark_line_id': payload[key]['line_options'][0]['id']} for key in ('a', 'b')]})}
    monkeypatch.setattr(exam, 'OllamaProvider', Provider)
    out, report = exam.run(); assert exam.verify(out)['cases_per_arm'] == 10
    (out/'eleventh-response.json').write_text('{}')
    with pytest.raises(ValueError, match='artifact set'): exam.verify(out)
    (out/'eleventh-response.json').unlink()
    missing = out/'bounded-0-response.json'; missing.unlink()
    with pytest.raises(ValueError, match='artifact set'): exam.verify(out)
