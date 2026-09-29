from copy import deepcopy
import json

import pytest

from scripts import product_exam_assessment as assessment


def fixture_exam(tmp_path, monkeypatch):
    p = assessment.product
    monkeypatch.setattr(p, 'ROOT', tmp_path)
    monkeypatch.setattr(assessment.revision, 'ROOT', tmp_path)
    monkeypatch.setattr(p, 'verify', lambda folder: {'verified': True})
    out = tmp_path/'exam'; out.mkdir(); (out/'implementation').mkdir()
    names = ('product_infographic_school.py', 'product_callouts.py', 'brand_school.py',
             'product_model_feedback.py', 'render_school_svg.py', 'vector_school_contract.py', 'local_ollama.py')
    for name in names: (out/'implementation'/name).write_text('frozen fixture code')
    budget = {'num_ctx': 16384, 'num_predict': 8192, 'num_thread': 4, 'timeout_seconds': 180}
    controls = {'source_contract': 'bottle-visible-parts.v4', 'panel_contract': 'text-and-lines.v2',
                'placement_contract': 'extended-transform.v2', 'annotation_contract': 'functional-callouts.v3'}
    manifest = {'schema': assessment.exam.VERSION, 'cases': [assessment.exam.definition(c) for c in assessment.exam.CASES],
                'arms': assessment.exam.ARMS, 'model': 'fixture', 'digest': 'f'*64, 'shared_budget': budget,
                'shared_controls': controls, 'training_export_allowed': False, 'manual_hints_allowed': False,
                'manual_product_edits_allowed': False, 'continuations_allowed': False}
    p.school.save(out/'exam.json', manifest)
    cases = []
    for case in manifest['cases']:
        item = {'id': case['id'], 'arms': {}}; cases.append(item)
        for arm, profile in manifest['arms'].items():
            folder = tmp_path/(case['id']+'-'+arm); folder.mkdir(); (folder/'implementation').mkdir()
            for name in names: (folder/'implementation'/name).write_text('frozen fixture code')
            p.school.save(folder/'style-request.json', {'system': 'fixture', 'user': 'fixture', 'format': {}})
            p.school.save(folder/'style-response.json', {'content': 'fixture'})
            passed = arm == 'deliberate'
            package = {'brief': case['brief'], 'supplier_copy': case['supplier_copy'], 'model': 'fixture', 'digest': 'f'*64,
                       'config': budget | {'sampling_profile': profile, 'think': passed}, 'elapsed_seconds': 1,
                       'status': 'pending_independent_review' if passed else 'failed',
                       'source_fidelity_contract': controls['source_contract'], 'panel_fidelity_contract': controls['panel_contract'],
                       'placement_contract': controls['placement_contract'], 'annotation_contract': controls['annotation_contract'],
                       'instruction_contract': 'focused-stages.v1', 'correction_contract': 'legacy-text.v1',
                       'transport_recovery_contract': 'bounded-incomplete-retry.v1',
                       'artifacts': {str(f.relative_to(folder)): p.school.checksum(f) for f in folder.rglob('*') if f.is_file()}}
            p.school.save(folder/'report.json', package)
            item['arms'][arm] = {'package': str(folder), 'report_sha256': p.school.checksum(folder/'report.json'),
                                 'measured_pass': passed, 'model_requests': 1, 'model_calls': 1}
    report = {'schema': 'product-full-package-exam-result.v1', 'status': 'completed', 'cases': cases,
              'scores': {'baseline': 0, 'deliberate': 3}, 'exam_sha256': p.school.checksum(out/'exam.json'),
              'artifacts': {str(f.relative_to(out)): p.school.checksum(f) for f in out.rglob('*') if f.is_file()}}
    p.school.save(out/'report.json', report)
    return out, report


def test_assessment_recounts_bound_outcomes_without_claiming_visual_or_autonomous_acceptance(tmp_path, monkeypatch):
    out, _ = fixture_exam(tmp_path, monkeypatch)
    result = assessment.assess(out)
    assert result['scores'] == {'baseline': 0, 'deliberate': 3} and result['integrity_verified']
    assert result['independent_visual_review_required'] and not result['autonomy_qualified']


@pytest.mark.parametrize('fault', ['score', 'outcome', 'duplicate', 'budget', 'implementation', 'inherited'])
def test_assessment_rejects_score_manipulation_and_unmatched_executions(tmp_path, monkeypatch, fault):
    out, report = fixture_exam(tmp_path, monkeypatch)
    result = report['cases'][0]['arms']['deliberate']
    if fault == 'score': report['scores']['baseline'] = 1
    elif fault == 'outcome': result['measured_pass'] = False
    elif fault == 'duplicate': report['cases'][1]['arms']['deliberate'] = deepcopy(result)
    else:
        path = tmp_path/(report['cases'][0]['id']+'-deliberate')
        package = json.loads((path/'report.json').read_text())
        if fault == 'budget': package['config']['num_predict'] = 4096
        elif fault == 'inherited': package['inherited_stages'] = ['source']
        else:
            file = path/'implementation/brand_school.py'; file.write_text('changed code')
            package['artifacts']['implementation/brand_school.py'] = assessment.product.school.checksum(file)
        assessment.product.school.save(path/'report.json', package)
        result['report_sha256'] = assessment.product.school.checksum(path/'report.json')
    assessment.product.school.save(out/'report.json', report)
    with pytest.raises(ValueError): assessment.assess(out)


@pytest.mark.parametrize('fault', [None, 'one_arm', 'unreviewed', 'undeclared'])
def test_exam_requires_identical_reviewed_training_lesson_for_both_arms(tmp_path, monkeypatch, fault):
    from scripts import product_source_lesson as lesson
    out, report = fixture_exam(tmp_path, monkeypatch)
    save = assessment.product.school.save; checksum = assessment.product.school.checksum
    manifest = json.loads((out/'exam.json').read_text())
    value = {'contract': lesson.CONTRACT, 'assembly': str(tmp_path/'approved'), 'example': 'reviewed local training scene'}
    manifest['source_lesson'] = value
    manifest['shared_controls']['source_lesson_contract'] = lesson.CONTRACT if fault != 'undeclared' else None
    monkeypatch.setattr(lesson, 'load', lambda path: value if fault != 'unreviewed' else value | {'example': 'changed'})
    (out/'implementation/product_source_lesson.py').write_text('frozen lesson fixture')
    for case in report['cases']:
        for arm, outcome in case['arms'].items():
            folder = tmp_path/(case['id']+'-'+arm)
            package = json.loads((folder/'report.json').read_text())
            package['source_lesson_contract'] = manifest['shared_controls']['source_lesson_contract']
            (folder/'implementation/product_source_lesson.py').write_text('frozen lesson fixture')
            saved = value | {'example': 'extra example for this arm'} if fault == 'one_arm' and arm == 'deliberate' else value
            save(folder/'source-lesson.json', saved)
            package['artifacts'] = {str(p.relative_to(folder)): checksum(p) for p in folder.rglob('*') if p.is_file() and p.name != 'report.json'}
            save(folder/'report.json', package)
            outcome['report_sha256'] = checksum(folder/'report.json')
    save(out/'exam.json', manifest)
    report['exam_sha256'] = checksum(out/'exam.json')
    report['artifacts'] = {str(p.relative_to(out)): checksum(p) for p in out.rglob('*') if p.is_file() and p.name != 'report.json'}
    save(out/'report.json', report)
    if fault:
        with pytest.raises(ValueError, match='lesson'): assessment.assess(out)
    else:
        assert assessment.assess(out)['integrity_verified']
