from copy import deepcopy
import json
import xml.etree.ElementTree as ET
from PIL import Image
import pytest

from scripts import brand_artwork_repair as repair
from scripts import brand_school as b
from scripts import verify_brand_package as evidence


def contributions(*pixels):
    return {'shape_contributions': [{'index': i, 'tag': 'path', 'changed_pixels': v} for i, v in enumerate(pixels)]}


def test_monochrome_requires_visible_details_to_survive_conversion():
    findings = repair.monochrome_findings(contributions(1000, 800), contributions(1000, 0))
    assert len(findings) == 1 and findings[0]['shape_index'] == 1
    assert not repair.monochrome_findings(contributions(1000, 800), contributions(900, 700))
    assert not repair.monochrome_findings(contributions(0, 10), contributions(0, 0))
    with pytest.raises(ValueError): repair.monochrome_findings(contributions(100), contributions())


def test_collision_feedback_includes_actual_geometry_without_proposed_solution():
    measured = {'layout': [{'text': 'A', 'bbox': [40, 40, 100, 40]}, {'text': 'B', 'bbox': [40, 60, 100, 40]}], 'shape_layout': [], 'group_layout': []}
    feedback = b.measured_feedback(measured, 'brand_card')
    assert any(i['kind'] == 'text_overlap' for i in feedback['issues'])
    assert feedback['text_layout'] == measured['layout']
    assert set(feedback) == {'issues', 'coordinate_system', 'text_layout', 'shape_layout', 'group_layout'}


@pytest.fixture
def repaired(tmp_path, monkeypatch, request):
    strict = getattr(request, 'param', False)
    monkeypatch.setattr(b, 'ROOT', tmp_path)
    monkeypatch.setattr(b.school, 'check_idle', lambda: {})
    monkeypatch.setattr(b, 'configuration', lambda: {'model': 'fixture', 'digest': 'f'*64})
    plan = {'positioning': 'A synthetic software fixture only.', 'tagline': 'Fixture tagline',
        'ink': '#123456', 'paper': '#FFFFFF', 'accent': '#654321', 'monochrome_ink': '#000000',
        'heading_font': 'Arial', 'body_font': 'Arial', 'concept_a': 'First synthetic fixture direction.',
        'concept_b': 'Second synthetic fixture direction.', 'guidelines': ['Only a synthetic unit-test rule.' for _ in range(4)]}
    def text(value, y):
        return {'text': value, 'attributes': {'x': '50', 'y': str(y), 'font-size': '40', 'font-family': 'Arial', 'font-weight': '400', 'fill': plan['ink'], 'text-anchor': 'start'}}
    a = {'shapes': [{'tag': 'circle', 'attributes': {'cx': '80', 'cy': '80', 'r': '20', 'fill': plan['accent']}}], 'texts': [text(b.BRIEF['restaurant_name'], 250)]}
    other = deepcopy(a); other['shapes'][0]['attributes']['r'] = '30'
    card = {'shapes': [{'tag': 'rect', 'attributes': {'x': '0', 'y': '0', 'width': '850', 'height': '550', 'fill': plan['paper']}}],
        'logo_placement': {'x': '40', 'y': '40', 'scale': '0.5'},
        'texts': [text(v, 300+i*45) for i, v in enumerate([plan['tagline'], *b.BRIEF['contacts']])]}
    corrected = deepcopy(a); corrected['shapes'][0]['attributes']['r'] = '24'
    corrected_card = deepcopy(card)
    if strict:
        card['shapes'].append({'tag': 'rect', 'attributes': {'x': '40', 'y': '40', 'width': '8', 'height': '8', 'fill': plan['accent']}})
    values = iter([plan, a, other, {'selected': 'a', 'reason': 'A synthetic fixture selection.'}, card, corrected, corrected_card])
    class Provider:
        def __init__(self, config): pass
        def complete(self, messages):
            return {'model': 'fixture', 'digest': 'f'*64, 'content': json.dumps(next(values))}
    monkeypatch.setattr(b, 'OllamaProvider', Provider)
    async def render(svg, output, *, profile, png_scale=1, measure_shape_contribution=False):
        baseline = Image.new('RGB', (int(b.PROFILES[profile]['width']*png_scale), int(b.PROFILES[profile]['height']*png_scale)), 'white')
        baseline.save(output/'preview.png')
        (output/'preview.pdf').write_bytes(b'%PDF-fixture')
        texts = b.validate_svg(svg, profile=profile)['texts']
        result = {'layout': [{'text': v, 'bbox': [40, 40+i*60, 100, 40]} for i,v in enumerate(texts)], 'shape_layout': [{'tag': 'circle', 'bbox': [40, 380, 20, 20]}], 'pdf': {'fixture': True}}
        if profile == 'brand_card':
            result['shape_layout'] = []
            for element in ET.fromstring(svg).iter():
                tag = element.tag.rsplit('}', 1)[-1]
                if tag == 'rect':
                    result['shape_layout'].append({'tag': tag, 'bbox': [float(element.get(k)) for k in ('x', 'y', 'width', 'height')]})
                elif tag == 'circle':
                    result['shape_layout'].append({'tag': tag, 'bbox': [40, 380, 20, 20]})
        if measure_shape_contribution:
            pixels = 0 if output.name == 'monochrome' and output.parent.name == 'initial-logo' else 100
            result.update(contributions(pixels))
            for x in range(pixels): baseline.putpixel((x, 0), (0, 0, 0))
            baseline.save(output/'shape-removed-0.png')
        return result
    monkeypatch.setattr(b, 'render', render)
    monkeypatch.setattr(evidence, 'pdf_checks', lambda *a, **kw: {})
    source, original = b.run()
    assert original['status'] == 'pending_independent_visual_review'
    out, report = repair.run(source, strict_card=strict)
    assert report['status'] == 'pending_independent_visual_review'
    return source, out, report


