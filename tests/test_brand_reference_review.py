import json
import pytest
from scripts import brand_reference_review as review
from scripts.brand_spatial_review import geometry


def example(reference='centers', relation='left'):
    text = 'The symbol sits '+relation+' of the wordmark center.'
    claims = {'concepts': [{'id': key, 'wordmark_lines': {'relation': 'single', 'quote': 'single line'},
        'claims': [{'relation': relation, 'quote': text, 'reference': reference,
            'reference_quote': 'wordmark center' if reference == 'centers' else ''}]} for key in ('a', 'b')]}
    texts = {key: text+' The name is a single line.' for key in ('a', 'b')}
    # Symbol is left of the text center, but overlaps its horizontal extent.
    measured = geometry({'layout': [{'bbox': [130, 200, 340, 50]}],
        'shape_layout': [{'bbox': [124, 160, 32, 26]}]})
    data = {'plan': {'concept_a': texts['a'], 'concept_b': texts['b'],
        'monochrome_ink': '#111111', 'guidelines': []},
        'spatial_measurements': {key: measured for key in texts},
        'wordmark_line_counts': {'a': 1, 'b': 1}}
    verdicts = {'reviews': [{'index': i, 'verdict': 'supported', 'reason': 'The local model agrees.'} for i in range(6)]}
    return claims, texts, data, verdicts


def test_explicit_center_reference_does_not_require_whole_bounds_separation():
    claims, texts, data, verdicts = example()
    parsed = review.claims_value(json.dumps(claims), texts)
    result, findings = review.combine(verdicts, parsed, data)
    assert not findings and result == verdicts
    assert claims == parsed
    bounds, texts, data, verdicts = example('bounds')
    result, findings = review.combine(verdicts, review.claims_value(json.dumps(bounds), texts), data)
    assert len(findings) == 2
    assert result['reviews'][4]['verdict'] == 'unsupported'


def test_wrong_direction_still_fails_and_line_count_guard_survives():
    claims, texts, data, verdicts = example(relation='right')
    parsed = review.claims_value(json.dumps(claims), texts)
    result, findings = review.combine(verdicts, parsed, data)
    assert len(findings) == 2
    assert all(f['kind'] == 'measured_center_reference_contradiction' for f in findings)
    assert findings[0]['symbol_minus_wordmark_center'] == [-160, -52]
    data['wordmark_line_counts']['a'] = 2
    _, findings = review.combine(verdicts, parsed, data)
    assert any(f['kind'] == 'wordmark_line_count_contradiction' for f in findings)


@pytest.mark.parametrize('fault', ['invented_quote', 'empty_quote', 'missing_reference', 'invalid_relation', 'extra_field'])
def test_reference_must_have_literal_and_directional_evidence(fault):
    claims, texts, _, _ = example()
    c = claims['concepts'][0]['claims'][0]
    if fault == 'invented_quote': c['reference_quote'] = 'made up center'
    elif fault == 'empty_quote': c['reference_quote'] = ''
    elif fault == 'missing_reference': del c['reference']
    elif fault == 'invalid_relation': c['relation'] = 'overlaps'
    else: c['extra'] = 'hint'
    with pytest.raises(ValueError): review.claims_value(json.dumps(claims), texts)


def test_explicit_centers_come_from_measurements_not_the_plan(monkeypatch):
    _, _, data, _ = example()
    monkeypatch.setattr(review.previous, 'expand', lambda *args: data)
    result = review.expand({}, None)
    assert result['measured_centers']['a']['symbol'] == [140, 173]
    assert result['measured_centers']['a']['wordmark'] == [300, 225]
    assert result['measured_centers']['a']['symbol_minus_wordmark'] == [-160, -52]


@pytest.mark.parametrize('value', [None, [], {}, {'concepts': [None]}, {'concepts': [{'claims': None}]}])
def test_malformed_references_fail_as_validation_errors(value):
    with pytest.raises(ValueError): review.claims_value(json.dumps(value), {})
