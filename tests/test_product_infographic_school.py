"""Non-design fixtures exercise supplier fidelity and literal product reuse."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from scripts import product_infographic_school as product
from scripts.vector_school_contract import NS, validate_svg


def style():
    return {'ink': '#111111', 'paper': '#FFFFFF', 'accent': '#888888',
            'body_color': '#003388', 'cap_color': '#222222', 'heading_font': 'Arial', 'body_font': 'Georgia'}


def line(text, y, *, heading=False):
    return {'text': text, 'attributes': {'x': '70', 'y': str(y), 'font-size': '44',
            'font-family': 'Arial' if heading else 'Georgia', 'font-weight': '400', 'fill': '#111111', 'text-anchor': 'start'}}


def source_scene():
    return {'shapes': [{'tag': 'rect', 'attributes': {'x': str(50+i*20), 'y': '50', 'width': '10', 'height': '10', 'fill': '#003388'}} for i in range(3)],
            'texts': [line(product.BRIEF['product_name'], 200, heading=True)]}


def panel_scene(name='capacity'):
    return {'shapes': [{'tag': 'rect', 'attributes': {'x': '0', 'y': '0', 'width': '1500', 'height': '1500', 'fill': '#FFFFFF'}}],
            'product_placement': {'x': '100', 'y': '300', 'scale': '1'},
            'texts': [line('Fixture headline', 150, heading=True), *[line(v, 1100+i*70) for i,v in enumerate(product.PANELS[name])]]}


def source():
    return product.compile_scene(json.dumps(source_scene()), style())


def test_product_reused_exactly_without_repainting_or_geometry_changes():
    original = source()
    result = product.compile_scene(json.dumps(panel_scene()), style(), panel='capacity', product=original)
    group = ET.fromstring(result).find(NS+'g')
    assert group.attrib == {'transform': 'translate(100 300) scale(1)'}
    assert [ET.tostring(n) for n in group] == [ET.tostring(n) for n in ET.fromstring(original)]
    assert validate_svg(result, profile='product_infographic')['texts'][2:] == product.PANELS['capacity']
    with pytest.raises(ValueError): validate_svg(result, profile='leaflet')


@pytest.mark.parametrize('fault', ['invented_capacity', 'negated_fact', 'extra_claim', 'changed_font', 'tiny_text', 'wrong_palette', 'extra_product_transform', 'missing_anchor'])
def test_unfaithful_or_unsupported_scene_is_rejected_without_repair(fault):
    value = panel_scene()
    if fault == 'invented_capacity': value['texts'][1]['text'] = 'Capacity: 900 ml'
    elif fault == 'negated_fact': value['texts'][1]['text'] = 'Not a capacity of 600 ml'
    elif fault == 'extra_claim': value['texts'].append(line('Certified safe', 1350))
    elif fault == 'changed_font': value['texts'][1]['attributes']['font-family'] = 'Arial'
    elif fault == 'tiny_text': value['texts'][1]['attributes']['font-size'] = '24'
    elif fault == 'wrong_palette': value['shapes'][0]['attributes']['fill'] = '#FFAABB'
    elif fault == 'extra_product_transform': value['product_placement']['rotate'] = '90'
    elif fault == 'missing_anchor': value['texts'][0]['attributes'].pop('text-anchor')
    with pytest.raises(ValueError): product.compile_scene(json.dumps(value), style(), panel='capacity', product=source())


def test_out_of_frame_and_copy_over_product_are_measured_independently():
    measured = {'layout': [{'text': 'fixture label', 'bbox': [100, 400, 180, 50]},
                           {'text': 'fixture headline', 'bbox': [100, 450, 240, 60]}],
                'group_layout': [{'bbox': [100, 300, 200, 600]}]}
    assert any(v['kind'] == 'product_overlaps_copy' for v in product.quality_issues(measured, panel=True))
    measured['group_layout'][0]['bbox'] = [1400, 300, 200, 600]
    assert any(v['kind'] == 'product_bounds_or_size' for v in product.quality_issues(measured, panel=True))
    measured = {'layout': [{'text': 'fixture label', 'bbox': [100, 400, 180, 50]}],
                'shape_layout': [{'bbox': [590, 20, 50, 100]}]}
    assert product.quality_issues(measured)[0]['kind'] == 'source_shape_outside_margin'


@pytest.mark.parametrize('width,height,accepted', [(120, 635, False), (200, 200, False),
                                                  (140, 480, True), (175, 600, True), (0, 480, False)])
def test_source_ratio_checks_real_silhouette_independent_of_canvas(width, height, accepted):
    measured = {'shape_layout': [{'bbox': [100, 50, width, height]}]}
    before = json.dumps(measured)
    issues = product.source_fidelity_issues(measured)
    assert (not issues) is accepted
    assert json.dumps(measured) == before
    if issues:
        assert issues[0]['kind'] == 'source_proportions_differ_from_supplier'


def test_source_ratio_includes_cap_and_base():
    measured = {'shape_layout': [{'bbox': [200, 150, 140, 480]}, {'bbox': [240, 70, 60, 80]}]}
    assert product.source_fidelity_issues(measured)[0]['height'] == 560
    assert product.source_fidelity_issues({'shape_layout': []})[0]['kind'] == 'missing_product_silhouette'


def test_source_label_requires_readable_background_and_real_measurement():
    measured = {'shape_layout': [{'bbox': [200, 100, 140, 480]}]}
    assert product.source_fidelity_issues(measured, label_check=True)[0]['kind'] == 'missing_source_label_contrast_measurement'
    measured['label_background_samples'] = [{'text': product.BRIEF['product_name'], 'character_indices': [0, 1]}]
    assert product.source_fidelity_issues(measured, label_check=True)[0]['kind'] == 'source_label_background_interference'
    measured['label_background_samples'][0]['character_indices'] = []
    assert product.source_fidelity_issues(measured, label_check=True) == []


def test_cap_present_in_json_but_hidden_by_body_is_not_a_visible_product_part():
    palette = style()
    def rgb(color): return 'rgb('+', '.join(str(int(color[i:i+2], 16)) for i in (1, 3, 5))+')'
    measured = {'shape_layout': [{'bbox': [200, 100, 140, 480]}, {'bbox': [230, 100, 60, 20]}],
                'source_shape_visibility': [
                    {'index': 0, 'fill': rgb(palette['body_color']), 'visible_samples': 25, 'tested_samples': 25},
                    {'index': 1, 'fill': rgb(palette['cap_color']), 'visible_samples': 0, 'tested_samples': 25}]}
    issues = product.source_fidelity_issues(measured, style=palette)
    assert issues[0]['kind'] == 'product_part_not_visible' and issues[0]['part'] == 'cap'
    assert issues[0]['shape_indices'] == [1]
    measured['source_shape_visibility'][1]['visible_samples'] = 12
    assert product.source_fidelity_issues(measured, style=palette) == []
    del measured['source_shape_visibility']
    assert product.source_fidelity_issues(measured, style=palette)[0]['kind'] == 'missing_product_part_visibility_measurement'


def test_partial_letter_background_collision_has_versioned_panel_gate():
    measured = {'layout': [{'text': 'FIELD 600', 'bbox': [100, 300, 100, 30]},
                           {'text': 'Care', 'bbox': [100, 100, 200, 60]},
                           {'text': 'Hand wash only', 'bbox': [600, 900, 500, 60]},
                           {'text': 'Air dry before storage', 'bbox': [600, 1100, 600, 60]}],
                'group_layout': [{'bbox': [100, 300, 200, 600]}],
                'label_background_samples': [
                    {'text': 'Care', 'character_indices': []},
                    {'text': 'Hand wash only', 'character_indices': []},
                    {'text': 'Air dry before storage', 'character_indices': [0, 1, 2]}]}
    assert product.quality_issues(measured, panel=True) == []
    issues = product.quality_issues(measured, panel=True, panel_contrast=True)
    assert len(issues) == 1 and issues[0]['kind'] == 'panel_text_background_interference'
    assert issues[0]['text'] == 'Air dry before storage'
    del measured['label_background_samples']
    assert product.quality_issues(measured, panel=True, panel_contrast=True)[0]['kind'] == 'missing_panel_text_contrast_measurement'


def test_printed_label_must_fit_product_even_when_it_fits_canvas():
    measured = {'shape_layout': [{'bbox': [210, 100, 180, 620]}],
                'layout': [{'text': product.BRIEF['product_name'], 'bbox': [184, 400, 232, 50]}]}
    issue = product.source_fidelity_issues(measured, label_bounds=True)[0]
    assert issue['kind'] == 'printed_label_outside_product'
    assert issue['label_bbox'] == [184, 400, 232, 50]
    measured['layout'][0]['bbox'] = [230, 400, 140, 40]
    assert product.source_fidelity_issues(measured, label_bounds=True) == []


def test_new_package_verifier_enforces_declared_source_proportions(tmp_path, monkeypatch):
    monkeypatch.setattr(product, 'ROOT', tmp_path)
    out = tmp_path/'trial'; out.mkdir(); (out/'source').mkdir()
    for name, value in [('style', style()), ('source', source_scene())]:
        (out/(name+'-response.json')).write_text(json.dumps({'content': json.dumps(value), 'model': 'fixture', 'digest': 'f'*64}))
    (out/'source/artwork.svg').write_text(source())
    (out/'source/render.json').write_text(json.dumps({'layout': [], 'shape_layout': [{'bbox': [240, 105, 120, 635]}]}))
    report = {'status': 'pending_independent_review', 'brief': product.BRIEF, 'supplier_copy': product.PANELS,
              'model': 'fixture', 'digest': 'f'*64, 'source_fidelity_contract': product.SOURCE_FIDELITY_CONTRACT,
              'artifacts': {str(p.relative_to(out)): product.school.checksum(p) for p in out.rglob('*') if p.is_file()}}
    (out/'report.json').write_text(json.dumps(report))
    with pytest.raises(ValueError, match='supplier proportions'):
        product.verify(out)


def test_rejected_latest_response_cannot_be_replaced_by_earlier_pass(tmp_path):
    for name in ['source', 'source-revision-1']:
        (tmp_path/(name+'-response.json')).write_text(json.dumps({'content': 'fixture'}))
    (tmp_path/'source-revision-1-feedback.json').write_text('{}')
    with pytest.raises(ValueError, match='rejected'): product.accepted_raw(tmp_path, 'source')


def test_verifier_replays_raw_answer_even_when_file_hashes_are_updated(tmp_path, monkeypatch):
    monkeypatch.setattr(product, 'ROOT', tmp_path)
    out = tmp_path/'trial'; out.mkdir(); (out/'source').mkdir()
    for name, value in [('style', style()), ('source', source_scene())]:
        (out/(name+'-response.json')).write_text(json.dumps({'content': json.dumps(value), 'model': 'fixture', 'digest': 'f'*64}))
    (out/'source/artwork.svg').write_text(source().replace('#003388', '#FFFFFF'))
    report = {'status': 'pending_independent_review', 'brief': product.BRIEF, 'supplier_copy': product.PANELS,
              'model': 'fixture', 'digest': 'f'*64,
              'artifacts': {str(p.relative_to(out)): product.school.checksum(p) for p in out.rglob('*') if p.is_file()}}
    (out/'report.json').write_text(json.dumps(report))
    with pytest.raises(ValueError, match='differs from raw'): product.verify(out)


def test_style_and_schema_keep_local_values_and_explicit_text_anchors():
    assert product.style_value(json.dumps(style())) == style()
    invalid = style(); invalid['ink'] = 'Juniper'
    with pytest.raises(ValueError): product.style_value(json.dumps(invalid))
    schema = product.schema('panel', style())
    assert 'text-anchor' in schema['properties']['texts']['items']['properties']['attributes']['required']
    assert schema['properties']['texts']['minItems'] == 3


def test_numeric_failure_identifies_attribute_value_and_source_canvas():
    value = source_scene(); value['shapes'][0]['attributes']['y'] = '1940'
    with pytest.raises(ValueError, match=r'rect.y=1940.*600x800'):
        product.compile_scene(json.dumps(value), style())


def test_focused_stage_instructions_exclude_the_other_stage_contract():
    source = product.stage_rules('source', focused=True)
    panel = product.stage_rules('capacity', focused=True)
    assert '600x800' in source and '1500x1500' not in source
    assert 'product_placement' not in source and 'EXACTLY THREE' not in source
    assert '1500x1500' in panel and '600x800' not in panel
    assert 'EXACTLY ONE name' not in panel
    assert product.stage_rules('source') == product.SCENE_RULES
    with pytest.raises(ValueError, match='Known product stage'):
        product.stage_rules('unknown', focused=True)


def test_continuation_requires_unchanged_failure_and_cannot_repeat_forever(tmp_path, monkeypatch):
    monkeypatch.setattr(product, 'ROOT', tmp_path)
    out = tmp_path/'trial'; out.mkdir()
    report = {'schema': 'product-infographic-school.v1', 'status': 'failed', 'brief': product.BRIEF,
              'supplier_copy': product.PANELS, 'stages': [], 'model': 'fixture', 'digest': 'f'*64}
    (out/'style-response.json').write_text(json.dumps({'content': '{}', 'model': 'fixture', 'digest': 'f'*64}))
    (out/'style-request.json').write_text('{}')
    feedback = {'stage': 'style', 'request_sha256': product.school.checksum(out/'style-request.json'),
                'response_sha256': product.school.checksum(out/'style-response.json'), 'error': 'fixture failure'}
    (out/'style-feedback.json').write_text(json.dumps(feedback))
    report['artifacts'] = {p.name: product.school.checksum(p) for p in out.iterdir()}
    (out/'report.json').write_text(json.dumps(report))
    previous, failed, correction = product.resume_input(out)
    assert failed == 'style' and correction['previous_answer'] == '{}'
    report['resume_round'] = 1; (out/'report.json').write_text(json.dumps(report))
    with pytest.raises(ValueError, match='one bounded continuation'): product.resume_input(out)
    report.pop('resume_round'); (out/'report.json').write_text(json.dumps(report))
    (out/'style-response.json').write_text('changed')
    with pytest.raises(ValueError, match='evidence changed'): product.resume_input(out)
