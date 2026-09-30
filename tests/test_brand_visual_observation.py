import json
import pytest
from scripts import brand_visual_observation as observation


@pytest.fixture
def observed(tmp_path, monkeypatch):
    b = observation.b
    monkeypatch.setattr(b, 'ROOT', tmp_path)
    monkeypatch.setattr(b.school, 'check_idle', lambda: {})
    monkeypatch.setattr(b, 'configuration', lambda: {'model': 'fixture', 'digest': 'f'*64})
    monkeypatch.setattr(observation.evidence, 'verify', lambda _: {})
    source = tmp_path/'source'; (source/'delivery').mkdir(parents=True)
    b.school.save(source/'report.json', {'model': 'fixture', 'digest': 'f'*64, 'concept': 'DO NOT SEND THIS DRAFT'})
    for key in ('a', 'b'): (source/'delivery'/('logo-'+key+'.png')).write_bytes(('image-'+key).encode())
    calls = []
    def complete(config, system, user, image):
        assert system == observation.SYSTEM and user == observation.USER
        assert b'DO NOT SEND' not in image
        calls.append(image)
        return {'model': 'fixture', 'digest': 'f'*64, 'content': json.dumps({'observation': 'A small geometric symbol is above the lettering.'})}
    monkeypatch.setattr(observation.local_vision, 'complete', complete)
    out, report = observation.run(source)
    assert calls == [b'image-a', b'image-b']
    assert report['status'] == 'pending_independent_review'
    return out, report


def test_image_observations_are_bound_and_never_self_approve(observed):
    result = observation.verify(observed[0])
    assert result['literal_observation_verified']
    assert result['independent_review_required'] and not result['autonomy_qualified']


@pytest.mark.parametrize('fault', ['image', 'hint', 'output'])
def test_rebinding_does_not_hide_changed_image_prompt_or_output(observed, fault):
    out, report = observed
    name = {'image': 'a.png', 'hint': 'a-request.json', 'output': 'a-response.json'}[fault]
    if fault == 'image': (out/name).write_bytes(b'replacement image')
    else:
        value = observation.evidence.read(out/name)
        if fault == 'hint': value['user'] += ' It is a leaf.'
        else: value['content'] = json.dumps({'observation': 'A newly invented replacement observation.'})
        observation.b.school.save(out/name, value)
    report['artifacts'][name] = observation.b.school.checksum(out/name)
    observation.b.school.save(out/'report.json', report)
    with pytest.raises(ValueError): observation.verify(out)
