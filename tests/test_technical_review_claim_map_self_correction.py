import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from app.services.local_ollama import output_format
from scripts import technical_review_claim_map_self_correction as repair
from scripts import technical_review_claim_self_correction as v2
from scripts import technical_review_holdout as holdout
from tests.test_technical_review_holdout import content, run_fixture


def review():
    return repair.v1.lab.Review.model_validate(json.loads(content()))


def audit(value, bad=None):
    return {claim: {'verdict': 'needs_revision' if claim == bad else 'supported',
                    'issue_quote': repair.v1.strings(unit)[-1] if claim == bad else '',
                    'reason': 'Synthetic keyed claim assessment for protocol testing.',
                    'evidence_quotes': []}
            for claim, unit in repair.v2.claim_units(value).items()}


def test_v3_critic_replaces_legacy_array_instruction_exactly():
    assert repair.v2.CRITIC.count(repair.LEGACY_AUDIT_SHAPE) == 1
    assert repair.LEGACY_AUDIT_SHAPE not in repair.CRITIC
    assert repair.CRITIC.count(repair.KEYED_AUDIT_SHAPE) == 1


@pytest.mark.parametrize('fault', ['missing', 'extra', 'duplicate'])
def test_claim_map_rejects_missing_extra_and_duplicate_keys(fault):
    original = review(); value = audit(original)
    if fault == 'missing': value.pop('top_fixes'); raw = json.dumps(value)
    elif fault == 'extra': value['invented'] = next(iter(value.values())); raw = json.dumps(value)
    else:
        raw = json.dumps(value)[:-1] + ',"top_fixes":' + json.dumps(value['top_fixes']) + '}'
    with pytest.raises(ValueError): repair.audit_value(raw, original, [])


def test_complete_unordered_map_is_canonicalized_to_input_order():
    original = review(); value = audit(original)
    raw = json.dumps(dict(reversed(list(value.items()))))
    parsed = repair.audit_value(raw, original, [])
    assert list(parsed) == list(repair.v2.claim_units(original))
    assert list(repair.audit_dump(parsed)) == list(repair.v2.claim_units(original))


def test_writer_projection_keeps_failure_evidence_and_field_protection():
    original = review(); value = audit(original, 'comment:3:recommendation')
    value['comment:3:recommendation']['evidence_quotes'] = [
        {'source_id': 'pilot', 'quote': 'Fictional exercise only'}]
    parsed = repair.audit_value(json.dumps(value), original, holdout.SOURCES)
    projected = repair.writer_audit(parsed)
    assert projected['comment:3:diagnosis'] == {'verdict': 'supported'}
    assert projected['comment:3:recommendation'] == value['comment:3:recommendation']
    changed = original.model_copy(deep=True)
    changed.comments[0].recommendation = 'Use a source-bounded correction.'
    result = repair.revision_value(json.dumps(changed.model_dump()), original, parsed,
                                   holdout.ARTICLE, holdout.SOURCES)
    assert result.comments[0].issue == original.comments[0].issue
    assert result.comments[0].recommendation != original.comments[0].recommendation


def test_real_and_maximum_claim_map_schemas_fit_real_adapter_limit():
    source = Path('/home/marcin/ai-company-workspaces/technical-review-holdout/replay-v2-9wo0u6n8')
    if source.exists(): _, actual, _, _ = repair.v1.origin(source)
    else:
        actual = review(); actual.comments.extend([actual.comments[0].model_copy(update={'line': 7}),
                                                   actual.comments[0].model_copy(update={'line': 8})])
    actual_schema = repair.audit_schema(actual)
    assert len(repair.v2.claim_units(actual)) == 30
    Draft202012Validator.check_schema(actual_schema)
    assert output_format({'format': actual_schema}) == actual_schema
    maximum = actual.model_copy(deep=True); maximum.comments = []
    article_lines = holdout.ARTICLE.splitlines()
    for number in range(1, 31):
        maximum.comments.append(repair.v1.lab.Comment(
            line=number, quote=article_lines[0], severity='suggestion',
            issue=f'Bounded diagnosis {number}', recommendation=f'Bounded recommendation {number}',
            source_ids=[]))
    maximum_schema = repair.audit_schema(maximum)
    assert len(repair.v2.claim_units(maximum)) == 126
    Draft202012Validator.check_schema(maximum_schema)
    assert len(json.dumps(maximum_schema)) <= 16000
    assert output_format({'format': maximum_schema}) == maximum_schema
    assert maximum_schema['additionalProperties'] is False
    assert set(maximum_schema['required']) == set(maximum_schema['properties'])


def test_full_three_call_run_and_verify(tmp_path, monkeypatch):
    source, _, _, _ = run_fixture(tmp_path/'source', monkeypatch, [content()])
    original = review(); first = audit(original, 'comment:3:recommendation')
    changed = original.model_copy(deep=True); changed.comments[0].recommendation = 'Use a bounded correction.'
    final = audit(changed); outputs = [first, changed.model_dump(), final]; calls = []
    config = repair.v1.base.load(source/'manifest.json')['configuration']
    monkeypatch.setattr(repair.v1.lab, 'configuration', lambda: config)
    monkeypatch.setattr(repair.v1.lab, 'check_idle', lambda: {})
    class Batch:
        def __init__(self, supplied, maximum): self.calls = []
        def call(self, out, stage, system, user, schema, *, final=False):
            response = {'content': json.dumps(outputs[len(calls)]), 'model': config['model'],
                        'digest': config['digest'], 'elapsed_seconds': .1}
            calls.append(stage)
            repair.v1.lab.save(out/(stage+'-request.json'), {'system': system, 'user': user, 'format': schema})
            repair.v1.lab.save(out/(stage+'-response.json'), response)
            self.calls.append({'stage': stage, 'keep_alive_seconds': 0 if final else 3,
                               'elapsed_seconds': .1, 'timings_ns': {}})
            return response['content']
        def close(self): return {'calls': self.calls, 'idle_after': True}
    monkeypatch.setattr(repair.v1, 'RetainedBatch', Batch)
    out, report = repair.run(source, root=tmp_path/'runs')
    assert report['status'] == 'pending_independent_review'
    assert calls == ['audit', 'writer', 'final-audit']
    assert repair.verify(out)['model_calls'] == 3
    assert repair.v1.base.load(out/'audit.json') == first
    writer = repair.v1.base.load(out/'writer-request.json')
    assert isinstance(json.loads(writer['user'])['claim_audit'], dict)
    assert set(repair.v1.base.load(out/'manifest.json')['implementation']) == {
        path.name for path in repair.snapshots()}


def test_preserved_failed_v2_pilot_still_replays_unchanged():
    pilot = Path('/home/marcin/ai-company-workspaces/technical-review-holdout/claim-self-correction-w3a0i7v3')
    if not pilot.exists(): pytest.skip('preserved v2 pilot unavailable')
    before = (pilot/'report.json').read_bytes()
    verified = v2.verify(pilot)
    assert verified['schema'] == 'technical-review-source-self-correction.v2'
    assert verified['status'] == 'failed' and verified['model_calls'] == 1
    assert (pilot/'report.json').read_bytes() == before
