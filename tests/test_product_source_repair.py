from copy import deepcopy
import json

import pytest

from scripts import product_source_repair as repair


@pytest.mark.parametrize('fault', [None, 'scene', 'author', 'brief', 'facts', 'inherited', 'undeclared', 'fabricated_response'])
def test_source_repair_binding_protects_exact_scene_original_brief_and_authorship(tmp_path, monkeypatch, fault):
    p = repair.product
    monkeypatch.setattr(repair.pilot.revision, 'ROOT', tmp_path)
    value = {'repair': str(tmp_path/'pilot'), 'scene': {'texts': ['original model name']},
        'model': 'fixture', 'digest': 'f'*64, 'brief': {'family': 'original failed case'},
        'supplier_copy': {'capacity': ['Capacity: 1100 ml']}}
    monkeypatch.setattr(repair, 'load', lambda path: deepcopy(value))
    saved = deepcopy(value)
    report = {'source_repair_contract': repair.CONTRACT, 'inherited_stages': ['style', 'source'],
        **{k: deepcopy(value[k]) for k in ('model', 'digest', 'brief', 'supplier_copy')}}
    if fault == 'scene': saved['scene']['texts'] = ['replacement teacher text']
    elif fault == 'author': report['model'] = 'other'
    elif fault == 'brief': report['brief']['family'] = 'new case'
    elif fault == 'facts': report['supplier_copy'] = {}
    elif fault == 'inherited': report['inherited_stages'] = []
    elif fault == 'undeclared': report.pop('source_repair_contract')
    elif fault == 'fabricated_response': p.school.save(tmp_path/'source-response.json', {'content': 'fabricated complete answer'})
    p.school.save(tmp_path/'source-repair.json', saved)
    report['artifacts'] = {path.name: p.school.checksum(path) for path in tmp_path.iterdir()}
    if fault:
        with pytest.raises(ValueError): repair.verify_binding(tmp_path, report)
    else:
        assert repair.verify_binding(tmp_path, report) == value


@pytest.mark.parametrize('option', ['resume', 'recompose', 'source_lesson', 'matched_exam_budget'])
def test_repaired_source_cannot_be_mixed_into_new_exam_or_lesson(tmp_path, monkeypatch, option):
    monkeypatch.setattr(repair.product.school, 'check_idle', lambda: pytest.fail('No inference or resources needed'))
    with pytest.raises(ValueError, match='never a fresh matched exam'):
        repair.product.run(source_repair=tmp_path, **{option: True if option == 'matched_exam_budget' else tmp_path})


def test_accepted_raw_uses_literal_patch_result_without_inventing_a_model_response(tmp_path, monkeypatch):
    value = {'repair': str(tmp_path/'pilot'), 'style_raw': '{"ink":"#123456"}', 'scene': {'texts': ['model name']}}
    repair.product.school.save(tmp_path/'source-repair.json', value)
    monkeypatch.setattr(repair, 'load', lambda path: deepcopy(value))
    assert repair.product.accepted_raw(tmp_path, 'style') == value['style_raw']
    assert json.loads(repair.product.accepted_raw(tmp_path, 'source')) == value['scene']
    assert not list(tmp_path.glob('*-response.json'))


def test_cli_continuation_selects_canonical_frozen_brief_without_main_module_recursion(tmp_path, monkeypatch):
    import runpy
    import sys
    from scripts import product_full_exam as exam
    frozen = exam.definition(exam.CASES[-1]); calls = []
    monkeypatch.setattr(repair, 'load', lambda path: deepcopy(frozen))
    previous = deepcopy(repair.product.BRIEF)
    def run(**kwargs):
        calls.append(kwargs)
        assert repair.product.BRIEF == frozen['brief']
        return tmp_path, {'status': 'pending_independent_review'}
    monkeypatch.setattr(repair.product, 'run', run)
    monkeypatch.setattr(sys, 'argv', ['product_infographic_school.py', '--continue-source-repair', str(tmp_path)])
    with pytest.raises(SystemExit) as result:
        runpy.run_path(str(repair.product.__file__), run_name='__main__')
    assert result.value.code == 0 and len(calls) == 1
    assert repair.product.BRIEF == previous
