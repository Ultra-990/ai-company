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
def revised(tmp_path, monkeypatch):
    brand = guide.brand; monkeypatch.setattr(brand, 'ROOT', tmp_path)
    source = tmp_path/'source'; delivery = source/'delivery'; delivery.mkdir(parents=True)
    original = {'model': 'fixture', 'digest': 'f'*64, 'selection': {'selected': 'a', 'reason': 'Model choice.'}}
    brand.school.save(source/'report.json', original)
    data = {'restaurant': 'Fixture', 'plan': deepcopy(PLAN)}
    brand.school.save(delivery/'style-plan.json', PLAN)
    (delivery/'brand-guide.md').write_text(guide.guide_text('Fixture', PLAN, original['selection']))
    (delivery/'logo.svg').write_text('<svg>protected fixture</svg>')
    brand.school.save(delivery/'manifest.json', {'model': 'fixture', 'digest': 'f'*64,
        'files': {p.name: brand.school.checksum(p) for p in delivery.iterdir()}})
    monkeypatch.setattr(guide, 'inputs', lambda p: (original, deepcopy(data)))
    monkeypatch.setattr(brand, 'configuration', lambda: {'model': 'fixture', 'digest': 'f'*64})
    monkeypatch.setattr(brand.school, 'check_idle', lambda: {})
    answers = iter([verdict(), PATCH, verdict(())])
    class Provider:
        def __init__(self, config): pass
        def complete(self, messages):
            assert 'independent-review' not in json.dumps(messages)
            return {'content': json.dumps(next(answers)), 'model': 'fixture', 'digest': 'f'*64}
    monkeypatch.setattr(brand, 'OllamaProvider', Provider)
    out, report = guide.run(source)
    assert report['status'] == 'pending_independent_review'
    return out, report


def test_complete_revision_replays_three_model_calls_and_protects_artwork(revised):
    result = guide.verify(revised[0])
    assert result['literal_authorship_verified'] and result['protected_artwork_unchanged']
    assert not result['autonomy_qualified'] and not result['exam_score_changed']


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
