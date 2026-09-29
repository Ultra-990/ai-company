from copy import deepcopy
import json
import pytest

from scripts import brand_guide_revision as guide


def verdict(flagged=(2,)):
    return {'reviews': [{'index': i, 'verdict': 'unsupported' if i in flagged else 'supported',
                         'reason': 'A specific fixture finding.'} for i in range(4)]}


PLAN = {'positioning': 'Fixture neighborhood restaurant.', 'tagline': 'Public test brand',
    'ink': '#111111', 'paper': '#FFFFFF', 'accent': '#225588', 'heading_font': 'Arial',
    'body_font': 'Georgia', 'monochrome_ink': '#111111',
    'guidelines': ['Use the ink color for text.', 'Use Arial for all headings.',
                   'Every size is guaranteed readable.', 'Use dark ink on a light field.']}
PATCH = {'replacements': [{'index': 2, 'text': 'Leave one letter height of clear space around the full logo.'}]}


def test_literal_patch_preserves_all_unflagged_fields_and_original():
    original = deepcopy(PLAN)
    changed = guide.apply(original, json.dumps(PATCH), verdict())
    assert original == PLAN
    assert changed['guidelines'][2] == PATCH['replacements'][0]['text']
    changed['guidelines'][2] = original['guidelines'][2]
    assert changed == original


@pytest.mark.parametrize('patch', [
    {'replacements': []}, {'replacements': PATCH['replacements']*2},
    {'replacements': [{'index': 1, 'text': 'A changed unflagged typography rule.'}]},
    {'replacements': [{'index': 2, 'text': PLAN['guidelines'][2]}]},
    {'replacements': [{'index': 2, 'text': 'too short'}]},
    {'replacements': [{'index': 2, 'text': 'x'*351}]},
    {'replacements': [{'index': True, 'text': 'Invalid index should be refused.'}]},
    PATCH | {'ink': '#FF0000'},
])
def test_patch_cannot_change_protected_or_invented_fields(patch):
    with pytest.raises(ValueError): guide.apply(PLAN, json.dumps(patch), verdict())


@pytest.mark.parametrize('fault', ['duplicate', 'missing', 'verdict', 'bool', 'reason'])
def test_review_requires_four_distinct_bounded_findings(fault):
    value = verdict()
    if fault == 'duplicate': value['reviews'][1]['index'] = 0
    elif fault == 'missing': value['reviews'].pop()
    elif fault == 'verdict': value['reviews'][0]['verdict'] = 'passed'
    elif fault == 'bool': value['reviews'][0]['index'] = False
    else: value['reviews'][0]['reason'] = ''
    with pytest.raises(ValueError): guide.review_value(json.dumps(value))


