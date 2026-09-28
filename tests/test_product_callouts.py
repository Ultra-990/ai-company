"""Counterexamples for annotation meaning, separate from technical layout."""
from copy import deepcopy
import asyncio
import os

import pytest

from scripts import product_callouts as callouts

STYLE = {'body_color': '#225588', 'cap_color': '#112233'}


def segment(a, b, fills=(None, None)):
    return {'kind': 'line', 'start': a, 'end': b, 'stroke_width': 3,
            'product_endpoint_fills': list(fills), 'visible_samples': 7}


def measured(panel):
    facts = ('Height: 24 cm', 'Diameter: 7 cm') if panel == 'dimensions' else ('Body: stainless steel', 'Lid: polypropylene')
    return {'group_layout': [{'bbox': [800, 300, 280, 960]}],
            'layout': [{'text': 'fixture', 'bbox': [820, 900, 200, 50]},
                       {'text': 'Product details', 'bbox': [300, 70, 800, 70]},
                       {'text': facts[0], 'bbox': [300, 700, 380, 60]},
                       {'text': facts[1], 'bbox': [810, 1370, 400, 60]}],
            'panel_line_segments': [segment([740, 300], [740, 1260]), segment([800, 1310], [1080, 1310])]}


def test_dimensions_need_actual_span_and_nearby_correct_label():
    data = measured('dimensions')
    assert callouts.issues(data, 'dimensions', STYLE) == []
    for replacement in ([740, 1100], [740, 1350], [950, 1260]):
        bad = deepcopy(data); bad['panel_line_segments'][0]['end'] = replacement
        assert callouts.issues(bad, 'dimensions', STYLE)[0]['fact'] == 'Height: 24 cm'
    bad = deepcopy(data); bad['layout'][2]['bbox'] = [50, 100, 300, 60]
    assert callouts.issues(bad, 'dimensions', STYLE)


@pytest.mark.parametrize('fault', ['invisible', 'inside', 'too_far', 'short_diameter'])
def test_decorative_lines_do_not_prove_dimensions(fault):
    data = measured('dimensions'); line = data['panel_line_segments'][1]
    if fault == 'invisible': line['visible_samples'] = 0
    if fault == 'inside': line['start'][1] = line['end'][1] = 900
    if fault == 'too_far': line['start'][1] = line['end'][1] = 1490
    if fault == 'short_diameter': line['end'][0] = 980
    assert callouts.issues(data, 'dimensions', STYLE)[0]['fact'] == 'Diameter: 7 cm'


def test_visible_rectangle_dimensions_are_equivalent_only_under_new_contract():
    data = measured('dimensions')
    for line in data['panel_line_segments']: line['kind'] = 'rectangle_bar'
    assert callouts.issues(data, 'dimensions', STYLE, contract=callouts.LINE_CONTRACT)
    assert callouts.issues(data, 'dimensions', STYLE) == []
    data['panel_line_segments'][0]['visible_samples'] = 0
    assert callouts.issues(data, 'dimensions', STYLE)


def material_data():
    data = measured('materials'); data['layout'][3]['bbox'] = [300, 250, 380, 60]
    data['panel_line_segments'] = [
        segment([850, 800], [750, 800], (callouts.paint(STYLE['body_color']), None)),
        segment([750, 800], [720, 740]),
        segment([850, 320], [720, 280], (callouts.paint(STYLE['cap_color']), None)),
    ]
    return data


def test_materials_require_connected_chain_touching_correct_visible_part():
    data = material_data()
    assert callouts.issues(data, 'materials', STYLE) == []
    for fault in ('disconnected', 'wrong_part', 'missing_sample', 'invisible', 'distant_fact'):
        bad = deepcopy(data)
        if fault == 'disconnected': bad['panel_line_segments'][1]['start'] = [770, 800]
        if fault == 'wrong_part': bad['panel_line_segments'][0]['product_endpoint_fills'][0] = callouts.paint(STYLE['cap_color'])
        if fault == 'missing_sample': bad['panel_line_segments'][0].pop('product_endpoint_fills')
        if fault == 'invisible': bad['panel_line_segments'][1]['visible_samples'] = 0
        if fault == 'distant_fact': bad['layout'][2]['bbox'] = [50, 1200, 380, 60]
        assert callouts.issues(bad, 'materials', STYLE), fault


def test_leader_cycles_terminate_without_implying_proximity():
    lines = [segment([800, 800], [900, 800], (callouts.paint(STYLE['body_color']), None)),
             segment([900, 800], [900, 900]), segment([900, 900], [800, 800])]
    assert not callouts.connected_to_fact(lines, callouts.paint(STYLE['body_color']), [50, 50, 100, 60])


def test_crossing_leaders_are_rejected_without_rewriting_historical_contract():
    data = material_data()
    data['panel_line_segments'] += [segment([900, 500], [1100, 700]), segment([900, 700], [1100, 500])]
    assert callouts.issues(data, 'materials', STYLE, contract=callouts.LEGACY_CONTRACT) == []
    issues = callouts.issues(data, 'materials', STYLE)
    assert issues == [{'kind': 'crossed_material_leaders', 'line_indices': [3, 4],
                       'intersection': [1000, 600], 'required': 'route leaders without interior crossings'}]
    assert callouts.crossing_point(segment([0, 0], [100, 0]), segment([100, 0], [100, 100])) is None


