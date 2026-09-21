"""Synthetic fixtures test attribution/replay; never supply model training answers."""
from hashlib import sha256
import json
from pathlib import Path

from PIL import Image
import pytest

from scripts import vector_practice as practice
from scripts.vector_curriculum import metadata
from tests.test_vector_school import fixture_svg, layout


def response(before, after):
    return json.dumps({'edits': [{'element': 3, 'attribute': 'font-size', 'before': str(before), 'after': str(after)}]})


def test_fault_plan_is_bounded_and_changes_only_its_assigned_attribute():
    source = fixture_svg(); case = practice.plan(source, 0)
    result = practice.apply_fault(source, response(20, 24), case)
    assert result != source
    with pytest.raises(ValueError): practice.plan(source, 24)
    with pytest.raises(ValueError): practice.plan(source, True)
    with pytest.raises(ValueError): practice.apply_fault(source, response(20, 16), case)
    with pytest.raises(ValueError): practice.apply_fault(source, response(20, 21), case)
    with pytest.raises(ValueError): practice.apply_fault(source, response(20, 24), practice.plan(source, 8))


def test_student_sees_faulty_catalogue_and_measurements_not_fault_response():
    source = fixture_svg(); case = practice.plan(source, 0)
    raw = response(20, 24); faulty = practice.apply_fault(source, raw, case)
    measured = layout(); measured[0]['bbox'][2] = 125
    request = practice.repair_request(faulty, {'layout': layout()}, {'layout': measured}, case, {'path': 'fixture', 'sha256': '0'*64})
    data = json.loads(request['user'])
    assert data['current_catalogue'][3]['attributes']['font-size'] == '24'
    assert data['geometry_errors'][0]['current_minus_reference']['width'] == 25
    assert raw not in request['user'] and source not in request['user']
    assert set(data) == {'task', 'editable_elements', 'editable_attribute', 'geometry_errors', 'current_catalogue', 'units'}


def fixture(tmp_path, monkeypatch, repair='20'):
    monkeypatch.setattr(practice.school, 'ROOT', tmp_path)
    source = fixture_svg().replace('><', '>\n<'); folder = tmp_path/'reference'; folder.mkdir()
    path = folder/'report.json'; path.write_text('{}')
    (folder/'reference-review.json').write_text('{"fixture":true}')
    (folder/'artwork.svg').write_text(source)
    Image.new('RGB', (592, 840), 'white').save(folder/'preview.png')
    family = metadata({'curriculum': 'restaurant-tasting-train-v1'})
    monkeypatch.setattr(practice, 'reference', lambda p: (family, source, {'layout': layout()}))
    monkeypatch.setattr(practice.school, 'check_idle', lambda: {'fixture': True})
    identity = {'model': 'fixture', 'digest': 'd'*64}
    monkeypatch.setattr(practice, 'configuration', lambda: identity)
    outputs = iter([response(20, 24), response(24, repair)])
    monkeypatch.setattr(practice.local_vision, 'complete', lambda *args: {**identity, 'content': next(outputs)})
    async def render(svg, out):
        measured = layout()
        size = float(practice.patch.catalogue(svg)[3]['attributes']['font-size'])
        measured[0]['bbox'][2] = size*5
        Image.new('RGB', (592, 840), 'white').save(out/'preview.png')
        (out/'preview.pdf').write_bytes(b'%PDF-fixture')
        return {'layout': measured}
    monkeypatch.setattr(practice.school, 'render', render)
    monkeypatch.setattr('scripts.render_school_svg.pdf_checks', lambda *args: {'fixture': True})
    out = tmp_path/'case'; out.mkdir()
    result = practice.run_case(path, 0, out)
    return out/'report.json', result


def test_exact_restoration_records_only_the_students_real_response(tmp_path, monkeypatch):
    path, result = fixture(tmp_path, monkeypatch)
    assert result['status'] == 'exact_restoration'
    proof = Path(result['source_report']).parent/'reference-review.json'
    entry = practice.experience(path, proof)
    assert entry['split'] == 'train'
    assert entry['messages'][-1]['content'] == response(24, 20)
    assert entry['review']['reviewer'] == 'exact_replay_of_independently_reviewed_reference'
    assert entry['source']['defect_origin'] == 'deliberate_local_model_perturbation'
    assert entry['commercial_delivery_approved'] is False


def test_exact_practice_enters_existing_candidate_intake_with_honest_attribution(tmp_path, monkeypatch):
    from scripts import vector_learning_records as records
    from scripts.check_vision_training_inputs import verify_bundle
    monkeypatch.setattr('scripts.check_vision_training_inputs.BUNDLE_ROOTS', (tmp_path,))
    path, result = fixture(tmp_path, monkeypatch)
    proof = Path(result['source_report']).parent/'reference-review.json'
    archived = path.parent/'experience.json'
    archived.write_text(json.dumps(practice.experience(path, proof)))
    out = records.export([archived]); rows = verify_bundle(out)
    assert len(rows) == 1 and rows[0]['split'] == 'train'
    assert rows[0]['review']['reviewer'] == 'exact_replay_of_independently_reviewed_reference'
    assert rows[0]['source']['defect_origin'] == 'deliberate_local_model_perturbation'
    assert rows[0]['messages'][-1]['content'] == response(24, 20)


def test_close_but_inexact_model_restoration_is_not_approved(tmp_path, monkeypatch):
    path, result = fixture(tmp_path, monkeypatch, repair='21')
    assert result['comparison']['mechanical_checks_passed'] is True
    assert result['status'] == 'needs_more_learning'
    with pytest.raises(ValueError): practice.verify(path)


def test_historical_authorship_survives_later_model_deployment_change(tmp_path, monkeypatch):
    path, result = fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(practice, 'configuration', lambda: {'model': 'future-version', 'digest': 'f'*64})
    assert practice.verify(path)[0]['model'] == 'fixture'
    result['config']['model'] = 'different-generator'
    path.write_text(json.dumps(result))
    with pytest.raises(ValueError, match='configuration'): practice.verify(path)


@pytest.mark.parametrize('change', ['manual_source', 'line_endings', 'student_prompt', 'teacher_review', 'split'])
def test_rehashing_cannot_replace_exact_model_authorship_or_reference_review(tmp_path, monkeypatch, change):
    path, result = fixture(tmp_path, monkeypatch)
    if change == 'manual_source':
        item = path.parent/'artwork.svg'; item.write_text(item.read_text().replace('font-size="20"', 'font-size="21"', 1))
        result['artifacts']['artwork.svg'] = sha256(item.read_bytes()).hexdigest()
    elif change == 'line_endings':
        item = path.parent/'artwork.svg'; item.write_bytes(item.read_bytes().replace(b'\n', b'\r\n'))
        result['artifacts']['artwork.svg'] = sha256(item.read_bytes()).hexdigest()
    elif change == 'student_prompt':
        item = path.parent/'repair-request.json'; value = json.loads(item.read_text())
        value['user'] += ' teacher replacement'; item.write_text(json.dumps(value))
        result['artifacts'][item.name] = sha256(item.read_bytes()).hexdigest()
    elif change == 'teacher_review':
        (Path(result['source_report']).parent/'reference-review.json').write_text('{"fixture":false}')
    elif change == 'split': result['data_split'] = 'test'
    path.write_text(json.dumps(result))
    with pytest.raises(ValueError): practice.verify(path)
