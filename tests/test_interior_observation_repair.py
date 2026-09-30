import io
import json
from hashlib import sha256

from PIL import Image
import pytest

from scripts import interior_observation_repair as repair
from tests.test_interior_school import fixture_plan


def observation():
    return {'description': 'Cream cupboards frame a window above a dark counter.',
        'alt_text': 'Cream cupboards surround a bright window above a dark counter.',
        'visible_details': ['A window above the counter.', 'Cream cupboards beside the window.', 'A dark counter below.'],
        'possible_defects': [], 'brand_fit': 'Cream tones suit a warm country interior.',
        'uncertainty': 'Exact materials cannot be confirmed from this image.', 'recommendation': 'candidate'}


def review(value, flagged=None):
    return {'reviews': [{'field': field, 'verdict': 'unsupported' if field == flagged else 'supported',
        'quote': value[field] if field == flagged else '', 'reason': 'The visible image supports this field.'}
        for field in repair.FIELDS]}


@pytest.fixture
def source(tmp_path, monkeypatch):
    monkeypatch.setattr(repair.school, 'ROOT', tmp_path)
    monkeypatch.setattr(repair.school.media, 'check_idle', lambda: {})
    config = {'model': 'fixture', 'digest': '0'*64}
    monkeypatch.setattr(repair.school, 'configuration', lambda: config)
    plan = fixture_plan()
    original = tmp_path/'plan.json'; repair.school.save(original, {'plan': plan})
    render = {'schema': 'interior-school.v1', 'status': 'rendered', 'own_service_stopped': True,
        'source_report': str(original), 'source_sha256': repair.digest(original), 'plan': plan, 'assets': []}
    report = {'schema': 'interior-school.v1', 'status': 'packaged_pending_independent_review',
        'synthetic': True, 'published': False, 'model': config['model'], 'digest': config['digest'],
        'source_report': str(tmp_path/'render.json'), 'plan': plan, 'inspections': []}
    for asset in repair.school.SHAPES:
        stream = io.BytesIO(); Image.new('RGB', repair.school.SHAPES[asset], 'ivory').save(stream, format='PNG')
        image = stream.getvalue(); image_hash = sha256(image).hexdigest()
        image_path = tmp_path/(asset+'.png'); image_path.write_bytes(image)
        width, height = repair.school.SHAPES[asset]
        render['assets'].append({'id': asset, 'file': image_path.name, 'sha256': image_hash, 'width': width, 'height': height})
        value = observation(); content = json.dumps(value)
        repair.school.save(tmp_path/(asset+'-request.json'), {'config': config, 'image_source': str(image_path), 'image_sha256': image_hash})
        repair.school.save(tmp_path/(asset+'-response.json'), config | {'content': content})
        report['inspections'].append({'id': asset, 'image_source': str(image_path), 'image_sha256': image_hash,
            'response_sha256': sha256(content.encode()).hexdigest(), 'observation': value})
    repair.school.save(tmp_path/'render.json', render)
    report['source_sha256'] = repair.digest(tmp_path/'render.json')
    repair.school.save(tmp_path/'source.json', report)
    return tmp_path/'source.json'


def test_reviewer_requires_complete_unique_fields_and_literal_scoped_quote():
    value = observation(); valid = review(value, 'description')
    assert repair.validate_review(json.dumps(valid), value) == valid
    for mutation in ('duplicate', 'foreign_quote', 'empty_quote', 'missing'):
        changed = json.loads(json.dumps(valid))
        if mutation == 'duplicate': changed['reviews'][1] = changed['reviews'][0]
        if mutation == 'foreign_quote': changed['reviews'][0]['quote'] = value['alt_text']
        if mutation == 'empty_quote': changed['reviews'][0]['quote'] = ''
        if mutation == 'missing': changed['reviews'].pop()
        with pytest.raises(ValueError): repair.validate_review(json.dumps(changed), value)


def test_measured_limits_cannot_be_overruled_by_reviewer():
    value = observation(); value['alt_text'] = ' '.join(['word']*17)
    assert repair.allowed_fields(review(value), value) == ['alt_text']
    assert repair.measurements(value)[0]['observed'] == 17
    value['alt_text'] = ' '.join(['word']*16)
    assert repair.allowed_fields(review(value), value) == []


def test_revision_preserves_unflagged_fields_and_recommendation():
    value = observation(); audit = review(value, 'description')
    revised = value | {'description': 'A window lights the cream cupboards and dark counter.'}
    assert repair.literal_revision(json.dumps(revised), value, audit) == revised
    for field, replacement in (('recommendation', 'reject'), ('visible_details', list(reversed(value['visible_details']))),
                               ('alt_text', 'A different set of cupboards fills this warm bright room.')):
        with pytest.raises(ValueError, match='protected'):
            repair.literal_revision(json.dumps(revised | {field: replacement}), value, audit)


