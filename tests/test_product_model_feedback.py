import json

import pytest

from scripts import product_model_feedback as feedback


def harness(tmp_path, monkeypatch, answers):
    calls = []
    replies = iter(answers)
    config = {'model': 'fixture', 'digest': 'f'*64, 'num_predict': 4096}
    def text_call(out, stage, system, user, schema, config):
        raw = next(replies)
        calls.append({'user': user, 'image': None})
        feedback.school.save(out/(stage+'-request.json'), {'system': system, 'user': user, 'format': schema})
        feedback.school.save(out/(stage+'-response.json'), {'content': raw})
        return raw
    def vision_call(config, system, user, image):
        assert config['num_predict'] == 2400
        calls.append({'user': user, 'image': image})
        return {'model': 'fixture', 'digest': 'f'*64, 'content': next(replies)}
    monkeypatch.setattr(feedback.brand, 'call', text_call)
    monkeypatch.setattr(feedback.local_vision, 'complete', vision_call)
    monkeypatch.setattr(feedback.school, 'check_idle', lambda: {})
    return calls, config


def failure(tmp_path, raw):
    folder = tmp_path/raw
    folder.mkdir()
    (folder/'preview.png').write_bytes(raw.encode())
    (folder/'artwork.svg').write_text(raw)
    return feedback.SceneFailure('all defects: '+'x'*700+' LAST DEFECT', folder,
                                 {'layout': [{'text': raw, 'bbox': [1, 2, 3, 4]}]})


def test_correction_receives_latest_pixels_full_error_and_exact_raw_answers(tmp_path, monkeypatch):
    calls, config = harness(tmp_path, monkeypatch, ['first', 'second', 'accepted'])
    def validate(raw):
        if raw != 'accepted': raise failure(tmp_path, raw)
        return raw
    assert feedback.validated_call(tmp_path, 'source', 'system', 'brief', {}, config, validate) == 'accepted'
    assert [c['image'] for c in calls] == [None, b'first', b'second']
    assert 'LAST DEFECT' in calls[1]['user']
    assert 'second' in calls[2]['user'] and 'first' not in calls[2]['user']
    assert json.loads((tmp_path/'source-response.json').read_text())['content'] == 'first'
    request = json.loads((tmp_path/'source-revision-2-request.json').read_text())
    assert request['image_sha256'] == feedback.school.checksum(tmp_path/'second/preview.png')
    feedback.verify_attempts(tmp_path, 'source')
    (tmp_path/'second/preview.png').write_bytes(b'changed')
    with pytest.raises(ValueError, match='evidence changed'):
        feedback.verify_attempts(tmp_path, 'source')


def test_syntax_failure_does_not_reuse_stale_preview(tmp_path, monkeypatch):
    calls, config = harness(tmp_path, monkeypatch, ['first', 'invalid', 'accepted'])
    def validate(raw):
        if raw == 'first': raise failure(tmp_path, raw)
        if raw == 'invalid': raise ValueError('invalid syntax')
        return raw
    feedback.validated_call(tmp_path, 'source', 'system', 'brief', {}, config, validate)
    assert [c['image'] for c in calls] == [None, b'first', None]
    feedback.verify_attempts(tmp_path, 'source')


def test_exhausted_corrections_preserve_rejection(tmp_path, monkeypatch):
    calls, config = harness(tmp_path, monkeypatch, ['a', 'b', 'c'])
    def validate(raw): raise failure(tmp_path, raw)
    with pytest.raises(feedback.SceneFailure):
        feedback.validated_call(tmp_path, 'source', 'system', 'brief', {}, config, validate)
    assert len(calls) == 3
    assert (tmp_path/'source-revision-2-feedback.json').exists()


def test_evidence_rejects_symlink_and_external_artwork(tmp_path):
    other = tmp_path/'other'; other.mkdir()
    out = tmp_path/'trial'; out.mkdir()
    with pytest.raises(ValueError, match='belong'):
        feedback.evidence(feedback.SceneFailure('bad', other), out)
    (out/'preview.png').symlink_to(other/'preview.png')
    with pytest.raises(ValueError, match='symlink'):
        feedback.evidence(feedback.SceneFailure('bad', out), out)


def test_feedback_never_silently_truncates_overlong_task():
    with pytest.raises(ValueError, match='Bounded'):
        feedback.correction_user('x'*12000, '{}', {'error': 'bad'})


def test_rehashed_correction_request_cannot_change_conversation(tmp_path, monkeypatch):
    _, config = harness(tmp_path, monkeypatch, ['first', 'accepted'])
    def validate(raw):
        if raw == 'first': raise failure(tmp_path, raw)
        return raw
    feedback.validated_call(tmp_path, 'source', 'system', 'brief', {}, config, validate)
    path = tmp_path/'source-revision-1-request.json'
    request = json.loads(path.read_text()); request['user'] += ' changed'
    feedback.school.save(path, request)
    with pytest.raises(ValueError, match='conversation changed'):
        feedback.verify_attempts(tmp_path, 'source')
