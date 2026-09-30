import json
from pathlib import Path

import pytest

from scripts import technical_review_final_correction as repair
from scripts import technical_review_claim_map_self_correction as v3
from tests.test_technical_review_claim_map_self_correction import audit, review
from tests.test_technical_review_holdout import content, run_fixture


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    source, _, _, _ = run_fixture(tmp_path/'source', monkeypatch, [content()])
    original = review()
    first = audit(original, 'comment:3:diagnosis')
    middle = original.model_copy(deep=True); middle.comments[0].issue = 'A bounded corrected diagnosis.'
    final = audit(middle, 'comment:3:recommendation')
    corrected = middle.model_copy(deep=True); corrected.comments[0].recommendation = 'A source-bounded recommendation.'
    outputs = [first, middle.model_dump(), final, corrected.model_dump()]; calls = []
    config = repair.v1.base.load(source/'manifest.json')['configuration']
    monkeypatch.setattr(repair.v1.lab, 'configuration', lambda: config)
    monkeypatch.setattr(repair.v1.lab, 'check_idle', lambda: {})
    class Batch:
        def __init__(self, supplied, maximum):
            assert maximum == 4; self.calls = []
        def call(self, out, stage, system, user, schema, *, final=False):
            response = {'content': json.dumps(outputs[len(calls)]), 'model': config['model'],
                        'digest': config['digest'], 'elapsed_seconds': .1}
            calls.append(stage)
            repair.v1.lab.save(out/(stage+'-request.json'), {'system': system, 'user': user, 'format': schema})
            repair.v1.lab.save(out/(stage+'-response.json'), response)
            self.calls.append({'stage': stage, 'keep_alive_seconds': 0 if final else 3,
                               'resources_before': {'resident_reused': False, 'gpu_free_mib': 30000,
                                                    'resident_vram_bytes': 0, 'docker': 'empty',
                                                    'comfyui': 'idle_or_not_listening'},
                               'elapsed_seconds': .1, 'timings_ns': {}})
            return response['content']
        def close(self):
            return {'schema': 'local-retained-batch.v1', 'calls': self.calls, 'idle_after': True}
    monkeypatch.setattr(repair.v1, 'RetainedBatch', Batch)
    return source, tmp_path/'runs', outputs, calls, original, middle, corrected


def test_final_audit_can_release_only_newly_rejected_recommendation(pipeline):
    source, root, _, calls, original, middle, corrected = pipeline
    out, report = repair.run(source, root=root)
    assert report['status'] == 'pending_independent_review_after_final_correction'
    assert calls == ['audit', 'writer', 'final-audit', 'final-writer']
    assert repair.verify(out)['model_calls'] == 4
    result = repair.v1.base.load(out/'review.json')
    assert result['comments'][0]['issue'] == middle.comments[0].issue
    assert result['comments'][0]['recommendation'] == corrected.comments[0].recommendation
    assert result['comments'][0]['recommendation'] != original.comments[0].recommendation
    request = json.loads(repair.v1.base.load(out/'final-writer-request.json')['user'])
    assert request['revision_stage'] == 'final-writer'
    assert request['claim_audit']['comment:3:diagnosis'] == {'verdict': 'supported'}
    assert request['claim_audit']['comment:3:recommendation']['verdict'] == 'needs_revision'
    assert report['accepted'] is report['autonomy_qualified'] is False


def test_final_writer_cannot_damage_final_audit_supported_claim(pipeline):
    source, root, outputs, calls, _, _, _ = pipeline
    outputs[3]['comments'][0]['issue'] = 'Damage a final-supported diagnosis.'
    out, report = repair.run(source, root=root)
    assert report['status'] == 'failed' and len(calls) == 4
    assert 'comment:3:diagnosis' in report['error']
    assert repair.verify(out)['status'] == 'failed'


def test_supported_final_audit_stops_at_three_calls(pipeline):
    source, root, outputs, calls, _, middle, _ = pipeline
    outputs[2] = audit(middle)
    out, report = repair.run(source, root=root)
    assert report['status'] == 'pending_independent_review'
    assert calls == ['audit', 'writer', 'final-audit']
    assert repair.verify(out)['model_calls'] == 3


@pytest.mark.parametrize('fault', ['extra_bound', 'extra_unbound', 'omitted_bound', 'omitted_disk'])
def test_verifier_requires_exact_branch_artifacts(pipeline, fault):
    source, root, _, _, _, _, _ = pipeline
    out, _ = repair.run(source, root=root)
    report = repair.v1.base.load(out/'report.json')
    if fault.startswith('extra'):
        extra = out/'unrelated.json'; extra.write_text('{}')
        if fault == 'extra_bound': report['artifacts']['unrelated.json'] = repair.v1.base.digest(extra)
    elif fault == 'omitted_bound':
        report['artifacts'].pop('review.md')
    else:
        (out/'review.md').unlink()
        report['artifacts'].pop('review.md')
    repair.v1.lab.save(out/'report.json', report)
    with pytest.raises(ValueError, match='Exact branch artifact'):
        repair.verify(out)


@pytest.mark.parametrize('fault', [
    'schema', 'extra_top', 'missing_field', 'extra_field',
    'extra_record', 'missing_record', 'missing_resource'])
def test_verifier_requires_exact_retained_batch_evidence(pipeline, fault):
    source, root, _, _, _, _, _ = pipeline
    out, _ = repair.run(source, root=root)
    batch = repair.v1.base.load(out/'retained-batch.json')
    if fault == 'schema': batch['schema'] = 'invented'
    elif fault == 'extra_top': batch['note'] = 'invented'
    elif fault == 'missing_field': batch['calls'][0].pop('resources_before')
    elif fault == 'extra_field': batch['calls'][0]['note'] = 'invented'
    elif fault == 'extra_record': batch['calls'].append(dict(batch['calls'][-1]))
    elif fault == 'missing_record': batch['calls'].pop()
    else: batch['calls'][0]['resources_before'].pop('docker')
    repair.v1.lab.save(out/'retained-batch.json', batch)
    report = repair.v1.base.load(out/'report.json')
    report['artifacts']['retained-batch.json'] = repair.v1.base.digest(out/'retained-batch.json')
    repair.v1.lab.save(out/'report.json', report)
    with pytest.raises(ValueError): repair.verify(out)


def test_preserved_real_v3_run_and_implementation_remain_unchanged():
    run = Path('/home/marcin/ai-company-workspaces/technical-review-holdout/claim-map-self-correction-qxhti21g')
    if not run.exists(): pytest.skip('preserved v3 run unavailable')
    before = {path.name: path.read_bytes() for path in run.iterdir() if path.is_file()}
    verified = v3.verify(run)
    assert verified['schema'] == 'technical-review-source-self-correction.v3'
    assert verified['status'] == 'needs_revision' and verified['model_calls'] == 3
    assert {path.name: path.read_bytes() for path in run.iterdir() if path.is_file()} == before
    assert Path(v3.__file__).read_bytes() == (run/'implementation/technical_review_claim_map_self_correction.py').read_bytes()
