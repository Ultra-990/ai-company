"""Non-design fixtures for protected group replacement and learning admission."""
from copy import deepcopy
import json
import xml.etree.ElementTree as ET

import pytest

from scripts import product_visual_revision as revision
from scripts.vector_school_contract import NS


def style():
    return {'ink': '#111111', 'paper': '#FFFFFF', 'accent': '#888888', 'body_color': '#003388',
            'cap_color': '#222222', 'heading_font': 'Arial', 'body_font': 'Georgia'}


def shape(color, x):
    return {'tag': 'rect', 'attributes': {'x': str(x), 'y': '60', 'width': '30', 'height': '40', 'fill': color}}


def scene():
    return {'shapes': [shape('#003388', 50), shape('#003388', 80), shape('#222222', 110), shape('#222222', 140)],
            'texts': [{'text': revision.product.BRIEF['product_name'], 'attributes': {'x': '60', 'y': '400',
                'font-family': 'Arial', 'font-size': '36', 'font-weight': '700', 'text-anchor': 'start', 'fill': '#111111'}}]}


def test_model_replaces_only_cap_group_and_all_other_fields_are_protected():
    original = scene(); before = deepcopy(original)
    source = revision.product.compile_scene(json.dumps(original), style())
    replacement = [shape('#222222', 170)]
    result = revision.apply_answer(json.dumps({'cap_shapes': replacement}), 'cap', style(), original, source)
    nodes = list(ET.fromstring(result))
    assert original == before
    assert [ET.tostring(n) for n in nodes[:2]] == [ET.tostring(n) for n in list(ET.fromstring(source))[:2]]
    assert ET.tostring(nodes[-1]) == ET.tostring(list(ET.fromstring(source))[-1])
    assert nodes[2].attrib == replacement[0]['attributes']
    assert len(nodes) == 4 and nodes[-1].tag == NS+'text'


@pytest.mark.parametrize('fault', ['extra_texts', 'extra_shapes', 'script', 'palette', 'empty'])
def test_teacher_tool_does_not_sanitize_or_repair_bad_model_operations(fault):
    value = {'cap_shapes': [shape('#222222', 170)]}
    if fault == 'extra_texts': value['texts'] = []
    elif fault == 'extra_shapes': value['cap_shapes'] *= 6
    elif fault == 'script': value['cap_shapes'][0]['attributes']['onclick'] = 'alert(1)'
    elif fault == 'palette': value['cap_shapes'][0]['attributes']['fill'] = '#FEDCBA'
    elif fault == 'empty': value['cap_shapes'] = []
    with pytest.raises(ValueError): revision.apply_answer(json.dumps(value), 'cap', style(), scene(), '')


def test_group_selection_cannot_include_same_color_body_or_noncontiguous_nodes():
    s = style(); s['cap_color'] = s['body_color']
    with pytest.raises(ValueError): revision.cap_indices(scene(), s)
    data = scene(); data['shapes'][0]['attributes']['fill'] = style()['cap_color']
    with pytest.raises(ValueError): revision.cap_indices(data, style())


def test_rejected_visual_review_cannot_become_a_training_record(tmp_path, monkeypatch):
    monkeypatch.setattr(revision, 'ROOT', tmp_path)
    report = tmp_path/'report.json'; report.write_text('{}')
    image = tmp_path/'preview.png'; image.write_bytes(b'fixture')
    monkeypatch.setattr(revision, 'authenticate', lambda p: ({}, tmp_path, {}, {}))
    judgment = tmp_path/'review.json'
    judgment.write_text(json.dumps({'schema': 'product-revision-learning-review.v1',
        'report_sha256': revision.school.checksum(report), 'output_png_sha256': revision.school.checksum(image),
        'reviewer': 'assistant_direct_visual_review', 'decision': 'needs_revision', 'notes': 'Still rejected.'}))
    with pytest.raises(ValueError, match='positive before/after'): revision.collect(report, judgment)


def test_request_versions_preserve_original_serialization_and_remove_layout_anchoring(tmp_path, monkeypatch):
    image = tmp_path/'fixture.png'; image.write_bytes(b'fixture image')
    monkeypatch.setattr(revision, 'evidence', lambda *args: ({}, style(), scene(), 'fixture', image, ['Fixture review.']))
    monkeypatch.setattr(revision, 'read', lambda p: {'fixture': 'measured reference'})
    monkeypatch.setattr(revision.product, 'accepted_raw', lambda *args: '{}')
    old, _ = revision.request(tmp_path, tmp_path/'review', 'care', version=1)
    new, _ = revision.request(tmp_path, tmp_path/'review', 'care', version=2)
    assert list(json.loads(old['user'])) == ['brief', 'style', 'independent_comments', 'original_scene', 'supplier_lines', 'product_reference', 'task']
    assert 'original_scene' not in json.loads(new['user'])
    assert json.loads(new['user'])['supplier_lines'] == revision.product.PANELS['care']