def test_subpixel_contact_is_new_version_only_and_cannot_override_wrong_or_ambiguous_part():
    data = material_data(); line = data['panel_line_segments'][0]
    body = callouts.paint(STYLE['body_color']); cap = callouts.paint(STYLE['cap_color'])
    line.update(product_endpoint_fills=[None, None], endpoint_contact_radius=1,
                product_endpoint_contact_fills=[[body], []])
    assert callouts.issues(data, 'materials', STYLE) == []
    assert callouts.issues(data, 'materials', STYLE, contract=callouts.RECTANGLE_CONTRACT)
    line['product_endpoint_fills'][0] = cap
    assert callouts.issues(data, 'materials', STYLE)
    line['product_endpoint_fills'][0] = None
    line['product_endpoint_contact_fills'][0] = [body, cap]
    assert callouts.issues(data, 'materials', STYLE)
    line['product_endpoint_contact_fills'][0] = [body]
    line['endpoint_contact_radius'] = 6
    assert callouts.issues(data, 'materials', STYLE)


@pytest.mark.parametrize('panel', ['dimensions', 'materials'])
def test_fact_roles_follow_exact_copy_not_array_position_only_in_new_contract(panel):
    data = measured(panel) if panel == 'dimensions' else material_data()
    data['layout'][2:] = data['layout'][2:][::-1]
    assert callouts.issues(data, panel, STYLE) == []
    assert callouts.issues(data, panel, STYLE, contract=callouts.CONTACT_CONTRACT)


@pytest.mark.parametrize('headline', ['Built From What Lasts', 'Leakproof assurance', 'Certified quality', 'Sustainable choice'])
def test_unsubstantiated_headline_fails_even_with_exact_supplier_copy(headline):
    data = measured('capacity'); data['layout'][1]['text'] = headline
    assert callouts.issues(data, 'capacity', STYLE)[0]['kind'] == 'unsupported_headline_claim'


def test_contract_is_explicit_and_unknown_versions_rejected():
    callouts.validate_contract(None); callouts.validate_contract(callouts.CONTRACT)
    with pytest.raises(ValueError): callouts.validate_contract('future')


def test_stage_instructions_do_not_assign_dimension_tasks_to_care():
    assert '20..180' in callouts.stage_rules('dimensions')
    assert '80 units' in callouts.stage_rules('materials')
    for part in ('care', 'capacity'):
        assert '20..180' not in callouts.stage_rules(part)
        assert 'do not introduce them here' in callouts.stage_rules(part)
    with pytest.raises(ValueError): callouts.stage_rules('source')


@pytest.mark.skipif(os.environ.get('AIC_CALLOUT_BROWSER_PILOT') != '1', reason='Explicit isolated headless browser pilot')
def test_browser_endpoints_use_frontmost_part_paint_and_detect_invisible_lines(tmp_path):
    from scripts.render_school_svg import render
    # Non-product measurement fixture: two overlapping squares, four line probes.
    text = lambda word, y: f'<text x="80" y="{y}" font-family="Arial" font-size="44" font-weight="400" fill="#112233">{word}</text>'
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="1500" viewBox="0 0 1500 1500">'
    svg += '<rect x="0" y="0" width="1500" height="1500" fill="#FFFFFF"/>'
    for y, color in ((550, '#112233'), (650, '#112233'), (450, '#FFFFFF'), (400, '#112233')):
        svg += f'<line x1="350" y1="{y}" x2="550" y2="{y}" stroke="{color}" stroke-width="4"/>'
    svg += '<rect x="350" y="578" width="200" height="4" fill="#112233"/>'
    svg += '<rect x="350" y="478" width="200" height="4" fill="#FFFFFF"/>'
    svg += '<line x1="700.25" y1="650" x2="900" y2="650" stroke="#112233" stroke-width="4"/>'
    svg += '<line x1="702" y1="675" x2="900" y2="675" stroke="#112233" stroke-width="4"/>'
    svg += '<rect x="700.25" y="620" width="200" height="4" fill="#112233"/>'
    svg += '<g transform="translate(0 0) scale(1)"><rect x="500" y="500" width="200" height="200" fill="#225588"/>'
    svg += '<rect x="500" y="500" width="200" height="100" fill="#112233"/>'
    svg += text('Fixture', 1000)+'</g>'+text('Probe one', 100)+text('Probe two', 200)+text('Probe three', 300)+'</svg>'
    result = asyncio.run(render(svg, tmp_path, profile='product_infographic_v2'))
    lines = result['panel_line_segments']
    assert lines[0]['product_endpoint_fills'] == [None, callouts.paint(STYLE['cap_color'])]
    assert lines[1]['product_endpoint_fills'] == [None, callouts.paint(STYLE['body_color'])]
    assert lines[0]['visible_samples'] > 0 and lines[1]['visible_samples'] > 0
    assert lines[2]['visible_samples'] == 0 and lines[3]['visible_samples'] == 9
    assert lines[4]['kind'] == 'rectangle_bar' and lines[4]['visible_samples'] > 0
    assert lines[4]['product_endpoint_fills'] == [None, callouts.paint(STYLE['cap_color'])]
    assert lines[5]['visible_samples'] == 0
    assert lines[6]['product_endpoint_fills'][0] is None
    assert lines[6]['product_endpoint_contact_fills'][0] == [callouts.paint(STYLE['body_color'])]
    assert lines[6]['endpoint_contact_radius'] == 1
    assert lines[7]['product_endpoint_contact_fills'][0] == []
    assert lines[8]['product_endpoint_fills'][0] is None
    assert lines[8]['product_endpoint_contact_fills'][0] == [callouts.paint(STYLE['body_color'])]
