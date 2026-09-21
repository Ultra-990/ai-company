"""Literal compiler tests use fixtures, never artwork or training examples."""
import json
import xml.etree.ElementTree as ET

import pytest

from scripts import vector_structured_source as scene
from scripts.vector_curriculum import metadata
from scripts.vector_school_contract import NS


def fixture_scene():
    return {'shapes': [{'tag': 'rect', 'attributes': {'x': str(index*10), 'y': '0', 'width': '10', 'height': '10', 'fill': '#123456'}} for index in range(3)],
            'texts': [{'text': 'A & B '+str(index), 'attributes': {'x': '30', 'y': str(40+index*40), 'font-size': '20',
                       'font-family': 'Arial', 'font-weight': '400', 'fill': '#000000'}} for index in range(8)]}


def test_compiler_preserves_every_model_value_without_defaults_or_repairs():
    data = fixture_scene(); source = scene.compile_scene(json.dumps(data)); nodes = list(ET.fromstring(source))
    assert len(nodes) == 11
    for actual, expected in zip(nodes[:3], data['shapes']):
        assert actual.tag == NS+expected['tag'] and actual.attrib == expected['attributes']
    for actual, expected in zip(nodes[3:], data['texts']):
        assert actual.tag == NS+'text' and actual.attrib == expected['attributes'] and actual.text == expected['text']
    assert '&amp;' in source


@pytest.mark.parametrize('change', ['count', 'extra_text_in_shape', 'shape_in_texts', 'unsafe_attribute', 'missing_font', 'missing_geometry', 'numeric_value', 'numeric_syntax', 'numeric_range', 'color_syntax', 'extra_key', 'duplicate_text'])
def test_invalid_scene_is_rejected_instead_of_silently_fixed(change):
    data = fixture_scene()
    if change == 'count': data['texts'].pop()
    elif change == 'extra_text_in_shape': data['shapes'][0] = data['texts'][0]
    elif change == 'shape_in_texts': data['texts'][0] = data['shapes'][0]
    elif change == 'unsafe_attribute': data['texts'][0]['attributes']['onclick'] = 'alert(1)'
    elif change == 'missing_font': data['texts'][0]['attributes'].pop('font-family')
    elif change == 'missing_geometry': data['shapes'][0]['attributes'].pop('width')
    elif change == 'numeric_value': data['texts'][0]['attributes']['x'] = 30
    elif change == 'numeric_syntax': data['texts'][0]['attributes']['x'] = '3e1'
    elif change == 'numeric_range': data['texts'][0]['attributes']['x'] = '9999'
    elif change == 'color_syntax': data['texts'][0]['attributes']['fill'] = 'red'
    elif change == 'extra_key': data['notes'] = 'extra'
    elif change == 'duplicate_text': data['texts'][1]['text'] = data['texts'][0]['text']
    with pytest.raises(ValueError): scene.compile_scene(json.dumps(data))


def reference(tmp_path, monkeypatch):
    monkeypatch.setattr(scene.school, 'ROOT', tmp_path)
    name = 'travel-club-test-v1'; prompt = scene.request(name)
    response = {'model': 'fixture', 'digest': 'a'*64, 'content': json.dumps(fixture_scene())}
    scene.school.save(tmp_path/'request.json', prompt); scene.school.save(tmp_path/'response.json', response)
    (tmp_path/'artwork.svg').write_text(scene.compile_scene(response['content']))
    (tmp_path/'preview.png').write_bytes(b'fixture'); (tmp_path/'preview.pdf').write_bytes(b'fixture')
    scene.school.save(tmp_path/'render.json', {'layout': []})
    report = {'schema': scene.SCHEMA, 'role': 'source', 'status': 'reference_ready', 'compiler': scene.VERSION,
              'model': response['model'], 'digest': response['digest'], **metadata({'curriculum': name}),
              'artifact_sha256': {name: scene.school.checksum(tmp_path/name) for name in
                                  ('request.json', 'response.json', 'artwork.svg', 'preview.png', 'preview.pdf', 'render.json')}}
    scene.school.save(tmp_path/'report.json', report)
    return tmp_path/'report.json', report


def test_structured_source_remains_reserved_and_binds_its_actual_model_scene(tmp_path, monkeypatch):
    path, report = reference(tmp_path, monkeypatch)
    assert scene.school.authenticate(path, report) == {'layout': []}
    with pytest.raises(ValueError, match='Reserved'): scene.school.load_source(path)
    svg = path.parent/'artwork.svg'; svg.write_text(svg.read_text().replace('font-size="20"', 'font-size="21"', 1))
    report['artifact_sha256']['artwork.svg'] = scene.school.checksum(svg)
    with pytest.raises(ValueError, match='literal model'): scene.school.authenticate(path, report)


def test_relabelling_reserved_structured_source_does_not_change_its_frozen_brief(tmp_path, monkeypatch):
    path, report = reference(tmp_path, monkeypatch)
    for key in ('curriculum', 'curriculum_sha256', 'family', 'data_split'): report.pop(key)
    report.update(metadata({'curriculum': 'garden-workshop-train-v1'}))
    scene.school.save(path, report)
    with pytest.raises(ValueError, match='brief changed'): scene.school.load_source(path)


def test_reference_feedback_is_bound_and_cannot_accept_student_answers(tmp_path, monkeypatch):
    path, report = reference(tmp_path, monkeypatch)
    feedback = {'schema': 'vector-scene-reference-feedback.v1', 'source_report': str(path),
                'source_sha256': scene.school.checksum(path),
                'request_sha256': scene.school.checksum(tmp_path/'request.json'),
                'response_sha256': scene.school.checksum(tmp_path/'response.json'),
                'comments': 'Review the readability of your own scene.'}
    prompt = scene.request(report['curriculum'], feedback)
    assert prompt['source_feedback'] == feedback
    assert json.loads((tmp_path/'response.json').read_text())['content'] in prompt['user']
    with pytest.raises(ValueError, match='Reserved'): scene.school.load_source(path)
    with pytest.raises(ValueError, match='three'): scene.request(report['curriculum'], feedback, _depth=3)
    with pytest.raises(ValueError, match='family'): scene.request('garden-workshop-train-v1', feedback)
    report['role'] = 'recreation'; scene.school.save(path, report)
    feedback['source_sha256'] = scene.school.checksum(path)
    with pytest.raises(ValueError, match='Source preparation'): scene.request(report['curriculum'], feedback)
