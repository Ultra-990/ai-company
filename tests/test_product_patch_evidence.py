import json

import pytest

from scripts import product_patch_evidence as evidence


def pilot_fixture(tmp_path, monkeypatch, *, annotation_contract=None):
    pilot = evidence.pilot; p = pilot.product
    package = tmp_path/'original'; package.mkdir()
    save = p.school.save; checksum = p.school.checksum
    original = {'shapes': [{'tag': 'rect', 'attributes': {'x': '10'}}],
                'texts': [{'text': 'Protected fact', 'attributes': {'y': '40'}}]}
    previous = {'placement_contract': p.PLACEMENT_CONTRACT, 'model': 'fixture', 'digest': 'f'*64}
    save(package/'report.json', previous); save(package/'response.json', {'content': json.dumps(original)})
    save(package/'product-reference.json', {})
    monkeypatch.setattr(p, 'ROOT', tmp_path)
    monkeypatch.setattr(pilot.revision, 'ROOT', tmp_path)
    monkeypatch.setattr(pilot, 'inputs', lambda path: (previous, None, 'capacity', package/'response.json', original))
    monkeypatch.setattr(p.school, 'check_idle', lambda: {})
    monkeypatch.setattr(p, 'configuration', lambda: {'model': 'fixture', 'digest': 'f'*64})
    monkeypatch.setattr(p, 'accepted_raw', lambda *args: '{}')
    monkeypatch.setattr(p, 'style_value', lambda raw: {})
    monkeypatch.setattr(p, 'compile_scene', lambda *args, **kwargs: '<svg>fixture</svg>')
    def checked(out, stage, *args, **kwargs):
        index = 0
        def validate(raw):
            nonlocal index
            folder = out/(stage+'-layout-'+str(index)); folder.mkdir(); index += 1
            if json.loads(raw)['texts'][0]['attributes']['y'] != '80':
                raise p.feedback.SceneFailure('Original measured collision', folder, {'layout': []})
            return '<svg>fixture</svg>'
        return validate
    monkeypatch.setattr(p, 'checked_scene', checked)
    def call(out, name, system, user, schema, config):
        raw = json.dumps({'edits': [{'target': 'texts', 'index': 0, 'attribute': 'y', 'value': '80'}]})
        save(out/(name+'-request.json'), {'system': system, 'user': user, 'format': schema})
        save(out/(name+'-response.json'), {'content': raw, 'model': 'fixture', 'digest': 'f'*64})
        return raw
    monkeypatch.setattr(p.brand, 'call', call)
    return pilot.run(package, annotation_contract=annotation_contract)[0]


@pytest.mark.parametrize('fault', [None, 'extra_hint', 'altered_scene', 'changed_fact', 'extra_call', 'author', 'budget'])
def test_independent_patch_replay_rejects_substitution_even_with_updated_hashes(tmp_path, monkeypatch, fault):
    out = pilot_fixture(tmp_path, monkeypatch)
    p = evidence.product; save = p.school.save; checksum = p.school.checksum
    report = json.loads((out/'report.json').read_text())
    if fault in ('extra_hint', 'extra_call'):
        request = json.loads((out/'patch-0-request.json').read_text())
        request['user'] += ' Extra human coordinates.'
        save(out/('patch-0-request.json' if fault == 'extra_hint' else 'patch-1-request.json'), request)
        report['attempts'][0]['request_sha256'] = checksum(out/'patch-0-request.json')
    elif fault in ('altered_scene', 'changed_fact'):
        name = 'patch-0-after.json' if fault == 'altered_scene' else 'accepted-scene.json'
        value = json.loads((out/name).read_text())
        value['texts'][0]['text'] = 'Changed protected fact'
        save(out/name, value)
    elif fault == 'author':
        value = json.loads((out/'patch-0-response.json').read_text()); value['model'] = 'different'
        save(out/'patch-0-response.json', value)
        report['attempts'][0]['response_sha256'] = checksum(out/'patch-0-response.json')
    elif fault == 'budget': report['config']['num_predict'] = 99999
    report['artifacts'] = {str(p.relative_to(out)): checksum(p) for p in out.rglob('*') if p.is_file() and p.name != 'report.json'}
    save(out/'report.json', report)
    if fault:
        with pytest.raises((ValueError, RuntimeError)): evidence.assess(out)
    else:
        _, result = evidence.assess(out)
        assert result['literal_edits_replayed'] and result['feedback_remeasured']
        assert result['unchanged_facts_paint_and_fonts'] and not result['whole_package_accepted']


@pytest.mark.parametrize('tampered', [False, True])
def test_visible_route_patch_feedback_replays_actual_measurements(tmp_path, monkeypatch, tampered):
    p = evidence.product
    out = pilot_fixture(tmp_path, monkeypatch, annotation_contract=p.callouts.ROUTE_CONTRACT)
    if tampered:
        request_path = out/'patch-0-request.json'
        request = json.loads(request_path.read_text()); data = json.loads(request['user'])
        data['measurements']['panel_line_segments'] = [{'route_product_fills': ['invented paint']}]
        request['user'] = json.dumps(data); p.school.save(request_path, request)
        report = json.loads((out/'report.json').read_text())
        report['artifacts'][request_path.name] = p.school.checksum(request_path)
        report['attempts'][0]['request_sha256'] = p.school.checksum(request_path)
        p.school.save(out/'report.json', report)
        with pytest.raises(ValueError): evidence.assess(out)
    else:
        _, result = evidence.assess(out)
        assert result['literal_edits_replayed'] and result['feedback_remeasured']


@pytest.mark.parametrize('fault', [None, 'negative_review', 'changed_image', 'changed_evidence'])
def test_assembly_requires_bound_independent_geometry_review(tmp_path, monkeypatch, fault):
    out = pilot_fixture(tmp_path, monkeypatch)
    p = evidence.product; save, checksum = p.school.save, p.school.checksum
    report = json.loads((out/'report.json').read_text())
    image = report['accepted_layout']+'/preview.png'
    (out/image).write_bytes(b'synthetic image fixture')
    report['artifacts'][image] = checksum(out/image); save(out/'report.json', report)
    replay, _ = evidence.assess(out)
    judgment = {'schema': 'product-panel-patch-independent-review.v1',
        'reviewer': 'assistant_direct_visual_review', 'decision': 'approved_targeted_panel_repair',
        'report_sha256': checksum(out/'report.json'), 'inspected_images': {image: checksum(out/image)},
        'evidence_report': str(replay/'report.json'), 'evidence_report_sha256': checksum(replay/'report.json'),
        'training_exported': False}
    if fault == 'negative_review': judgment['decision'] = 'needs_visual_revision'
    elif fault == 'changed_image': (out/image).write_bytes(b'another fixture')
    elif fault == 'changed_evidence':
        value = json.loads((replay/'report.json').read_text()); value['feedback_remeasured'] = False
        save(replay/'report.json', value); judgment['evidence_report_sha256'] = checksum(replay/'report.json')
    save(out/'judgment.json', judgment)
    if fault:
        with pytest.raises(ValueError): evidence.approved_panel(out/'report.json', out/'judgment.json')
    else:
        actual, svg = evidence.approved_panel(out/'report.json', out/'judgment.json')
        assert actual['part'] == 'capacity' and svg == out/'accepted.svg'
