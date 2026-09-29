import pytest
from scripts import brand_spatial_alignment_review as alignment


@pytest.mark.parametrize('word,center,flag', [('centered', 300, False), ('centred', 300, False), ('centered', 160, True), ('centred', 160, True), ('above', 160, False)])
def test_centering_is_not_inferred_from_above_relation(word, center, flag):
    boxes = {'symbol_bounds': [center-40, 40, center+40, 120], 'wordmark_bounds': [50, 250, 550, 320], 'necessary_conditions': {'above': True}}
    data = {'plan': {'concept_a': 'A '+word+' symbol above the wordmark.', 'concept_b': 'A symbol above the wordmark.'}, 'spatial_measurements': {'a': boxes, 'b': boxes}}
    claims = {'concepts': [{'id': key, 'claims': [{'relation': 'above', 'quote': 'above the wordmark'}]} for key in ('a','b')]}
    raw = {'reviews': [{'index': i, 'verdict': 'supported', 'reason': 'Model accepted the source.'} for i in range(6)]}
    value, findings = alignment.combine(raw, claims, data)
    assert bool(findings) is flag
    assert value['reviews'][4]['verdict'] == ('uncertain' if flag else 'supported')
    assert value['reviews'][5]['verdict'] == 'supported'
