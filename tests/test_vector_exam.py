"""Synthetic fixtures exercise exam isolation, never create training records."""
import json
import errno

from PIL import Image
import pytest

from scripts import vector_exam as exam
from scripts import render_school_svg as renderer
from tests.test_vector_school import reserved_reference, fixture_svg, layout


def approved(tmp_path, monkeypatch):
    path, report = reserved_reference(tmp_path, monkeypatch)
    exam.school.save(path.parent/'reference-review.json', {
        'schema': 'vector-evaluation-reference-review.v1', 'source_sha256': exam.school.checksum(path),
        'reviewer': 'assistant_direct_visual_review', 'decision': 'usable_reserved_reference',
        'notes': 'Synthetic fixture approval for infrastructure tests only.'})
    return path


def fixture_exam(tmp_path, monkeypatch):
    path = approved(tmp_path, monkeypatch)
    identity = {'model': 'fixture', 'digest': 'f'*64}
    monkeypatch.setattr(exam.school, 'check_idle', lambda: {'fixture': True})
    monkeypatch.setattr(exam, 'configuration', lambda: identity)
    def generate(config, system, user, image):
        data = json.loads(user); case = data['exercise']
        before = data['catalogue'][case['element']]['attributes'][case['attribute']]
        after = str(int(before)+(8 if case['attribute'] == 'font-size' else 20)*(1 if case['direction'] == 'increase' else -1))
        return identity | {'content': json.dumps({'edits': [{'element': case['element'], 'attribute': case['attribute'], 'before': before, 'after': after}]})}
    monkeypatch.setattr(exam.practice.local_vision, 'complete', generate)
    async def render(source, folder, *, purpose='deliverable'):
        measured = []
        for entry in exam.patch.catalogue(source):
            if entry['tag'] != 'text': continue
            a = entry['attributes']; size = float(a['font-size'])
            measured.append({'text': entry['text'], 'bbox': [float(a['x']), float(a['y'])-20, size*5, 24]})
        Image.new('RGB', (592, 840), 'white').save(folder/'preview.png')
        (folder/'preview.pdf').write_bytes(b'%PDF-fixture')
        return {'layout': measured, 'render_purpose': purpose}
    monkeypatch.setattr(exam, 'render', render)
    out, report = exam.prepare(path)
    return out, report


def test_fault_input_pdf_warning_never_weakens_output_acceptance(monkeypatch):
    def rejected(*args): raise ValueError('PDF page/text export check failed')
    monkeypatch.setattr(renderer, 'pdf_checks', rejected)
    assert renderer.export_assessment(None, [], 'controlled_fault_input')['accepted_as_deliverable'] is False
    with pytest.raises(ValueError): renderer.export_assessment(None, [], 'deliverable')
    with pytest.raises(ValueError): renderer.export_assessment(None, [], 'unknown')


def test_owned_profile_retries_only_its_own_cleanup_race(tmp_path, monkeypatch):
    original = renderer.shutil.rmtree; calls = []
    def racing(path):
        calls.append(path)
        if len(calls) == 1: raise OSError(errno.ENOTEMPTY, 'fixture race')
        original(path)
    monkeypatch.setattr(renderer.shutil, 'rmtree', racing)
    monkeypatch.setattr(renderer.time, 'sleep', lambda _: None)
    with renderer.owned_profile(tmp_path) as path:
        assert str(tmp_path) in path
    assert calls == [path, path]


def test_browser_shutdown_targets_only_the_created_process_group(monkeypatch):
    calls = []
    monkeypatch.setattr(renderer.os, 'killpg', lambda pid, sig: calls.append((pid, sig)))
    class Owned:
        pid = 12345
        def wait(self, timeout): assert timeout == 5
    renderer.stop_owned_chrome(Owned())
    assert calls == [(12345, renderer.signal.SIGTERM), (12345, renderer.signal.SIGKILL)]


def test_reference_requires_reserved_split_and_independent_review(tmp_path, monkeypatch):
    path = approved(tmp_path, monkeypatch)
    assert exam.reference(path)[1] == fixture_svg()
    with pytest.raises(ValueError, match='Reserved'): exam.school.load_source(path)
    review = exam.practice.read(path.parent/'reference-review.json'); review['decision'] = 'model_self_approval'
    exam.school.save(path.parent/'reference-review.json', review)
    with pytest.raises(ValueError, match='Independent'): exam.reference(path)


def test_prepared_exam_freezes_24_repairs_and_separate_whole_recreation(tmp_path, monkeypatch):
    out, report = fixture_exam(tmp_path, monkeypatch)
    assert report['status'] == 'frozen' and len(report['cases']) == 25
    assert exam.load_exam(out/'report.json')[0] == report
    for entry in report['cases']:
        prompt = exam.practice.read(out/f"case-{entry['id']:02d}"/'request.json')
        assert fixture_svg() not in prompt['user']
    assert report['cases'][-1]['kind'] == 'whole_recreation'
    assert not report['training_exported'] and not report['training_started']