@pytest.fixture
def revised(tmp_path, monkeypatch, request):
    brand = guide.brand; monkeypatch.setattr(brand, 'ROOT', tmp_path)
    source = tmp_path/'source'; delivery = source/'delivery'; delivery.mkdir(parents=True)
    original = {'model': 'fixture', 'digest': 'f'*64, 'selection': {'selected': 'a', 'reason': 'Model choice.'}}
    brand.school.save(source/'report.json', original)
    data = {'restaurant': 'Fixture', 'plan': deepcopy(PLAN)}
    expanded = getattr(request, 'param', False)
    spatial = expanded in ('spatial', 'subject')
    if expanded:
        data['plan'].update(concept_a='A false original concept description.', concept_b='A preserved second concept description.')
    if spatial:
        from scripts import brand_spatial_review as measured
        if expanded == 'subject': from scripts import brand_spatial_subject_review as measured
        data['plan'].update(concept_a='A wave sits below the wordmark.', concept_b='A circle surrounds the wordmark.')
        from scripts.brand_spatial_review import geometry as measure
        geometry = measure({'layout': [{'bbox': [100, 250, 300, 60]}], 'shape_layout': [{'bbox': [200, 100, 100, 80]}]})
        if expanded == 'subject': geometry['necessary_conditions']['inside'] = False
        monkeypatch.setattr(measured, 'expand', lambda data, p: data | {'spatial_measurements': {'a': geometry, 'b': geometry}})
        monkeypatch.setattr(measured, 'remeasure', lambda p, data: {'fixture_only': True})
    brand.school.save(delivery/'style-plan.json', PLAN)
    (delivery/'brand-guide.md').write_text(guide.guide_text('Fixture', PLAN, original['selection']))
    (delivery/'logo.svg').write_text('<svg>protected fixture</svg>')
    brand.school.save(delivery/'manifest.json', {'model': 'fixture', 'digest': 'f'*64,
        'files': {p.name: brand.school.checksum(p) for p in delivery.iterdir()}})
    monkeypatch.setattr(guide, 'inputs', lambda p: (original, deepcopy(data)))
    monkeypatch.setattr(brand, 'configuration', lambda: {'model': 'fixture', 'digest': 'f'*64})
    monkeypatch.setattr(brand.school, 'check_idle', lambda: {})
    first, patch, final = verdict(), deepcopy(PATCH), verdict(())
    if expanded:
        for value in (first, final):
            value['reviews'].extend([{'index': i, 'verdict': 'supported', 'reason': 'A matching concept description.'} for i in (4, 5)])
        first['reviews'][4]['verdict'] = 'unsupported'
        patch['replacements'].append({'index': 4, 'text': 'A corrected description from the local model.'})
    answers = iter([first, patch, final])
    if spatial:
        first['reviews'][4]['verdict'] = 'supported'
        patch['replacements'][-1]['text'] = 'A wave sits above the wordmark.'
        patch['replacements'].append({'index': 5, 'text': 'A circle sits above the wordmark.'})
        def claims(phase):
            return {'concepts': [{'id': key, 'claims': [{'relation': relation, 'quote': quote}]} for key, relation, quote in phase]}
        before = claims([('a', 'below', 'below the wordmark'), ('b', 'surrounds', 'surrounds the wordmark')])
        after = claims([('a', 'above', 'above the wordmark'), ('b', 'above', 'above the wordmark')])
        if expanded == 'subject':
            for value in (before, after):
                for row in value['concepts']:
                    noun = 'wave' if row['id'] == 'a' else 'circle'
                    for c in row['claims']:
                        c.update(subject='symbol', subject_quote=noun, quote='A '+noun+' '+('surrounds the wordmark.' if c['relation'] == 'surrounds' else 'sits '+c['relation']+' the wordmark.'))
        answers = iter([first, before, patch, final, after])
    class Provider:
        def __init__(self, config): pass
        def complete(self, messages):
            assert 'independent-review' not in json.dumps(messages)
            return {'content': json.dumps(next(answers)), 'model': 'fixture', 'digest': 'f'*64}
    monkeypatch.setattr(brand, 'OllamaProvider', Provider)
    out, report = guide.run(source, expanded=bool(expanded), spatial='subject' if expanded == 'subject' else spatial)
    assert report['status'] == 'pending_independent_review'
    return out, report


def test_complete_revision_replays_three_model_calls_and_protects_artwork(revised):
    result = guide.verify(revised[0])
    assert result['literal_authorship_verified'] and result['protected_artwork_unchanged']
    assert not result['autonomy_qualified'] and not result['exam_score_changed']


@pytest.mark.parametrize('revised', [True], indirect=True)
def test_expanded_revision_replays_structure_and_changed_concept(revised):
    out, report = revised
    assert report['review_contract'] == 'brand-plan-factual-review.v2'
    result = guide.verify(out)
    assert result['literal_authorship_verified'] and result['protected_artwork_unchanged']
    assert json.loads((out/'revised-plan.json').read_text())['concept_a'] == 'A corrected description from the local model.'


@pytest.mark.parametrize('revised', ['spatial', 'subject'], indirect=True)
def test_spatial_revision_overrides_false_model_approval_and_replays_five_calls(revised):
    out, report = revised
    assert report['max_model_calls'] == 5
    raw = json.loads((out/'raw-review.json').read_text())
    combined = json.loads((out/'review.json').read_text())
    assert raw['reviews'][4]['verdict'] == 'supported'
    assert combined['reviews'][4]['verdict'] == 'unsupported'
    result = guide.verify(out)
    assert result['independent_spatial_render'] == {'fixture_only': True}
    assert result['protected_artwork_unchanged']


@pytest.mark.parametrize('fault', ['artwork', 'guide', 'author', 'hint', 'extra', 'qualify'])
def test_rebound_tampering_is_rejected(revised, fault):
    out, report = revised
    if fault == 'artwork': (out/'delivery/logo.svg').write_text('<svg>teacher replacement</svg>')
    elif fault == 'guide': (out/'delivery/brand-guide.md').write_text('Teacher substitute guide')
    elif fault == 'qualify': report['autonomy_qualified'] = True
    else:
        name = 'writer-response.json' if fault == 'author' else 'writer-request.json'
        value = json.loads((out/name).read_text())
        if fault == 'author': value['model'] = 'another author'
        elif fault == 'hint': value['user'] += 'Extra teacher wording.'
        else: name = 'extra-request.json'
        guide.brand.school.save(out/name, value)
    report['artifacts'] = {str(p.relative_to(out)): guide.brand.school.checksum(p)
        for p in out.rglob('*') if p.is_file() and p.name != 'report.json'}
    guide.brand.school.save(out/'report.json', report)
    with pytest.raises(ValueError): guide.verify(out)
