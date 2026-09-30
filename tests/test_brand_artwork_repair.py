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
    source_visible = strict == 'visible-source'
    source_scoped = strict in ('scoped-source', 'visible-source')
    if source_scoped: strict = False
    visible = strict == 'visible'
    full = strict in ('full', 'visible')
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
    corrected_other = deepcopy(other); corrected_other['shapes'][0]['attributes']['r'] = '28'
    answers = [plan, a, other, {'selected': 'a', 'reason': 'A synthetic fixture selection.'}, card, corrected]
    if full: answers.append(corrected_other)
    values = iter(answers+[corrected_card])
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
        if profile == 'brand_logo':
            result['shape_layout'][0]['bbox'] = [200, 341 if full and not visible and 'r="30"' in svg else 100, 20, 20]
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
            if visible and (output.name in ('initial-logo', 'initial-alternate') or output.parent.name in ('initial-logo', 'initial-alternate')):
                pixels = 0
            result.update(contributions(pixels))
            for x in range(pixels): baseline.putpixel((x, 0), (0, 0, 0))
            baseline.save(output/'shape-removed-0.png')
        return result
    monkeypatch.setattr(b, 'render', render)
    monkeypatch.setattr(evidence, 'pdf_checks', lambda *a, **kw: {})
    source, original = b.run(scoped_scenes=source_scoped, visible_shapes=source_visible)
    assert original['status'] == 'pending_independent_visual_review'
    out, report = repair.run(source, strict_card=bool(strict), full_scene=full, visible_shapes=visible)
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


@pytest.mark.parametrize('repaired', ['scoped-source'], indirect=True)
def test_new_generation_applies_scoped_copy_and_margins_before_acceptance(repaired):
    source, _, _ = repaired
    assert evidence.read(source/'report.json')['scene_contract'] == 'brand-scoped-scene.v1'
    assert evidence.verify(source)['literal_authorship_verified']
    schema = evidence.read(source/'logo-b-request.json')['format']
    assert schema['properties']['texts']['items']['properties']['text']['enum'] == [b.BRIEF['restaurant_name']]


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


@pytest.mark.parametrize('repaired', ['full'], indirect=True)
def test_complete_scene_checks_repair_alternate_logo_and_replay_all_three_stages(repaired):
    source, out, report = repaired
    verified = evidence.verify(out)
    assert verified['repair_origin']['schema'] == repair.FULL_CONTRACT
    assert verified['repair_origin']['repaired_stages'] == ['logo-a', 'logo-b', 'card']
    assert verified['repair_origin']['additional_model_calls'] == 3
    name = 'logo-b/render.json'; data = evidence.read(out/name)
    data['shape_layout'][0]['bbox'][1] = 341
    b.school.save(out/name, data)
    report['artifacts'][name] = b.school.checksum(out/name); b.school.save(out/'report.json', report)
    with pytest.raises(ValueError, match='violates margins'): evidence.verify(out)


def test_exhausted_second_logo_can_be_completed_as_separate_development_work(repaired, monkeypatch):
    from scripts import brand_scene_recovery as recovery
    import shutil
    source, _, _ = repaired
    original=evidence.read(source/'report.json')
    failed=source.parent/'failed-second-logo';failed.mkdir()
    for stage in ('plan','logo-a'):
        for p in source.glob(stage+'*-*.json'): shutil.copyfile(p,failed/p.name)
    shutil.copyfile(source/'plan.json',failed/'plan.json')
    plan=evidence.read(source/'plan.json')
    second=json.loads(evidence.chain(source,'logo-b',original)[0])
    wrong=deepcopy(second);wrong['texts'][0]['text']='Wrong tagline'
    replies=iter([wrong,wrong,wrong])
    class Provider:
        def __init__(self,config): pass
        def complete(self,messages):
            return {'model':'fixture','digest':'f'*64,'content':json.dumps(next(replies))}
    monkeypatch.setattr(b,'OllamaProvider',Provider)
    with pytest.raises(ValueError):
        b.validated_call(failed,'logo-b','fixture','fixture',{},original['config'],lambda raw:b.compile_scene(raw,plan,kind='logo'))
    stopped=original|{'status':'failed','stages':['plan','logo-a']}
    stopped['artifacts']={str(p.relative_to(failed)):b.school.checksum(p) for p in failed.rglob('*') if p.is_file()}
    b.school.save(failed/'report.json',stopped)
    replies=iter([second,json.loads(evidence.chain(source,'selection',original)[0]),json.loads(evidence.chain(source,'card',original)[0])])
    out,report=recovery.run(failed)
    assert report['status']=='pending_independent_visual_review'
    result=evidence.verify(out)
    assert result['scene_recovery_origin']['additional_model_calls']==3
    assert not result['scene_recovery_origin']['fresh_exam']
    assert (out/'logo-a-response.json').read_bytes()==(failed/'logo-a-response.json').read_bytes()
    report['fresh_exam']=True;b.school.save(out/'report.json',report)
    with pytest.raises(ValueError,match='nonqualification boundary'):evidence.verify(out)


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