def test_repair_reuses_protected_stages_and_exports_full_literal_package(repaired):
    source, out, report = repaired
    verified = evidence.verify(out)
    assert verified['zip_files'] == 21
    assert verified['repair_origin']['additional_model_calls'] == 1
    assert verified['repair_origin']['repaired_stages'] == ['logo-a']
    assert (source/'plan-response.json').read_bytes() == (out/'plan-response.json').read_bytes()
    assert not verified['repair_origin']['fresh_exam']


@pytest.mark.parametrize('repaired', [True], indirect=True)
def test_strict_card_repair_replays_authorship_and_rejects_reintroduced_decoration(repaired):
    source, out, report = repaired
    verified = evidence.verify(out)
    assert verified['repair_origin']['schema'] == repair.CARD_CONTRACT
    assert verified['repair_origin']['repaired_stages'] == ['logo-a', 'card']
    assert verified['repair_origin']['additional_model_calls'] == 2
    # Even rebinding the report cannot hide an invalid final measured layout.
    name = 'business-card/render.json'
    measured = evidence.read(out/name)
    measured['shape_layout'][0]['bbox'] = [40, 40, 8, 8]
    b.school.save(out/name, measured)
    report['artifacts'][name] = b.school.checksum(out/name)
    b.school.save(out/'report.json', report)
    with pytest.raises(ValueError, match='still enters text bounds'):
        evidence.verify(out)


@pytest.mark.parametrize('fault', ['diagnostic', 'protected', 'extra_hint', 'source', 'qualify'])
def test_rebound_changes_cannot_hide_repair_origin_or_invent_feedback(repaired, fault):
    source, out, report = repaired
    name = 'initial-logo-feedback.json'
    if fault == 'diagnostic':
        value = evidence.read(out/name); value['issues'][0]['shape_index'] = 9
    elif fault == 'protected':
        name = 'selection-response.json'; value = evidence.read(out/name); value['content'] = '{}'
    elif fault == 'extra_hint':
        name = 'logo-a-request.json'; value = evidence.read(out/name); value['user'] += 'teacher coordinates'
    elif fault == 'source':
        name = 'repair-origin.json'; value = evidence.read(out/name); value['source_report_sha256'] = 'a'*64
    else:
        report['autonomy_qualified'] = True; value = evidence.read(out/name)
    b.school.save(out/name, value)
    report['artifacts'][name] = b.school.checksum(out/name); b.school.save(out/'report.json', report)
    with pytest.raises(ValueError): evidence.verify(out)
