import json
from copy import deepcopy
import pytest
from scripts import brand_spatial_review as spatial


TEXTS = {'a': 'A wave sits beneath the wordmark.', 'b': 'A circle surrounds the name.'}
CLAIMS = {'concepts': [
    {'id': 'a', 'claims': [{'relation': 'below', 'quote': 'beneath the wordmark'}]},
    {'id': 'b', 'claims': [{'relation': 'surrounds', 'quote': 'surrounds the name'}]},
]}


def measured():
    return spatial.geometry({'layout': [{'bbox': [100, 250, 300, 60]}],
        'shape_layout': [{'bbox': [200, 100, 100, 80]}]})


def test_svg_coordinate_direction_and_failed_surrounding_are_computed():
    result = measured()
    assert result['necessary_conditions']['above']
    assert not any(result['necessary_conditions'][k] for k in ('below', 'surrounds', 'overlaps', 'side_by_side'))
    assert result['symbol_bounds'] == [200, 100, 300, 180]


def test_model_support_cannot_override_measured_contradiction():
    value = {'reviews': [{'index': i, 'verdict': 'supported', 'reason': 'Model claims everything matches.'} for i in range(6)]}
    original = deepcopy(value)
    claims = spatial.claims_value(json.dumps(CLAIMS), TEXTS)
    checked, findings = spatial.combine(value, claims, {'spatial_measurements': {'a': measured(), 'b': measured()}})
    assert value == original
    assert [r['verdict'] for r in checked['reviews']] == ['supported']*4+['unsupported']*2
    assert [f['relation'] for f in findings] == ['below', 'surrounds']
    assert spatial.patch_schema(checked)['properties']['replacements']['items']['properties']['index']['enum'] == [4, 5]


@pytest.mark.parametrize('fault', ['quote', 'duplicate', 'id', 'mixed_unspecified'])
def test_spatial_extraction_is_bound_to_literal_source(fault):
    value = deepcopy(CLAIMS)
    if fault == 'quote': value['concepts'][0]['claims'][0]['quote'] = 'above the wordmark'
    elif fault == 'duplicate': value['concepts'][0]['claims'] *= 2
    elif fault == 'id': value['concepts'][1]['id'] = 'a'
    else: value['concepts'][0]['claims'].append({'relation': 'unspecified', 'quote': ''})
    with pytest.raises(ValueError): spatial.claims_value(json.dumps(value), TEXTS)


@pytest.mark.parametrize('bbox', [[0, 0, -1, 10], [0, 0, float('nan'), 10], [0, 0, True, 10]])
def test_invalid_measurement_cannot_be_used_as_evidence(bbox):
    with pytest.raises(ValueError): spatial.box(bbox)


def test_uncertain_claim_is_not_silently_approved():
    value = {'reviews': [{'index': i, 'verdict': 'supported', 'reason': 'Model claims everything matches.'} for i in range(6)]}
    claims = deepcopy(CLAIMS); claims['concepts'][0]['claims'][0]['relation'] = 'uncertain'
    combined, findings = spatial.combine(value, claims, {'spatial_measurements': {'a': measured(), 'b': measured()}})
    assert combined['reviews'][4]['verdict'] == 'uncertain'
    assert findings[0]['kind'] == 'unresolved_spatial_claim'