def test_invalid_preparation_cannot_drop_a_case_or_start_candidate_evaluation(tmp_path, monkeypatch):
    path = approved(tmp_path, monkeypatch)
    monkeypatch.setattr(exam.school, 'check_idle', lambda: {'fixture': True})
    monkeypatch.setattr(exam, 'configuration', lambda: {'model': 'fixture', 'digest': 'f'*64})
    calls = []
    def invalid(*args):
        calls.append(True)
        return {'model': 'fixture', 'digest': 'f'*64, 'content': '{"edits":[]}'}
    monkeypatch.setattr(exam.practice.local_vision, 'complete', invalid)
    out, report = exam.prepare(path)
    assert report['status'] == 'preparation_failed' and len(report['cases']) == 1
    with pytest.raises(ValueError, match='Complete frozen'): exam.evaluate(out/'report.json')
    assert len(calls) == 1


def test_reserved_exam_reports_cannot_enter_learning_collector(tmp_path, monkeypatch):
    from scripts.vector_learning_records import approved_experience
    monkeypatch.setattr(exam.school, 'ROOT', tmp_path)
    for schema in (exam.SCHEMA, 'vector-exam-answer.v1'):
        path = tmp_path/'report.json'; exam.school.save(path, {'schema': schema, 'data_split': 'train'})
        with pytest.raises(ValueError, match='Unknown reviewed'):
            approved_experience(path, tmp_path/'review.json')


@pytest.mark.parametrize('change', ['prompt', 'fault', 'author', 'missing_case', 'missing_whole', 'review'])
def test_rehashing_cannot_change_exam_inputs_or_authorship(tmp_path, monkeypatch, change):
    out, report = fixture_exam(tmp_path, monkeypatch); folder = out/'case-00'; entry = report['cases'][0]
    if change == 'prompt':
        p = folder/'request.json'; data = exam.practice.read(p); data['user'] += 'Answer is 20.'; exam.school.save(p, data)
        entry['artifacts'][p.name] = exam.school.checksum(p)
    elif change == 'fault':
        p = folder/'faulty.svg'; p.write_bytes(p.read_bytes()+b'\n'); entry['artifacts'][p.name] = exam.school.checksum(p)
    elif change == 'author':
        p = folder/'fault-response.json'; data = exam.practice.read(p); data['model'] = 'other'; exam.school.save(p, data)
        entry['artifacts'][p.name] = exam.school.checksum(p)
    elif change == 'missing_case': report['cases'].pop(2)
    elif change == 'missing_whole': report['cases'][-1]['kind'] = 'attribute_restoration'
    elif change == 'review':
        p = exam.school.ROOT/'reference'/'reference-review.json'; data = exam.practice.read(p); data['decision'] = 'rejected_reference'; exam.school.save(p, data)
        report['reference_review_sha256'] = exam.school.checksum(p)
    exam.school.save(out/'report.json', report)
    with pytest.raises(ValueError): exam.load_exam(out/'report.json')


@pytest.mark.parametrize('interrupt', [False, True])
def test_evaluation_uses_frozen_requests_and_reports_each_skill(tmp_path, monkeypatch, interrupt):
    out, report = fixture_exam(tmp_path, monkeypatch)
    calls = []
    def answer(config, system, user, image):
        calls.append(user)
        if user == exam.RECREATE_BRIEF: raw = json.dumps({'svg': fixture_svg()})
        else:
            data = json.loads(user); element = data['editable_elements'][0]; attr = data['editable_attribute']
            before = data['current_catalogue'][element]['attributes'][attr]
            after = exam.patch.catalogue(fixture_svg())[element]['attributes'][attr]
            raw = json.dumps({'edits': [{'element': element, 'attribute': attr, 'before': before, 'after': after}]})
        return {'model': config['model'], 'digest': config['digest'], 'content': raw}
    monkeypatch.setattr(exam.practice.local_vision, 'complete', answer)
    monkeypatch.setattr(exam, 'pdf_checks', lambda *args: {'fixture': True})
    if interrupt:
        original = exam.score
        def fail_after_capture(*args): raise OSError(errno.ENOTEMPTY, 'fixture profile cleanup failure')
        monkeypatch.setattr(exam, 'score', fail_after_capture)
    answers, results = exam.evaluate(out/'report.json')
    if interrupt:
        assert results['status'] == 'interrupted' and len(calls) == 1
        captured = exam.school.checksum(answers/'case-00'/'answer-response.json')
        monkeypatch.setattr(exam, 'score', original)
        answers, results = exam.evaluate(out/'report.json', resume=answers/'report.json')
        assert results['results'][0]['reused_captured_response'] is True
        assert exam.school.checksum(answers/'case-00'/'answer-response.json') == captured
        assert (answers/'interruption-001'/'case-00'/'answer-response.json').exists()
    assert len(calls) == 25
    assert results['status'] == 'completed'
    assert results['totals'] == {'attribute_restoration': {'passed': 24, 'answered': 24}, 'whole_recreation': {'passed': 1, 'answered': 1}}
    assert not results['service_readiness_proven'] and not results['training_exported']
    assert all(exam.practice.read(answers/f"case-{case['id']:02d}"/'render.json')['render_purpose'] == 'deliverable' for case in report['cases'])
    assert exam.verify_answers(answers/'report.json')['totals'] == results['totals']
    p = answers/'case-00'/'artwork.svg'; p.write_bytes(p.read_bytes()+b'\n')
    results['results'][0]['artifacts']['artwork.svg'] = exam.school.checksum(p)
    exam.school.save(answers/'report.json', results)
    with pytest.raises(ValueError, match='artwork changed'): exam.verify_answers(answers/'report.json')
