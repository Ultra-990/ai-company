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
