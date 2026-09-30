from copy import deepcopy
import json
from pathlib import Path
import tempfile
import shutil
import pytest

from scripts import brand_delivery_exam as exam
from scripts.brand_full_exam import exercise_context


@pytest.mark.parametrize('strict', [False, True])
def test_new_cases_are_frozen_reserved_and_distinct(strict):
    briefs = [exam.definition(c, strict=strict) for c in (exam.STRICT_CASES if strict else exam.CASES)]
    assert len({v['family'] for v in briefs}) == 3
    assert all(v['split'] == 'test' and v['synthetic'] for v in briefs)
    old = deepcopy(exam.b.BRIEF)
    for brief in briefs:
        with exercise_context(brief): assert exam.b.BRIEF == brief
        assert exam.b.BRIEF == old
    with pytest.raises(ValueError):
        with exercise_context(briefs[0] | {'restaurant_name': 'unfrozen'}): pass


@pytest.fixture
def completed(tmp_path, monkeypatch, request):
    strict = getattr(request, 'param', False)
    b = exam.b
    monkeypatch.setattr(b, 'ROOT', tmp_path)
    monkeypatch.setattr(b.school, 'check_idle', lambda: {})
    monkeypatch.setattr(b, 'configuration', lambda: {'model': 'fixture', 'digest': 'f'*64})
    monkeypatch.setattr(exam.artwork, 'source_values', lambda p: None)
    monkeypatch.setattr(exam.evidence, 'verify', lambda p: {})
    monkeypatch.setattr(exam, 'check_no_text_repair', lambda folder, source, **kwargs: None)
    def create(names):
        out = Path(tempfile.mkdtemp(dir=tmp_path)); code = out/'implementation'; code.mkdir()
        for name in names:
            source = Path(exam.__file__).parent/name
            shutil.copyfile(source, code/name)
        return out
    def finish(out, value):
        value['artifacts'] = {str(p.relative_to(out)): b.school.checksum(p) for p in out.rglob('*') if p.is_file()}
        b.school.save(out/'report.json', value); return out, value
    def generate():
        out = create(('brand_school.py',))
        b.school.save(out/'plan-request.json', {})
        return finish(out, {'model': 'fixture', 'digest': 'f'*64, 'brief': deepcopy(b.BRIEF),
            'config': dict(exam.GENERATION), 'status': 'pending_independent_visual_review'})
    calls = []
    def repair(source, *, deliberate, matched_budget, strict_card=False):
        assert matched_budget and strict_card is strict; calls.append(deliberate)
        out = create(('brand_artwork_repair.py',)); original = exam.evidence.read(source/'report.json')
        b.school.save(out/'repair-origin.json', {'source': str(source), 'source_report_sha256': b.school.checksum(source/'report.json'),
            'max_additional_model_calls': 6, 'fresh_exam': False, 'repaired_stages': []})
        return finish(out, {'model': 'fixture', 'digest': 'f'*64, 'brief': original['brief'],
            'config': exam.ARTWORK | {'think': deliberate, 'sampling_profile': 'qwen-deliberate-trial.v1' if deliberate else 'bounded-default.v1'},
            'repair_contract': exam.artwork.CARD_CONTRACT if strict else exam.artwork.CONTRACT, 'status': 'pending_independent_visual_review'})
    def revise(package, *, spatial, warm):
        assert spatial == ('background' if strict else 'alignment') and warm
        out = create(('brand_guide_revision.py',))
        b.school.save(out/'review-request.json', {})
        b.school.save(out/'spatial-request.json', {})
        return finish(out, {'model': 'fixture', 'digest': 'f'*64, 'package': str(package),
            'source_report_sha256': b.school.checksum(package/'report.json'),
            'config': exam.TEXT | {'think': False, 'sampling_profile': 'bounded-default.v1'},
            'max_model_calls': 5, 'review_contract': exam.protocol_for(strict).CONTRACT,
            'retained_batch_contract': 'local-retained-batch.v1', 'status': 'no_repair_requested'})
    monkeypatch.setattr(b, 'run', generate)
    monkeypatch.setattr(exam.artwork, 'run', repair)
    monkeypatch.setattr(exam.text_repair, 'run', revise)
    out, report = exam.run(strict=strict)
    assert calls == [False, True, True, False, False, True]
    return out, report


