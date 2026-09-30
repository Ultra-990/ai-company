from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts import brand_composed_review as review
from scripts import brand_reference_review as legacy
from scripts import brand_spatial_subject_review as subjects
from scripts.brand_spatial_review import geometry


def claim(subject, noun, relation, text, reference='bounds', reference_quote=''):
    return {'subject': subject, 'subject_quote': noun, 'relation': relation,
        'quote': text, 'reference': reference, 'reference_quote': reference_quote}


def pair(first, second=None):
    second = second or first
    return {'concepts': [{'id': key, 'claims': [deepcopy(c)],
        'wordmark_lines': {'relation': 'unspecified', 'quote': ''}} for key, c in [('a', first), ('b', second)]]}


def inputs(raw, text_box=(100, 200, 200, 50), symbol_box=(120, 100, 80, 50)):
    texts = {row['id']: row['claims'][0]['quote'] for row in raw['concepts']}
    measured = geometry({'layout': [{'bbox': list(text_box)}], 'shape_layout': [{'bbox': list(symbol_box)}]})
    l, t, r, b = measured['symbol_bounds']; x, y, u, v = measured['wordmark_bounds']
    measured['necessary_conditions']['inside'] = l >= x and t >= y and r <= u and b <= v
    data = {'plan': {'concept_a': texts['a'], 'concept_b': texts['b'], 'monochrome_ink': '#111111', 'guidelines': []},
        'spatial_measurements': {key: deepcopy(measured) for key in texts},
        'wordmark_line_counts': {'a': 1, 'b': 1}}
    verdicts = {'reviews': [{'index': i, 'verdict': 'supported', 'reason': 'The local model agrees.'} for i in range(6)]}
    return texts, data, verdicts


def test_inverse_grammatical_forms_have_the_same_measured_result():
    raw = pair(claim('wordmark', 'wordmark', 'below', 'The wordmark sits below the ring.'),
               claim('symbol', 'ring', 'above', 'The ring sits above the wordmark.'))
    texts, data, verdicts = inputs(raw)
    parsed = review.claims_value(json.dumps(raw), texts)
    assert [x['claims'][0]['relation'] for x in parsed['concepts']] == ['above', 'above']
    assert review.combine(verdicts, parsed, data) == (verdicts, [])
    data['spatial_measurements']['a']['necessary_conditions']['above'] = False
    result, findings = review.combine(verdicts, parsed, data)
    assert result['reviews'][4]['verdict'] == 'unsupported'
    assert len(findings) == 1


def test_wordmark_left_and_center_reference_are_inverted_once():
    raw = pair(claim('wordmark', 'name', 'left', 'The name lies left of the bowl.'))
    texts, data, verdicts = inputs(raw, text_box=(100, 200, 200, 50), symbol_box=(340, 190, 50, 60))
    parsed = review.claims_value(json.dumps(raw), texts)
    assert review.combine(verdicts, parsed, data) == (verdicts, [])
    raw = pair(claim('wordmark', 'name', 'left', 'The name lies left of the bowl center.', 'centers', 'bowl center'))
    texts, data, verdicts = inputs(raw, text_box=(100, 200, 200, 50), symbol_box=(230, 190, 50, 60))
    parsed = review.claims_value(json.dumps(raw), texts)
    assert parsed['concepts'][0]['claims'][0]['relation'] == 'right'
    assert review.combine(verdicts, parsed, data) == (verdicts, [])
    for row in raw['concepts']:
        row['claims'][0].update(reference='bounds', reference_quote='')
    _, findings = review.combine(verdicts, review.claims_value(json.dumps(raw), texts), data)
    assert len(findings) == 2  # Center ordering does not prove separated bounds.


