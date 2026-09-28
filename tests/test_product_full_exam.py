from copy import deepcopy
import json

import pytest

from scripts import product_full_exam as exam


def test_new_cases_are_frozen_nontraining_and_have_distinct_physical_ratios():
    cases = [exam.definition(case) for case in exam.CASES]
    assert len({case['brief']['family'] for case in cases}) == 3
    ratios = set()
    for case in cases:
        assert case['brief']['split'] == 'test'
        assert case['brief']['family'] != exam.product.DEFAULT_BRIEF['family']
        height, diameter = case['brief']['physical_dimensions_cm']; ratios.add(height/diameter)
        assert case['supplier_copy']['dimensions'] == [f'Height: {height} cm', f'Diameter: {diameter} cm']
        assert exam.matching_case(case) is not None
        changed = deepcopy(case); changed['supplier_copy']['capacity'][0] = 'Capacity: 1 ml'
        assert exam.matching_case(changed) is None
    assert len(ratios) == 3 and max(ratios)-min(ratios) > 1
    for case in exam.LEGACY_CASES:
        old = exam.definition(case)
        assert old['brief']['qualification_exam'] == exam.LEGACY_VERSION
        assert exam.matching_case(old) == case
    for case in exam.SECOND_CASES:
        old = exam.definition(case)
        assert old['brief']['qualification_exam'] == exam.SECOND_VERSION
        assert exam.matching_case(old) == case


def test_context_uses_case_dimensions_and_restores_globals_even_after_failure():
    original = exam.product.BRIEF, exam.product.PANELS
    measured = {'shape_layout': [{'bbox': [100, 100, 100, 275]}]}
    assert exam.product.source_fidelity_issues(measured)
    with pytest.raises(RuntimeError):
        with exam.exercise_context(exam.CASES[0]):
            assert exam.product.source_fidelity_issues(measured) == []
            raise RuntimeError('fixture interruption')
    assert exam.product.BRIEF is original[0] and exam.product.PANELS is original[1]


def test_verify_cannot_select_arbitrary_report_defined_brief(tmp_path, monkeypatch):
    monkeypatch.setattr(exam.product, 'ROOT', tmp_path)
    original = exam.product.BRIEF
    case = exam.definition(exam.CASES[0]); case['status'] = 'failed'
    (tmp_path/'report.json').write_text(json.dumps(case))
    with pytest.raises(ValueError, match='Completed package'): exam.product.verify(tmp_path)
    assert exam.product.BRIEF is original
    case['brief']['physical_dimensions_cm'] = [1, 1000]
    (tmp_path/'report.json').write_text(json.dumps(case))
    with pytest.raises(ValueError, match='Completed package'): exam.product.verify(tmp_path)
    assert exam.product.BRIEF is original


def test_full_exam_freezes_before_calls_matches_budgets_and_preserves_failures(tmp_path, monkeypatch):
    monkeypatch.setattr(exam.product, 'ROOT', tmp_path)
    monkeypatch.setattr(exam.product.school, 'check_idle', lambda: {'ready': True})
    monkeypatch.setattr(exam.product, 'configuration', lambda: {'model': 'fixture', 'digest': 'f'*64})
    monkeypatch.setattr(exam.product, 'verify', lambda path: {'verified': True})
    calls = []
    original = exam.product.BRIEF, exam.product.PANELS
    def run(**kwargs):
        manifest = json.loads(next(tmp_path.glob('full-exam-*/exam.json')).read_text())
        assert not manifest['training_export_allowed'] and not manifest['manual_hints_allowed']
        assert len(manifest['cases']) == 3 and kwargs['matched_exam_budget'] is True
        assert kwargs['functional_callouts'] is True and kwargs['focused_stages'] is True
        assert kwargs['visual_feedback'] is False
        assert kwargs['recover_incomplete'] is True
        assert kwargs['source_contour'] is True
        calls.append((exam.product.BRIEF['family'], kwargs['sampling_profile']))
        package = tmp_path/f'package-{len(calls)}'; package.mkdir()
        report = {'model': 'fixture', 'digest': 'f'*64, 'config': manifest['shared_budget'],
                  'elapsed_seconds': 1, 'status': 'failed' if kwargs['sampling_profile'] == exam.ARMS['baseline'] else 'pending_independent_review'}
        (package/'report.json').write_text(json.dumps(report))
        return package, report
    monkeypatch.setattr(exam.product, 'run', run)
    out, result = exam.run()
    assert result['status'] == 'completed' and result['scores'] == {'baseline': 0, 'deliberate': 3}
    assert len(calls) == 6
    for a, b in zip(calls[::2], calls[1::2]):
        assert a[0] == b[0] and a[1] != b[1]
    assert exam.product.BRIEF is original[0] and exam.product.PANELS is original[1]
    assert result['exam_sha256'] == exam.product.school.checksum(out/'exam.json')
    assert not result['visual_acceptance'] and not result['autonomy_qualified']
