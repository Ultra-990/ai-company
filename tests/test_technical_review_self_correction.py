from copy import deepcopy
import json

import pytest

from scripts import technical_review_self_correction as repair
from tests.test_technical_review_holdout import content, run_fixture


def audit(review, bad=False):
    return {'assessments': [
        {'id': key, 'verdict': 'needs_revision' if bad and key == 'top_fixes' else 'supported',
         'issue_quote': 'fix' if bad and key == 'top_fixes' else '',
         'reason': 'This is an explicitly synthetic audit fixture.', 'evidence_quotes': []}
        for key in repair.units(review)]}


@pytest.fixture
def experiment(tmp_path, monkeypatch):
    source, _, _, _ = run_fixture(tmp_path, monkeypatch, [content()])
    original = repair.lab.check_response(content(), (source/'article.md').read_text(), repair.base.load(source/'sources.json'))
    config = repair.base.load(source/'manifest.json')['configuration']
    monkeypatch.setattr(repair.lab, 'configuration', lambda: config)
    monkeypatch.setattr(repair.lab, 'check_idle', lambda: {'docker': 'empty'})
    outputs = [audit(original, True)]
    changed = original.model_copy(deep=True); changed.top_fixes = ['Preserve an explicitly bounded correction.']
    outputs += [changed.model_dump(), audit(changed)]
    calls = []
    class Batch:
        def __init__(self, config, maximum):
            assert maximum == 3
            self.calls = []
        def call(self, out, name, system, user, schema, *, final=False):
            calls.append(name)
            raw = outputs[len(calls)-1]
            response = {'content': raw if isinstance(raw, str) else json.dumps(raw),
                        'model': config['model'], 'digest': config['digest'], 'elapsed_seconds': .1}
            repair.lab.save(out/(name+'-request.json'), {'system': system, 'user': user, 'format': schema})
            repair.lab.save(out/(name+'-response.json'), response)
            self.calls.append({'stage': name, 'keep_alive_seconds': 0 if final else 3,
                               'elapsed_seconds': .1, 'timings_ns': {}})
            return response['content']
        def close(self): return {'calls': self.calls, 'idle_after': True}
    monkeypatch.setattr(repair, 'RetainedBatch', Batch)
    return source, tmp_path, outputs, calls, changed


def test_bounded_correction_and_recheck_preserve_full_authorship(experiment):
    source, root, outputs, calls, changed = experiment
    before = {p.name: p.read_bytes() for p in source.iterdir() if p.is_file()}
    out, report = repair.run(source, root=root)
    assert report['status'] == 'pending_independent_review'
    assert calls == ['audit', 'writer', 'final-audit']
    assert repair.verify(out)['model_calls'] == 3
    assert repair.base.load(out/'review.json') == changed.model_dump()
    assert {p.name: p.read_bytes() for p in source.iterdir() if p.is_file()} == before
    request = repair.base.load(out/'writer-request.json')
    assert 'independent-development-assessment' not in json.dumps(request)
    assert report['accepted'] is report['autonomy_qualified'] is False


@pytest.mark.parametrize('failure', ['audit_schema', 'audit_quote', 'writer_schema', 'final_schema', 'unchanged', 'still_bad', 'no_repair'])
def test_honest_stops_and_no_extra_calls(experiment, failure):
    source, root, outputs, calls, changed = experiment
    expected_calls = 1 if failure in ('audit_schema', 'audit_quote', 'no_repair') else 2 if failure in ('writer_schema', 'unchanged') else 3
    expected_status = 'failed'
    if failure == 'audit_schema': outputs[0] = '{}'
    elif failure == 'audit_quote': outputs[0]['assessments'][0]['evidence_quotes'] = [{'source_id': 'pilot', 'quote': 'Invented evidence.'}]
    elif failure == 'writer_schema': outputs[1] = '{}'
    elif failure == 'final_schema': outputs[2] = '{}'
    elif failure == 'unchanged': outputs[1] = json.loads(content()); expected_status = 'unchanged_revision'
    elif failure == 'still_bad':
        outputs[2]['assessments'][0].update(verdict='uncertain', issue_quote='future change RAG')
        expected_status = 'needs_revision'
    elif failure == 'no_repair':
        outputs[0] = audit(repair.lab.Review.model_validate(json.loads(content())))
        expected_status = 'no_repair_requested'
    out, report = repair.run(source, root=root)
    assert report['status'] == expected_status
    assert len(calls) == expected_calls
    assert repair.verify(out)['status'] == expected_status


@pytest.mark.parametrize('fault', ['missing_unit', 'duplicate_unit', 'wrong_quote', 'wrong_source'])
def test_audit_must_cover_actual_review_and_literal_evidence(fault):
    review = repair.lab.Review.model_validate(json.loads(content()))
    value = audit(review, True)
    if fault == 'missing_unit': value['assessments'].pop()
    elif fault == 'duplicate_unit': value['assessments'][1] = deepcopy(value['assessments'][0])
    elif fault == 'wrong_quote': next(row for row in value['assessments'] if row['id'] == 'top_fixes')['issue_quote'] = 'not in review'
    else: value['assessments'][0]['evidence_quotes'] = [{'source_id': 'invented', 'quote': 'A quote.'}]
    with pytest.raises(ValueError): repair.audit_value(json.dumps(value), review, [])


def test_writer_cannot_remove_a_supported_finding(experiment):
    source, root, outputs, calls, _ = experiment
    outputs[1]['comments'].pop(0)
    out, report = repair.run(source, root=root)
    assert report['status'] == 'failed'
    assert len(calls) == 2
    assert report['error'] == 'Preserve comments that the source audit marked supported'
    assert repair.verify(out)['status'] == 'failed'


@pytest.mark.parametrize('fault', ['manual_hint', 'changed_export', 'changed_parent', 'budget', 'author', 'extra_call', 'wrong_terminal'])
def test_verifier_rejects_changed_provenance_and_false_outcomes(experiment, fault):
    source, root, _, _, _ = experiment
    out, report = repair.run(source, root=root)
    if fault == 'manual_hint':
        name = 'writer-request.json'; value = repair.base.load(out/name)
        value['system'] += '\nAn examiner wrote a replacement for you.'
    elif fault == 'changed_export':
        name = 'review.json'; value = repair.base.load(out/name); value['top_fixes'] = ['A manual replacement.']
    elif fault == 'changed_parent':
        (source/'review.md').write_text('Tampered source'); name = None
    elif fault == 'budget':
        name = 'manifest.json'; value = repair.base.load(out/name); value['max_model_calls'] = 4
    elif fault == 'author':
        name = 'writer-response.json'; value = repair.base.load(out/name); value['digest'] = '0'*64
    elif fault == 'extra_call': name = 'fourth-request.json'; value = {}
    else: name = None; report['status'] = 'no_repair_requested'
    if name:
        repair.lab.save(out/name, value)
        report['artifacts'][name] = repair.base.digest(out/name)
        if name == 'manifest.json': report['manifest_sha256'] = repair.base.digest(out/name)
    repair.lab.save(out/'report.json', report)
    with pytest.raises(ValueError): repair.verify(out)