def test_inside_surrounds_and_line_count_survive_composition():
    raw = pair(claim('wordmark', 'wordmark', 'inside', 'The wordmark sits inside the ring.'))
    texts, data, verdicts = inputs(raw, symbol_box=(80, 180, 250, 90))
    parsed = review.claims_value(json.dumps(raw), texts)
    assert parsed['concepts'][0]['claims'][0]['relation'] == 'surrounds'
    assert review.combine(verdicts, parsed, data) == (verdicts, [])
    raw = pair(claim('symbol', 'ring', 'inside', 'The ring sits inside the wordmark.'))
    texts, data, verdicts = inputs(raw, symbol_box=(150, 215, 10, 10))
    parsed = review.claims_value(json.dumps(raw), texts)
    assert review.combine(verdicts, parsed, data) == (verdicts, [])
    for row in raw['concepts']:
        texts[row['id']] += ' The name uses a single line.'
        row['wordmark_lines'] = {'relation': 'single', 'quote': 'single line'}
    data['wordmark_line_counts']['a'] = 2
    _, findings = review.combine(verdicts, review.claims_value(json.dumps(raw), texts), data)
    assert any(x['kind'] == 'wordmark_line_count_contradiction' for x in findings)


@pytest.mark.parametrize('fault', ['role', 'direction', 'noun', 'reference', 'line', 'extra', 'duplicate'])
def test_rebound_claims_cannot_hide_role_reference_or_line_errors(fault):
    raw = pair(claim('wordmark', 'wordmark', 'below', 'The wordmark sits below the ring.'))
    texts, _, _ = inputs(raw)
    c = raw['concepts'][0]['claims'][0]
    if fault == 'role': c['subject'] = 'symbol'
    elif fault == 'direction': c['relation'] = 'above'
    elif fault == 'noun': c['subject_quote'] = 'invented subject'
    elif fault == 'reference': c.update(reference='centers', reference_quote='made up center')
    elif fault == 'line': raw['concepts'][0]['wordmark_lines'] = {'relation': 'multiple', 'quote': 'invented stacking'}
    elif fault == 'extra': c['hint'] = 'accept'
    else: raw['concepts'][0]['claims'].append(deepcopy(c))
    with pytest.raises(ValueError): review.claims_value(json.dumps(raw), texts)


@pytest.mark.parametrize('value', [None, [], {}, {'concepts': [None]}, {'concepts': [{'claims': None}]}])
def test_malformed_data_fails_closed(value):
    with pytest.raises(ValueError): review.claims_value(json.dumps(value), {})


def test_prescription_prompt_is_explicit_without_changing_legacy():
    # This checks the model's input contract, not semantic model competence.
    assert 'untested numerical print minima' in legacy.REVIEW_SYSTEM
    assert 'untested numerical print minima' not in review.REVIEW_SYSTEM
    for text in ('Do not use the full logo below 22 mm', 'Tested and readable at 22 mm',
                 'absence of a render at that size alone does not refute',
                 'missing variants', 'removing the symbol', 'print readiness'):
        assert text in review.REVIEW_SYSTEM
    assert review.CLAIM_SYSTEM.startswith(subjects.CLAIM_SYSTEM)
    assert 'subject' not in legacy.CLAIM_SCHEMA['properties']['concepts']['items']['properties']['claims']['items']['properties']
    assert len(review.REVIEW_SYSTEM) < 12000 and len(review.CLAIM_SYSTEM) < 12000


def test_expansion_preserves_all_layers_and_reuses_subject_remeasure(monkeypatch):
    monkeypatch.setattr(review.previous, 'expand', lambda data, package: data | {'measured_centers': 'kept', 'wordmark_line_counts': 'kept', 'background_evidence': 'kept'})
    monkeypatch.setattr(review.subjects, 'expand', lambda data, package: data | {'inside': 'added'})
    result = review.expand({'plan': {}}, None)
    assert result == {'plan': {}, 'measured_centers': 'kept', 'wordmark_line_counts': 'kept', 'background_evidence': 'kept', 'inside': 'added', 'review_contract': review.CONTRACT}
    assert review.remeasure is subjects.remeasure


def test_composed_cli_is_explicit_and_keeps_reference_option():
    process = subprocess.run([sys.executable, 'scripts/brand_school.py', '--help'],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=10)
    assert process.returncode == 0
    assert '--revise-composed-text' in process.stdout and '--revise-reference-text' in process.stdout