@pytest.mark.parametrize('pixels', [(0, 0), (0, 100), (100, 0)])
def test_visibility_rejects_unobservable_components_even_if_monochrome_matches(pixels):
    findings = repair.visibility_findings(contributions(*pixels))
    assert [v['shape_index'] for v in findings] == [i for i, count in enumerate(pixels) if count == 0]
    assert not repair.monochrome_findings(contributions(*pixels), contributions(*pixels))
    assert not repair.visibility_findings(contributions(1, 100))
    for bad in (-1, True, 0.0):
        with pytest.raises(ValueError): repair.visibility_findings(contributions(bad))


@pytest.mark.parametrize('repaired', ['visible'], indirect=True)
@pytest.mark.parametrize('target', ['logo-a', 'logo-b'])
def test_visibility_repairs_both_logos_and_rechecks_actual_ablation_evidence(repaired, target):
    source, out, report = repaired
    result = evidence.verify(out)
    assert result['repair_origin']['schema'] == repair.VISIBLE_CONTRACT
    assert result['repair_origin']['repaired_stages'] == ['logo-a', 'logo-b', 'card']
    assert result['repair_origin']['additional_model_calls'] == 3
    for name in ('initial-logo', 'initial-alternate'):
        feedback = evidence.read(out/(name+'-feedback.json'))
        assert [v['kind'] for v in feedback['issues']] == ['shape_has_no_measurable_contribution']
    # Rebind both counts AND underlying PNG so the pixel audit passes, while
    # the accepted component no longer contributes. Visibility must still fail.
    folder = out/(target+'-layout-0')
    (folder/'shape-removed-0.png').write_bytes((folder/'preview.png').read_bytes())
    measured = evidence.read(folder/'render.json')
    measured['shape_contributions'][0]['changed_pixels'] = 0
    b.school.save(folder/'render.json', measured)
    for name in ('shape-removed-0.png', 'render.json'):
        relative = str((folder/name).relative_to(out))
        report['artifacts'][relative] = b.school.checksum(folder/name)
    b.school.save(out/'report.json', report)
    with pytest.raises(ValueError, match='unobservable component'): evidence.verify(out)


@pytest.mark.parametrize('repaired', ['visible-source'], indirect=True)
def test_new_source_checks_both_final_rasters_and_rejects_zero_contribution(repaired):
    source, _, _ = repaired
    report = evidence.read(source/'report.json')
    assert report['visibility_contract'] == repair.SOURCE_VISIBLE_CONTRACT
    assert evidence.verify(source)['literal_authorship_verified']
    for name in ('logo-a', 'logo-b'):
        assert evidence.read(source/name/'render.json')['shape_contributions']
    folder = source/'logo-b'
    (folder/'shape-removed-0.png').write_bytes((folder/'preview.png').read_bytes())
    measured = evidence.read(folder/'render.json')
    measured['shape_contributions'][0]['changed_pixels'] = 0
    b.school.save(folder/'render.json', measured)
    for name in ('shape-removed-0.png', 'render.json'):
        relative = str((folder/name).relative_to(source))
        report['artifacts'][relative] = b.school.checksum(folder/name)
    b.school.save(source/'report.json', report)
    with pytest.raises(ValueError, match='Source logo has an unobservable component'): evidence.verify(source)


def test_new_scene_returns_visibility_failure_before_accepting_the_logo(tmp_path, monkeypatch):
    svg = '<svg><circle/></svg>'
    monkeypatch.setattr(b, 'compile_scene', lambda *a, **kw: svg)
    monkeypatch.setattr(b.school, 'check_idle', lambda: {})
    counts = iter([0, 100])
    async def render(svg, folder, *, profile, measure_shape_contribution):
        assert profile == 'brand_logo' and measure_shape_contribution
        return contributions(next(counts)) | {'layout': [], 'shape_layout': []}
    monkeypatch.setattr(b, 'render', render)
    check = b.checked_scene(tmp_path, 'logo-a', {}, 'logo', visible_shapes=True)
    with pytest.raises(ValueError, match='shape_has_no_measurable_contribution'): check('{}')
    assert check('{}') == svg
    assert (tmp_path/'logo-a-layout-0/render.json').is_file()
    assert (tmp_path/'logo-a-layout-1/render.json').is_file()
