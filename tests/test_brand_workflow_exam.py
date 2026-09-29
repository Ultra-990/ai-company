from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import pytest

from scripts import brand_workflow_exam as workflow
from scripts import brand_full_exam as original_exam
from scripts import brand_plan_review as expanded


def test_new_frozen_briefs_are_distinct_and_context_restores():
    briefs = [workflow.definition(c) for c in workflow.CASES]
    assert len({b['family'] for b in briefs}) == 3
    assert all(b['split'] == 'test' and b['synthetic'] for b in briefs)
    previous = deepcopy(workflow.brand.BRIEF)
    with original_exam.exercise_context(briefs[0]): assert workflow.brand.BRIEF == briefs[0]
    assert workflow.brand.BRIEF == previous


@pytest.fixture
def completed(tmp_path, monkeypatch):
    b = workflow.brand; r = workflow.revision
    monkeypatch.setattr(b, 'ROOT', tmp_path)
    monkeypatch.setattr(b.school, 'check_idle', lambda: {})
    monkeypatch.setattr(b, 'configuration', lambda: {'model': 'fixture', 'digest': 'f'*64})
    monkeypatch.setattr(r.evidence, 'verify', lambda p: {})
    monkeypatch.setattr(r, 'inputs', lambda p: (r.evidence.read(p/'report.json'), {'fixture': 'source data'}))
    monkeypatch.setattr(expanded, 'expand', lambda data, p: data | {'expanded': True})
    def start(names):
        out = Path(tempfile.mkdtemp(dir=tmp_path)); code = out/'implementation'; code.mkdir()
        for name in names:
            path = Path(b.__file__).parent/name if name != 'local_ollama.py' else Path(b.__file__).parents[1]/'app/services/local_ollama.py'
            shutil.copyfile(path, code/name)
        return out
    def finish(out, report):
        report['artifacts'] = {str(p.relative_to(out)): b.school.checksum(p) for p in out.rglob('*') if p.is_file()}
        b.school.save(out/'report.json', report); return out, report
    def generate():
        out = start(('brand_school.py', 'render_school_svg.py', 'vector_structured_source.py', 'vector_school_contract.py', 'local_ollama.py'))
        b.school.save(out/'plan-request.json', {})
        return finish(out, {'brief': deepcopy(b.BRIEF), 'model': 'fixture', 'digest': 'f'*64,
            'status': 'pending_independent_visual_review',
            'config': {'num_ctx': 8192, 'num_predict': 4096, 'num_thread': 4, 'timeout_seconds': 180}})
    arms = []
    def revise(source, *, expanded=False):
        from scripts import brand_plan_review as enhanced
        protocol = enhanced if expanded else r; arms.append(expanded)
        names = ['brand_guide_revision.py', 'brand_school.py', 'verify_brand_package.py', 'local_ollama.py']
        if expanded: names.append('brand_plan_review.py')
        out = start(names)
        data = r.inputs(source)[1]
        if expanded: data = enhanced.expand(data, source)
        value = {'reviews': [{'index': i, 'verdict': 'supported', 'reason': 'A complete matching fixture reason.'} for i in range(6 if expanded else 4)]}
        b.school.save(out/'review-request.json', {'system': protocol.REVIEW_SYSTEM, 'user': json.dumps(data), 'format': protocol.REVIEW_SCHEMA})
        b.school.save(out/'review-response.json', {'model': 'fixture', 'digest': 'f'*64, 'content': json.dumps(value)})
        b.school.save(out/'review.json', value)
        report = {'package': str(source), 'source_report_sha256': b.school.checksum(source/'report.json'),
            'status': 'no_repair_requested', 'max_model_calls': 3, 'elapsed_seconds': 1,
            'model': 'fixture', 'digest': 'f'*64,
            'config': {'num_ctx': 8192, 'num_predict': 1800, 'num_thread': 4, 'timeout_seconds': 90,
                'sampling_profile': 'bounded-default.v1', 'think': False}}
        if expanded: report['review_contract'] = enhanced.CONTRACT
        return finish(out, report)
    monkeypatch.setattr(b, 'run', generate)
    monkeypatch.setattr(r, 'run', revise)
    out, report = workflow.run()
    assert arms == [False, True, True, False, False, True]
    return out, report


def test_paired_workflow_discloses_shared_sources_and_no_qualification(completed):
    result = workflow.verify(completed[0])
    assert result['technical_scores'] == {'legacy': 3, 'expanded': 3}
    assert result['shared_original_per_pair'] and not result['autonomy_qualified']


@pytest.mark.parametrize('fault', ['budget', 'code', 'source', 'candidate', 'score'])
def test_paired_workflow_rejects_rebound_changes(completed, fault):
    out, report = completed; b = workflow.brand
    item = report['cases'][0]['arms']['expanded']; folder = Path(item['revision'])
    value = workflow.revision.evidence.read(folder/'report.json')
    if fault == 'score': report['technical_scores']['expanded'] = 2
    elif fault == 'candidate': item['candidate'] = str(folder)
    else:
        if fault == 'budget': value['config']['num_predict'] = 900
        elif fault == 'source': value['package'] = report['cases'][1]['source']
        else:
            p = folder/'implementation/brand_plan_review.py'; p.write_text('changed')
            value['artifacts'][str(p.relative_to(folder))] = b.school.checksum(p)
        b.school.save(folder/'report.json', value); item['report_sha256'] = b.school.checksum(folder/'report.json')
    b.school.save(out/'report.json', report)
    with pytest.raises(ValueError): workflow.verify(out)