def test_prompt_history_survives_changes_to_live_generator(tmp_path, monkeypatch):
    image = tmp_path/'fixture.png'; image.write_bytes(b'fixture image')
    monkeypatch.setattr(revision, 'evidence', lambda *args: ({}, style(), scene(), 'fixture', image, ['Fixture review.']))
    monkeypatch.setattr(revision, 'read', lambda p: {'fixture': 'measured reference'})
    monkeypatch.setattr(revision.product, 'accepted_raw', lambda *args: '{}')
    snapshots = {v: revision.request(tmp_path, tmp_path/'review', 'care', version=v)[0] for v in (1, 2, 3, 4, 5, 6, 7)}
    assert 'visibly at least350 units tall' in snapshots[2]['user']
    assert '120 units wide' not in snapshots[2]['user']
    assert '120 units wide' in snapshots[3]['user']
    assert '50..1450' in snapshots[3]['user']
    assert snapshots[4] == snapshots[3]
    assert 'Leaders must not cross' in snapshots[5]['user']
    assert 'ACTIVE PURPOSE: care instructions only' in snapshots[6]['user']
    assert '20..180' not in snapshots[6]['user']
    monkeypatch.setattr(revision.product, 'SCENE_RULES', 'PANEL: unrelated future contract')
    for v, before in snapshots.items():
        assert revision.request(tmp_path, tmp_path/'review', 'care', version=v)[0] == before
    assert revision.request(tmp_path, tmp_path/'review', 'care')[0] == snapshots[7]


@pytest.mark.parametrize('version', [0, 8, True, 2.0, '2'])
def test_unknown_prompt_versions_cannot_fall_back_to_current(tmp_path, version):
    with pytest.raises(ValueError, match='Known revision request version'):
        revision.request(tmp_path, tmp_path/'review', 'care', version=version)


def test_extended_source_package_requires_versioned_revision_rules(tmp_path, monkeypatch):
    image = tmp_path/'fixture.png'; image.write_bytes(b'fixture')
    monkeypatch.setattr(revision, 'evidence', lambda *args: (
        {'placement_contract': revision.product.PLACEMENT_CONTRACT}, style(), scene(), 'fixture', image, ['Improve scale.']))
    monkeypatch.setattr(revision, 'read', lambda p: {'visible_bbox': [10, 20, 100, 350]})
    prompt, inputs = revision.request(tmp_path, tmp_path/'review', 'care', version=4)
    assert '(.1..4)' in prompt['user'] and '240 units wide' in prompt['user']
    assert inputs[-1] == revision.product.PLACEMENT_CONTRACT
    with pytest.raises(ValueError, match='version 4'):
        revision.request(tmp_path, tmp_path/'review', 'care', version=3)


@pytest.mark.parametrize('tamper', ['prompt', 'answer', 'artwork'])
def test_authentication_rejects_rehashed_conversation_or_artwork_changes(tmp_path, monkeypatch, tamper):
    monkeypatch.setattr(revision, 'ROOT', tmp_path)
    image = tmp_path/'input.png'; image.write_bytes(b'fixture image')
    package = tmp_path/'package'; package.mkdir()
    (package/'report.json').write_text('{}')
    review = tmp_path/'source-review.json'; review.write_text('{}')
    source = revision.product.compile_scene(json.dumps(scene()), style())
    monkeypatch.setattr(revision, 'evidence', lambda *args: ({}, style(), scene(), source, image, ['Fixture review.']))
    monkeypatch.setattr(revision.product, 'quality_issues', lambda *a, **kw: [])
    monkeypatch.setattr(revision, 'pdf_checks', lambda *a, **kw: {})
    out = tmp_path/'revision'; out.mkdir(); folder = out/'attempt-0'; folder.mkdir()
    prompt, inputs = revision.request(package, review, 'cap', version=2)
    prompt['config'] = {}
    answer = {'model': 'fixture', 'digest': 'a'*64, 'content': json.dumps({'cap_shapes': [shape('#222222', 170)]})}
    svg = revision.apply_answer(answer['content'], 'cap', *inputs)
    for name, content in {'request.json': json.dumps(prompt), 'response.json': json.dumps(answer),
                          'artwork.svg': svg, 'preview.png': 'fixture', 'preview.pdf': 'fixture',
                          'render.json': '{}'}.items():
        (folder/name).write_text(content)
    report = {'schema': 'product-visual-revision.v1', 'status': 'pending_independent_review',
              'family': revision.product.BRIEF['family'], 'split': 'train', 'accepted_attempt': 0,
              'package': str(package), 'package_sha256': revision.school.checksum(package/'report.json'),
              'source_review': str(review), 'source_review_sha256': revision.school.checksum(review),
              'part': 'cap', 'request_version': 2, 'config': {}, 'model': 'fixture', 'digest': 'a'*64}
    def save_report():
        report['artifacts'] = {str(p.relative_to(out)): revision.school.checksum(p) for p in folder.iterdir()}
        (out/'report.json').write_text(json.dumps(report))
    save_report()
    assert revision.authenticate(out/'report.json')[3] == answer
    if tamper == 'prompt':
        prompt['user'] += ' changed instruction'
        (folder/'request.json').write_text(json.dumps(prompt))
    elif tamper == 'answer':
        answer['content'] = json.dumps({'cap_shapes': [shape('#222222', 190)]})
        (folder/'response.json').write_text(json.dumps(answer))
    else:
        (folder/'artwork.svg').write_text(svg+'\n')
    save_report()
    with pytest.raises(ValueError, match='differs'):
        revision.authenticate(out/'report.json')
