from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts import technical_review_claim_self_correction as repair
from scripts import technical_review_self_correction as v1
from scripts import technical_review_holdout as holdout
from tests.test_technical_review_holdout import content
from tests.test_technical_review_holdout import run_fixture


def review():
    return v1.lab.Review.model_validate(json.loads(content()))


def claim_audit(value, *, bad=None):
    return {'assessments': [
        {'id': claim, 'verdict': 'needs_revision' if claim == bad else 'supported',
         'issue_quote': v1.strings(unit)[-1] if claim == bad else '',
         'reason': 'Synthetic claim-level source audit for protocol testing.', 'evidence_quotes': []}
        for claim, unit in repair.claim_units(value).items()]}


def test_comment_is_split_into_independent_claims_in_stable_order():
    claims = repair.claim_units(review())
    assert list(claims)[:4] == [
        'comment:3:diagnosis', 'comment:3:recommendation',
        'comment:3:severity', 'comment:3:source_grounding']
    assert claims['comment:3:diagnosis']['issue'] == 'future change RAG'
    assert claims['comment:3:recommendation'] == 'future change RAG'
    assert claims['comment:3:severity'] == 'major'
    assert claims['comment:3:source_grounding']['source_ids'] == ['pilot']


def test_supported_diagnosis_does_not_protect_unsupported_recommendation():
    original = review()
    target = 'comment:3:recommendation'
    audit = repair.audit_value(json.dumps(claim_audit(original, bad=target)), original, [])
    changed = original.model_copy(deep=True)
    changed.comments[0].recommendation = 'Use a bounded, source-grounded correction.'
    result = repair.revision_value(json.dumps(changed.model_dump()), original, audit, holdout.ARTICLE, holdout.SOURCES)
    assert result.comments[0].issue == original.comments[0].issue
    assert result.comments[0].recommendation != original.comments[0].recommendation


@pytest.mark.parametrize('field,claim', [
    ('issue', 'diagnosis'), ('recommendation', 'recommendation'),
    ('severity', 'severity'), ('source_ids', 'source_grounding')])
def test_each_supported_comment_claim_is_independently_immutable(field, claim):
    original = review(); audit = repair.audit_value(json.dumps(claim_audit(original)), original, [])
    changed = original.model_copy(deep=True)
    replacement = {'issue': 'Changed diagnosis.', 'recommendation': 'Changed recommendation.',
                   'severity': 'minor', 'source_ids': []}[field]
    setattr(changed.comments[0], field, replacement)
    with pytest.raises(ValueError, match=f'comment:3:{claim}'):
        repair.revision_value(json.dumps(changed.model_dump()), original, audit, holdout.ARTICLE, holdout.SOURCES)


def test_mixed_comment_audit_requires_exact_recommendation_quote():
    original = review(); value = claim_audit(original, bad='comment:3:recommendation')
    row = next(item for item in value['assessments'] if item['id'] == 'comment:3:recommendation')
    row['issue_quote'] = original.comments[0].issue + ' extra'
    with pytest.raises(ValueError, match='actual reviewed claim'):
        repair.audit_value(json.dumps(value), original, [])


def test_empty_source_list_can_be_flagged_with_literal_claim_context():
    original = review(); original.comments[0].source_ids = []
    value = claim_audit(original, bad='comment:3:source_grounding')
    row = next(item for item in value['assessments'] if item['id'] == 'comment:3:source_grounding')
    row['issue_quote'] = original.comments[0].issue
    audit = repair.audit_value(json.dumps(value), original, [])
    changed = original.model_copy(deep=True); changed.comments[0].source_ids = ['pilot']
    result = repair.revision_value(json.dumps(changed.model_dump()), original, audit, holdout.ARTICLE, holdout.SOURCES)
    assert result.comments[0].issue == original.comments[0].issue
    assert result.comments[0].source_ids == ['pilot']


def test_writer_prompt_exposes_claim_audit_without_teacher_answer():
    original = review(); audit = repair.audit_value(
        json.dumps(claim_audit(original, bad='comment:3:recommendation')), original, [])
    request = repair.messages('writer', 'article', [], original, audit)
    assert 'claim_audit' in request['user']
    assert 'independent-assessment' not in request['user']
    assert 'a correct diagnosis does not' in repair.CRITIC


def test_historical_v1_module_and_failed_pilot_replay_are_unchanged():
    pilot = Path('/home/marcin/ai-company-workspaces/technical-review-holdout/self-correction-xappp25s')
    if not pilot.exists(): pytest.skip('preserved local pilot is not available')
    assert (pilot/'implementation/technical_review_self_correction.py').read_bytes() == Path(v1.__file__).read_bytes()
    verified = v1.verify(pilot)
    assert verified['schema'] == 'technical-review-source-self-correction.v1'
    assert verified['status'] == 'needs_revision'
    assert verified['model_calls'] == 3