@pytest.mark.parametrize('mutation', ['image', 'response', 'plan', 'test_split'])
def test_authentication_rejects_source_changes(source, mutation):
    parent = source.parent
    if mutation == 'image': (parent/'hero.png').write_bytes(b'changed')
    if mutation == 'response':
        raw = repair.read(parent/'hero-response.json'); raw['content'] = json.dumps(observation() | {'description': 'A changed observation without source provenance.'})
        repair.school.save(parent/'hero-response.json', raw)
    if mutation == 'plan': repair.school.save(parent/'plan.json', {'plan': {}})
    if mutation == 'test_split':
        report = repair.read(source); report.update(curriculum='cottage-reading-eval-v1', data_split='test', family='cottage-reading-room-001')
        repair.school.save(source, report)
    with pytest.raises(ValueError): repair.source(source, 'hero')


@pytest.mark.parametrize('repair_needed,still_bad', [(False, False), (True, False), (True, True)])
def test_real_orchestration_replay_and_bounded_stop(source, monkeypatch, repair_needed, still_bad):
    calls = []
    def complete(config, system, user, image):
        assert image == (source.parent/'hero.png').read_bytes()
        assert 'word word word' not in system+user  # fixture generation prompt is withheld
        data = json.loads(user)
        if 'allowed_fields' in data:
            result = data['observation'] | {'description': 'The bright window sits above a dark counter and cream cupboards.'}
        else:
            fields = data['fields']; result = review(fields, 'description' if repair_needed and (not calls or still_bad) else None)
        calls.append((system, data))
        return {'model': config['model'], 'digest': config['digest'], 'content': json.dumps(result)}
    monkeypatch.setattr(repair.school.local_vision, 'complete', complete)
    out, report = repair.run(source, 'hero')
    assert len(calls) == (3 if repair_needed else 1)
    assert report['status'] == ('needs_revision' if still_bad else 'pending_independent_review')
    assert report['independently_accepted'] is False and report['fresh_exam'] is False
    verified = repair.verify(out)
    assert verified['model_calls'] == len(calls) and verified['independently_accepted'] is False
    before = repair.read(out/'observation.json')
    assert before['alt_text'] == observation()['alt_text']
    # A recomputed artifact manifest cannot authenticate a changed author prompt.
    path = out/'initial-review-request.json'; request = repair.read(path); request['user'] += ' Extra teacher hint.'
    repair.school.save(path, request); report['artifacts'][path.name] = repair.digest(path)
    repair.school.save(out/'report.json', report)
    with pytest.raises(ValueError, match='request'): repair.verify(out)


def test_dry_run_never_calls_model(source, monkeypatch, capsys):
    monkeypatch.setattr('sys.argv', ['interior_observation_repair.py', str(source), '--asset', 'pin'])
    monkeypatch.setattr(repair.school.local_vision, 'complete', lambda *a: pytest.fail('No model in dry run'))
    assert repair.main() == 0
    assert json.loads(capsys.readouterr().out)['model_invoked'] is False


def test_failed_revision_does_not_call_final_reviewer(source, monkeypatch):
    calls = []
    def complete(config, system, user, image):
        calls.append(user)
        result = review(observation(), 'description') if len(calls) == 1 else observation() | {'alt_text': 'Illegally changed preserved alternative text for this image.'}
        return {'model': config['model'], 'digest': config['digest'], 'content': json.dumps(result)}
    monkeypatch.setattr(repair.school.local_vision, 'complete', complete)
    out, report = repair.run(source, 'hero')
    assert len(calls) == 2 and report['status'] == 'failed'
    assert (out/'revision-response.json').is_file()
    with pytest.raises(ValueError, match='Completed'): repair.verify(out)


def test_actual_png_geometry_is_checked_even_when_hashes_are_rebound(source):
    parent = source.parent
    (parent/'hero.png').write_bytes((parent/'pin.png').read_bytes())
    changed_hash = repair.digest(parent/'hero.png')
    rendered = repair.read(parent/'render.json'); rendered['assets'][0]['sha256'] = changed_hash
    repair.school.save(parent/'render.json', rendered)
    report = repair.read(source); report['source_sha256'] = repair.digest(parent/'render.json')
    report['inspections'][0]['image_sha256'] = changed_hash; repair.school.save(source, report)
    request = repair.read(parent/'hero-request.json'); request['image_sha256'] = changed_hash
    repair.school.save(parent/'hero-request.json', request)
    with pytest.raises(ValueError, match='dimensions'): repair.source(source, 'hero')
