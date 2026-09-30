import json
import pytest
from scripts import brand_scene_contract as scoped
from scripts import brand_wordmark_review as lines


def test_wrong_copy_reports_actual_and_required_values_without_repairing_them():
    with pytest.raises(ValueError) as error:
        scoped.compile_scene(json.dumps({'shapes': [], 'texts': [{'text': 'A tagline'}]}), {}, kind='logo', brief={'restaurant_name': 'Exact Name'})
    finding = json.loads(str(error.value))
    assert finding['observed_texts'] == ['A tagline'] and finding['expected_texts'] == ['Exact Name']


def test_schema_constrains_copy_from_brief_not_a_fixed_example():
    schema = scoped.schema('logo', {'ink':'#111111','paper':'#FFFFFF','accent':'#AABBCC','heading_font':'Arial'}, {'restaurant_name':'Different Name'})
    assert schema['properties']['texts']['items']['properties']['text']['enum'] == ['Different Name']
    assert '850x550' not in scoped.rules('logo')


def test_margin_check_includes_stroke_and_measures_other_logo_geometry():
    svg = '<svg><path d="M 150 340 L 450 340" fill="none" stroke="#111111" stroke-width="4"/></svg>'
    data = {'shape_layout':[{'tag':'path','bbox':[150,339,300,12]}]}
    assert scoped.margin_findings(svg,data,'logo','#FFFFFF')[0]['measured_bounds_with_half_stroke'] == [148,337,452,353]
    data['shape_layout'][0]['bbox']=[150,300,300,12]
    assert not scoped.margin_findings(svg,data,'logo','#FFFFFF')


def test_inserted_logo_stroke_is_scaled_and_only_paper_background_is_exempt():
    svg='<svg><rect fill="#FFFFFF"/><g transform="translate(20 40) scale(0.5)"><path fill="none" stroke="#111111" stroke-width="8"/></g></svg>'
    data={'shape_layout':[{'tag':'rect','bbox':[0,0,850,550]},{'tag':'path','bbox':[36,100,100,10]}]}
    issues=scoped.margin_findings(svg,data,'card','#FFFFFF')
    assert len(issues)==1 and issues[0]['measured_bounds_with_half_stroke'][0]==34


def test_plain_wordmark_fact_refuses_to_guess_about_multiline_extensions():
    assert lines.line_count('<svg><text>Two Words</text></svg>') == 1
    for svg in ('<svg><text><tspan>Two</tspan><tspan>Words</tspan></text></svg>', '<svg><text>A\nB</text></svg>', '<svg><text>A</text><text>B</text></svg>'):
        with pytest.raises(ValueError): lines.line_count(svg)


def test_model_extracted_multiple_line_claim_vetoes_approval_but_unspecified_does_not():
    texts={'a':'A bowl above the stacked wordmark.','b':'A symbol above the wordmark.'}
    claims={'concepts':[{'id':key,'claims':[{'relation':'above','quote':'above the'}],
        'wordmark_lines': {'relation':'multiple','quote':'stacked wordmark'} if key=='a' else {'relation':'unspecified','quote':''}} for key in texts]}
    parsed=lines.claims_value(json.dumps(claims),texts)
    data={'plan':{'concept_a':texts['a'],'concept_b':texts['b'],'monochrome_ink':'#111111','guidelines':[]},
          'spatial_measurements':{k:{'necessary_conditions':{'above':True}} for k in texts},'wordmark_line_counts':{'a':1,'b':1}}
    review={'reviews':[{'index':i,'verdict':'supported','reason':'The model approved it.'} for i in range(6)]}
    result,findings=lines.combine(review,parsed,data)
    assert result['reviews'][4]['verdict']=='unsupported' and result['reviews'][5]['verdict']=='supported'
    assert findings[0]['actual_lines']==1 and review['reviews'][4]['verdict']=='supported'
    claims['concepts'][0]['wordmark_lines']['quote']='invented quote'
    with pytest.raises(ValueError): lines.claims_value(json.dumps(claims),texts)
