from copy import deepcopy
import pytest
from scripts import brand_artwork_repair as art
from scripts import brand_background_review as background


def card_fixture():
    svg = '''<svg xmlns="http://www.w3.org/2000/svg">
      <rect x="0" y="0" width="850" height="550" fill="#FFFFFF"/>
      <rect x="120" y="110" width="8" height="8" fill="#FFAA00"/>
      <g><circle cx="120" cy="80" r="10"/></g>
      <text x="100" y="120">Example name</text></svg>'''
    measured = {'layout': [{'text': 'Example name', 'bbox': [100, 100, 200, 30]}],
        'shape_layout': [{'tag': 'rect', 'bbox': [0, 0, 850, 550]},
                         {'tag': 'rect', 'bbox': [120, 110, 8, 8]},
                         {'tag': 'circle', 'bbox': [110, 70, 20, 20]}]}
    return svg, measured


def test_card_finds_added_decoration_without_flagging_paper_or_inserted_logo():
    svg, data = card_fixture()
    issues = art.card_decoration_findings(svg, data, '#FFFFFF')
    assert len(issues) == 1 and issues[0]['shape_index'] == 1
    assert issues[0]['intersection_bounds'] == [120, 110, 128, 118]
    data['shape_layout'][1]['bbox'][1] = 132
    assert not art.card_decoration_findings(svg, data, '#FFFFFF')


def test_card_stroke_is_included_even_for_zero_height_line():
    svg, data = card_fixture()
    svg = svg.replace('<rect x="120" y="110" width="8" height="8" fill="#FFAA00"/>',
                      '<line x1="100" y1="132" x2="300" y2="132" fill="none" stroke="#000000" stroke-width="6"/>')
    data['shape_layout'][1] = {'tag': 'line', 'bbox': [100, 132, 200, 0]}
    assert art.card_decoration_findings(svg, data, '#FFFFFF')[0]['intersection_bounds'][1:] == [129, 300, 130]


def test_shape_mapping_does_not_silently_skip_missing_or_reordered_measurements():
    svg, data = card_fixture()
    bad = deepcopy(data); bad['shape_layout'].pop()
    with pytest.raises(ValueError): art.card_decoration_findings(svg, bad, '#FFFFFF')
    data['shape_layout'].reverse()
    with pytest.raises(ValueError): art.card_decoration_findings(svg, data, '#FFFFFF')


@pytest.mark.parametrize('sentence,flag', [
    ('Apply the monochrome ink on dark backgrounds or for single-color stamping.', True),
    ('Use monochrome on black stock.', True),
    ('Use dark ink on the supplied light paper.', False),
    ('Use the paper color as the background.', False),
    # Explicitly conservative about negation; never label this a contradiction.
    ('Do not use this ink on dark backgrounds.', True),
])
def test_background_screen_marks_unverified_scope_not_invented_semantic_proof(sentence, flag):
    data = {'plan': {'monochrome_ink': '#2B2B2B', 'guidelines': [sentence]}}
    findings = background.background_findings(data)
    assert bool(findings) == flag
    if flag: assert findings[0]['kind'] == 'unverified_dark_background_scope'


def test_palette_luminance_and_light_ink_do_not_invent_dark_ink_conflict():
    assert background.luminance('#000000') == 0
    assert background.luminance('#FFFFFF') == pytest.approx(1)
    assert not background.background_findings({'plan': {'monochrome_ink': '#FFFFFF', 'guidelines': ['Use on dark backgrounds.']}})


def test_false_model_approval_is_vetoed_without_mutating_its_original_response():
    data = {'plan': {'monochrome_ink': '#222222', 'guidelines': ['Use on dark backgrounds.'],
                    'concept_a': 'A symbol.', 'concept_b': 'A symbol.'}, 'spatial_measurements': {
                        key: {'necessary_conditions': {}} for key in ('a', 'b')}}
    claims = {'concepts': [{'id': key, 'claims': [{'relation': 'unspecified', 'quote': ''}]} for key in ('a', 'b')]}
    raw = {'reviews': [{'index': i, 'verdict': 'supported', 'reason': 'The model approved it.'} for i in range(6)]}
    result, findings = background.combine(raw, claims, data)
    assert raw['reviews'][0]['verdict'] == 'supported'
    assert result['reviews'][0]['verdict'] == 'uncertain'
    assert len(findings) == 1
