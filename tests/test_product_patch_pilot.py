from pathlib import Path
import json

import pytest

from scripts import product_patch_pilot as pilot


@pytest.mark.parametrize('invalid', [False, True])
def test_bounded_pilot_uses_model_edits_and_preserves_defect_when_patch_is_invalid(tmp_path, monkeypatch, invalid):
    p = pilot.product
    package = tmp_path/'original'; package.mkdir()
    (package/'report.json').write_text('{}'); response = package/'response.json'; response.write_text('{}')
    (package/'product-reference.json').write_text('{}')
    original = {'shapes': [{'tag': 'rect', 'attributes': {'x': '10'}}],
                'texts': [{'text': 'Protected fact', 'attributes': {'y': '40'}}]}
    monkeypatch.setattr(p, 'ROOT', tmp_path)
    monkeypatch.setattr(pilot.revision, 'ROOT', tmp_path)
    monkeypatch.setattr(pilot, 'inputs', lambda path: ({'placement_contract': p.PLACEMENT_CONTRACT}, None, 'capacity', response, original))
    monkeypatch.setattr(p.school, 'check_idle', lambda: {'fixture': True})
    monkeypatch.setattr(p, 'configuration', lambda: {'model': 'fixture', 'digest': 'f'*64})
    monkeypatch.setattr(p, 'accepted_raw', lambda *args: '{}')
    monkeypatch.setattr(p, 'style_value', lambda raw: {})
    monkeypatch.setattr(p, 'compile_scene', lambda *args, **kwargs: '<svg>fixture</svg>')
    def checked(out, *args, **kwargs):
        attempts = []
        def validate(raw):
            folder = out/('repair-layout-'+str(len(attempts))); folder.mkdir(); attempts.append(raw)
            if len(attempts) == 1:
                raise p.feedback.SceneFailure('Original measured collision', folder, {'layout': []})
            return '<svg>fixture</svg>'
        return validate
    monkeypatch.setattr(p, 'checked_scene', checked)
    calls = []
    def call(out, name, system, user, schema, config):
        calls.append(json.loads(user))
        raw = json.dumps({'edits': [{'target': 'texts', 'index': 0, 'attribute': 'text' if invalid else 'y', 'value': '80'}]})
        p.school.save(out/(name+'-request.json'), {'system': system, 'user': user, 'format': schema})
        p.school.save(out/(name+'-response.json'), {'content': raw, 'model': 'fixture', 'digest': 'f'*64})
        return raw
    monkeypatch.setattr(p.brand, 'call', call)
    out, result = pilot.run(package)
    assert original['texts'][0]['attributes']['y'] == '40'
    assert not result['exam_score_changed'] and not result['whole_package_accepted']
    if invalid:
        assert result['status'] == 'failed' and len(calls) == 3
        assert calls[-1]['independent_error'] == 'Original measured collision'
        assert 'previous_patch_rejection' in calls[-1]
        assert not (out/'accepted-scene.json').exists()
    else:
        assert result['status'] == 'pending_independent_review' and len(calls) == 1
        assert result['accepted_layout'] == 'repair-layout-1'
        saved = json.loads((out/'accepted-scene.json').read_text())
        assert saved['texts'][0] == {'text': 'Protected fact', 'attributes': {'y': '80'}}