@pytest.mark.parametrize('completed', [False, True], indirect=True)
def test_full_flow_keeps_shared_sources_and_no_self_qualification(completed):
    out, report = completed
    assert report['technical_scores'] == {'baseline': 3, 'deliberate': 3}
    result = exam.verify(out)
    assert result['equal_artwork_budgets'] and result['shared_original_per_pair']
    assert not result['autonomy_qualified']


@pytest.mark.parametrize('completed', [False, True], indirect=True)
@pytest.mark.parametrize('fault', ['budget', 'profile', 'source', 'code', 'candidate', 'score', 'brief', 'contract'])
def test_rebound_changes_do_not_create_a_valid_frozen_comparison(completed, fault):
    out, report = completed; outcome = report['cases'][0]['arms']['deliberate']; folder = Path(outcome['artwork'])
    value = exam.evidence.read(folder/'report.json')
    if fault == 'score': report['technical_scores']['deliberate'] = 0
    elif fault == 'candidate': outcome['candidate'] = report['cases'][0]['source']
    else:
        if fault == 'budget': value['config']['num_predict'] = 4096
        elif fault == 'contract': value['repair_contract'] = 'unfrozen-contract'
        elif fault == 'profile': value['config']['think'] = False
        elif fault == 'brief': value['brief']['restaurant_name'] = 'Unfrozen replacement'
        elif fault == 'code': (folder/'implementation/brand_artwork_repair.py').write_text('changed code')
        else:
            record = exam.evidence.read(folder/'repair-origin.json'); record['source'] = report['cases'][1]['source']
            exam.b.school.save(folder/'repair-origin.json', record)
        value['artifacts'] = {str(p.relative_to(folder)): exam.b.school.checksum(p) for p in folder.rglob('*') if p.is_file() and p.name != 'report.json'}
        exam.b.school.save(folder/'report.json', value); outcome['artwork_report_sha256'] = exam.b.school.checksum(folder/'report.json')
    exam.b.school.save(out/'report.json', report)
    with pytest.raises(ValueError): exam.verify(out)


@pytest.mark.parametrize('completed', [True], indirect=True)
def test_resource_continuation_preserves_finished_work_and_model_failure_budgets(completed, monkeypatch):
    from scripts import brand_delivery_resume as resume
    source, original = completed
    original['cases'] = original['cases'][:2]
    original.update(status='failed', error_type='PreflightFailure', error='active_containers')
    outcome = original['cases'][1]['arms']['baseline']
    art = Path(outcome['artwork']); value = exam.evidence.read(art/'report.json')
    value.update(status='failed', error_type='PreflightFailure', error='active_containers')
    exam.b.school.save(art/'report.json', value)
    outcome.update(artwork_report_sha256=exam.b.school.checksum(art/'report.json'),
                   status='failed', text=None, candidate=None)
    outcome.pop('text_report_sha256')
    exam.b.school.save(source/'report.json', original)
    monkeypatch.setattr(exam.artwork, 'source_values', lambda p: (exam.evidence.read(p/'report.json'), None, None, None, None))
    out, report = resume.run(source)
    assert report['status'] == 'completed'
    assert report['cases'][0] == original['cases'][0]
    assert report['cases'][1]['arms']['deliberate'] == original['cases'][1]['arms']['deliberate']
    assert len(report['resource_continuation']['zero_inference_restarts']) == 1
    assert resume.verify(out)['interrupted_additional_model_calls'] == 0
    changed = deepcopy(report)
    changed['resource_continuation']['zero_inference_restarts'] = []
    exam.b.school.save(out/'report.json', changed)
    with pytest.raises(ValueError, match='Unbound extra restart'): resume.verify(out)
    value['error_type'] = 'ValueError'
    exam.b.school.save(art/'report.json', value)
    outcome['artwork_report_sha256'] = exam.b.school.checksum(art/'report.json')
    with pytest.raises(ValueError, match='zero additional model calls'): resume.can_restart_art(outcome)