def test_bounded_claim_protocol_runs_and_replays_literal_authorship(tmp_path, monkeypatch):
    source, _, _, _ = run_fixture(tmp_path/'source', monkeypatch, [content()])
    original = review(); first = claim_audit(original, bad='comment:3:recommendation')
    changed = original.model_copy(deep=True)
    changed.comments[0].recommendation = 'Use a bounded, source-grounded correction.'
    final = claim_audit(changed)
    outputs = [first, changed.model_dump(), final]; calls = []
    config = v1.base.load(source/'manifest.json')['configuration']
    monkeypatch.setattr(v1.lab, 'configuration', lambda: config)
    monkeypatch.setattr(v1.lab, 'check_idle', lambda: {'docker': 'empty'})
    class Batch:
        def __init__(self, supplied, maximum):
            assert supplied['model'] == config['model'] and maximum == 3
            self.calls = []
        def call(self, out, stage, system, user, schema, *, final=False):
            raw = outputs[len(calls)]; calls.append(stage)
            response = {'content': json.dumps(raw), 'model': config['model'], 'digest': config['digest'],
                        'elapsed_seconds': .1}
            v1.lab.save(out/(stage+'-request.json'), {'system': system, 'user': user, 'format': schema})
            v1.lab.save(out/(stage+'-response.json'), response)
            self.calls.append({'stage': stage, 'keep_alive_seconds': 0 if final else 3,
                               'elapsed_seconds': .1, 'timings_ns': {}})
            return response['content']
        def close(self): return {'calls': self.calls, 'idle_after': True}
    monkeypatch.setattr(v1, 'RetainedBatch', Batch)
    out, report = repair.run(source, root=tmp_path/'runs')
    assert report['status'] == 'pending_independent_review'
    assert calls == ['audit', 'writer', 'final-audit']
    verified = repair.verify(out)
    assert verified['model_calls'] == 3 and verified['autonomy_qualified'] is False
    writer = v1.base.load(out/'writer-request.json')
    payload = json.loads(writer['user'])
    assert payload['claim_audit']['assessments'][1]['id'] == 'comment:3:recommendation'
    assert v1.base.load(out/'review.json')['comments'][0]['issue'] == original.comments[0].issue


def test_claim_protocol_verifier_rejects_false_acceptance(tmp_path, monkeypatch):
    source, _, _, _ = run_fixture(tmp_path/'source', monkeypatch, [content()])
    original = review(); outputs = [claim_audit(original)]; config = v1.base.load(source/'manifest.json')['configuration']
    monkeypatch.setattr(v1.lab, 'configuration', lambda: config); monkeypatch.setattr(v1.lab, 'check_idle', lambda: {})
    class Batch:
        def __init__(self, supplied, maximum): self.calls = []
        def call(self, out, stage, system, user, schema, *, final=False):
            response = {'content': json.dumps(outputs[0]), 'model': config['model'], 'digest': config['digest'],
                        'elapsed_seconds': .1}
            v1.lab.save(out/(stage+'-request.json'), {'system': system, 'user': user, 'format': schema})
            v1.lab.save(out/(stage+'-response.json'), response)
            self.calls.append({'stage': stage, 'keep_alive_seconds': 3, 'elapsed_seconds': .1, 'timings_ns': {}})
            return response['content']
        def close(self): return {'calls': self.calls, 'idle_after': True}
    monkeypatch.setattr(v1, 'RetainedBatch', Batch)
    out, report = repair.run(source, root=tmp_path/'runs')
    report['accepted'] = True; v1.lab.save(out/'report.json', report)
    with pytest.raises(ValueError, match='protocol'):
        repair.verify(out)


def test_removed_protected_comment_is_a_replayable_failed_run(tmp_path, monkeypatch):
    source, _, _, _ = run_fixture(tmp_path/'source', monkeypatch, [content()])
    original = review(); first = claim_audit(original, bad='comment:3:recommendation')
    changed = original.model_copy(deep=True)
    changed.comments = [comment for comment in changed.comments if comment.line != 4]
    outputs = [first, changed.model_dump()]; calls = []
    config = v1.base.load(source/'manifest.json')['configuration']
    monkeypatch.setattr(v1.lab, 'configuration', lambda: config)
    monkeypatch.setattr(v1.lab, 'check_idle', lambda: {})
    class Batch:
        def __init__(self, supplied, maximum): self.calls = []
        def call(self, out, stage, system, user, schema, *, final=False):
            raw = outputs[len(calls)]; calls.append(stage)
            response = {'content': json.dumps(raw), 'model': config['model'], 'digest': config['digest'],
                        'elapsed_seconds': .1}
            v1.lab.save(out/(stage+'-request.json'), {'system': system, 'user': user, 'format': schema})
            v1.lab.save(out/(stage+'-response.json'), response)
            self.calls.append({'stage': stage, 'keep_alive_seconds': 3,
                               'elapsed_seconds': .1, 'timings_ns': {}})
            return response['content']
        def close(self): return {'calls': self.calls, 'idle_after': True}
    monkeypatch.setattr(v1, 'RetainedBatch', Batch)
    out, report = repair.run(source, root=tmp_path/'runs')
    assert report['status'] == 'failed' and calls == ['audit', 'writer']
    assert report['error'] == 'Protected claim is missing from revised review: comment:4:diagnosis'
    assert repair.verify(out)['status'] == 'failed'
    assert 'technical_review_self_correction.py' in v1.base.load(out/'manifest.json')['implementation']
