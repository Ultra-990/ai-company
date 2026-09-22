"""Non-design fixtures validate literal asset reuse and independent constraints."""
import json
import xml.etree.ElementTree as ET

import pytest

from scripts import brand_school as brand
from scripts.vector_school_contract import validate_svg, layout_issues, NS
from scripts.render_school_svg import document


def plan():
    return {'positioning': 'Synthetic test fixture only, not a creative training example.', 'tagline': 'Fixture tagline',
        'ink': '#123456', 'paper': '#FFFFFF', 'accent': '#654321', 'monochrome_ink': '#000000',
        'heading_font': 'Georgia', 'body_font': 'Arial', 'concept_a': 'First synthetic fixture description.',
        'concept_b': 'Second synthetic fixture description.', 'guidelines': ['Only a synthetic unit-test rule.' for _ in range(4)]}


def text(value, y, font='Arial'):
    return {'text': value, 'attributes': {'x': '40', 'y': str(y), 'font-family': font,
        'font-size': '40', 'font-weight': '400', 'fill': '#123456'}}


def logo():
    data = {'shapes': [{'tag': 'rect', 'attributes': {'x': '30', 'y': '30', 'width': '10', 'height': '10', 'fill': '#654321'}}],
            'texts': [text(brand.BRIEF['restaurant_name'], 100, 'Georgia')]}
    return brand.compile_scene(json.dumps(data), plan(), kind='logo')


def card():
    return {'shapes': [{'tag': 'rect', 'attributes': {'x': '0', 'y': '0', 'width': '850', 'height': '550', 'fill': '#FFFFFF'}}],
        'logo_placement': {'x': '40', 'y': '40', 'scale': '0.5'},
        'texts': [text(value, 300+i*50) for i, value in enumerate([plan()['tagline'], *brand.BRIEF['contacts']])]}


def test_card_reuses_exact_model_logo_with_only_its_chosen_placement():
    source = logo(); result = brand.compile_scene(json.dumps(card()), plan(), kind='card', logo=source)
    group = ET.fromstring(result).find(NS+'g')
    assert group.attrib == {'transform': 'translate(40 40) scale(0.5)'}
    assert [ET.tostring(n) for n in group] == [ET.tostring(n) for n in ET.fromstring(source)]
    assert validate_svg(result, profile='brand_card')['editable_text_count'] == 5
    assert 'size:85mm 55mm' in document(result, profile='brand_card')
    with pytest.raises(ValueError): validate_svg(result)


def test_monochrome_changes_only_paints_to_the_model_chosen_ink():
    source = logo(); converted = brand.monochrome(source, plan()['monochrome_ink'])
    before, after = ET.fromstring(source), ET.fromstring(converted)
    for original, actual in zip(before, after):
        assert actual.tag == original.tag and actual.text == original.text
        assert actual.attrib == {k: '#000000' if k in {'fill', 'stroke'} and v != 'none' else v for k,v in original.attrib.items()}
    with pytest.raises(ValueError): brand.monochrome(source.replace('</svg>', '<!-- hidden --></svg>'), '#000000')


@pytest.mark.parametrize('defect', ['contact', 'palette', 'font', 'placement', 'script', 'extra_field'])
def test_invalid_model_assets_are_rejected_without_teacher_repair(defect):
    data = card()
    if defect == 'contact': data['texts'][1]['text'] = 'invented@real.invalid'
    elif defect == 'palette': data['texts'][0]['attributes']['fill'] = '#FF00FF'
    elif defect == 'font': data['texts'][0]['attributes']['font-family'] = 'Georgia'
    elif defect == 'placement': data['logo_placement']['scale'] = '100'
    elif defect == 'script': data['shapes'][0]['attributes']['onclick'] = 'alert(1)'
    elif defect == 'extra_field': data['notes'] = 'extra'
    with pytest.raises(ValueError): brand.compile_scene(json.dumps(data), plan(), kind='card', logo=logo())


def test_brand_profile_does_not_weaken_leaflet_or_nested_group_safety():
    source = brand.compile_scene(json.dumps(card()), plan(), kind='card', logo=logo())
    with pytest.raises(ValueError): validate_svg(source.replace('translate(40 40) scale(0.5)', 'rotate(30)'), profile='brand_card')
    with pytest.raises(ValueError): validate_svg(source.replace('<g transform=', '<g><g transform=').replace('</g>', '</g></g>'), profile='brand_card')
    box = [{'text': 'fixture', 'bbox': [20, 20, 100, 30]}]
    assert not layout_issues(box, profile='brand_logo')
    assert layout_issues(box, profile='brand_card')[0]['kind'] == 'text_margin_or_bounds'


def test_plan_requires_distinct_real_colors_and_usage_rules():
    assert brand.plan_value(json.dumps(plan())) == plan()
    invalid = plan(); invalid['accent'] = invalid['ink']
    with pytest.raises(ValueError): brand.plan_value(json.dumps(invalid))
    invalid = plan(); invalid['tagline'] = 'An unfinished tagline, '
    with pytest.raises(ValueError): brand.plan_value(json.dumps(invalid))


def test_invalid_plan_returns_to_model_without_replacing_its_answer(tmp_path, monkeypatch):
    invalid = plan(); invalid['ink'] = 'Juniper'
    replies = iter([json.dumps(invalid), json.dumps(plan())]); requests = []
    class Provider:
        def __init__(self, config): pass
        def complete(self, messages):
            requests.append(messages)
            return {'model': 'fixture', 'digest': 'f'*64, 'content': next(replies)}
    monkeypatch.setattr(brand, 'OllamaProvider', Provider)
    monkeypatch.setattr(brand.school, 'check_idle', lambda: {'fixture': True})
    actual = brand.validated_call(tmp_path, 'plan', 'fixture system', 'fixture brief', {},
                                  {'model': 'fixture', 'digest': 'f'*64}, brand.plan_value)
    assert actual == plan() and len(requests) == 2
    assert json.dumps(invalid) in requests[1][-1]['content']
    assert json.loads((tmp_path/'plan-response.json').read_text())['content'] == json.dumps(invalid)
    assert (tmp_path/'plan-feedback.json').exists()


def test_logo_collision_and_small_print_are_not_hidden_by_valid_svg():
    measured = {'layout': [{'text': 'fixture', 'bbox': [100, 200, 250, 48]}],
                'shape_layout': [{'tag': 'path', 'bbox': [90, 190, 300, 60]}]}
    assert brand.quality_issues(measured, 'brand_logo')[0]['kind'] == 'logo_symbol_overlaps_wordmark'
    measured['layout'][0]['bbox'] = [40, 40, 100, 23]
    assert brand.quality_issues(measured, 'brand_card')[0]['kind'] == 'print_text_too_small'
    with pytest.raises(ValueError): brand.selected_value('{"selected":"b","reason":"An unfinished explanation, "}')
    assert 'text-anchor' in brand.scene_schema('logo', plan())['properties']['texts']['items']['properties']['attributes']['required']
