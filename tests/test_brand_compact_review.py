from copy import deepcopy
import json

from jsonschema import Draft202012Validator
import pytest
from app.services.local_ollama import output_format
from scripts import brand_compact_review as compact
from scripts import brand_literal_review as literal
from tests.test_brand_literal_review import TEXTS, answer


def encode(value, payload):
    """Fixture only: select catalogue entries matching a known literal answer."""
    result = {'concepts': []}
    for row in value['concepts']:
        key = row['id']; originals = literal.literal_claims(payload[key]['text'])
        identifiers = [payload[key]['options'][originals.index(claim)]['id'] for claim in row['claims']]
        result['concepts'].append({'id': key, 'claim_ids': identifiers,
                                   'wordmark_lines': row['wordmark_lines']['relation']})
    return result


def test_compact_choice_decodes_exact_v11_and_preserves_inverse_direction():
    payload = compact.catalogue(TEXTS); value = encode(answer(), payload)
    decoded, texts = compact.decode(json.dumps(value), payload)
    assert decoded == answer() and texts == TEXTS
    expected = literal.claims_value(json.dumps(answer()), TEXTS)
    assert compact.claims_value(json.dumps(value), payload) == expected
    assert expected['concepts'][0]['claims'][0]['relation'] == 'above'
    assert expected['concepts'][1]['claims'][0]['relation'] == 'right'


def test_schema_fits_real_adapter_for_previous_failure_and_300_character_text():
    problematic = 'A leaf icon sits above the name and left of the wordmark center.'
    texts = {'a': problematic, 'b': problematic}
    with pytest.raises(ValueError, match='invalid_generation_profile'):
        output_format({'format': literal.claim_schema(texts)})
    for text in (problematic, problematic+' '+('x'*(299-len(problematic)))):
        assert len(text) <= 300
        payload = compact.catalogue({'a': text, 'b': text})
        schema = compact.claim_schema(payload)
        Draft202012Validator.check_schema(schema)
        assert output_format({'format': schema}) == schema
        assert len(json.dumps(schema)) < 3000
        assert len(payload['a']['options']) == len(literal.literal_claims(text))


def test_schema_upper_bound_at_full_64_choices_per_concept(monkeypatch):
    # Upper-bound proof: the schema depends on up to 128 three-character IDs,
    # never on description/noun/quote lengths. This is not a semantic fixture.
    candidates = literal.literal_claims(TEXTS['a'])
    monkeypatch.setattr(literal, 'literal_claims', lambda _: [deepcopy(candidates[0]) for _ in range(64)])
    payload = compact.catalogue({'a': 'a'*300, 'b': 'b'*300})
    schema = compact.claim_schema(payload)
    assert len(payload['a']['options']) == len(payload['b']['options']) == 64
    assert len(json.dumps(schema)) < 3000
    assert output_format({'format': schema}) == schema
    monkeypatch.setattr(literal, 'literal_claims', lambda _: [deepcopy(candidates[0]) for _ in range(65)])
    with pytest.raises(ValueError, match='complete lexical catalogue'): compact.catalogue(TEXTS)


def test_every_offered_literal_option_survives_catalogue_and_decoder():
    payload = compact.catalogue(TEXTS)
    for key in ('a', 'b'):
        originals = literal.literal_claims(TEXTS[key])
        assert len(originals) == len(payload[key]['options'])
        for index, original in enumerate(originals):
            selected = encode(answer(), payload)
            row = next(r for r in selected['concepts'] if r['id'] == key)
            row['claim_ids'] = [payload[key]['options'][index]['id']]
            decoded, _ = compact.decode(json.dumps(selected), payload)
            assert next(r for r in decoded['concepts'] if r['id'] == key)['claims'] == [original]


def test_explicit_center_selection_keeps_exact_original_reference_quote():
    text = 'The symbol sits left of the wordmark center.'
    payload = compact.catalogue({'a': text, 'b': text})
    value = {'concepts': [{'id': key, 'claim_ids': [next(option['id']
        for option in payload[key]['options'] if option['subject'] == 'symbol'
        and option['relation'] == 'left' and option['reference'] == 'centers')],
        'wordmark_lines': 'unspecified'} for key in ('a', 'b')]}
    decoded, texts = compact.decode(json.dumps(value), payload)
    for row in decoded['concepts']:
        assert row['claims'][0]['reference_quote'] == text
        assert row['claims'][0]['quote'] == text
    assert compact.claims_value(json.dumps(value), payload) == literal.claims_value(json.dumps(decoded), texts)


@pytest.mark.parametrize('fault', ['unknown_id', 'foreign_concept_id', 'missing_ids', 'duplicate_id', 'duplicate_concept', 'manual_quote'])
def test_selection_cannot_invent_or_cross_bind_ids(fault):
    payload = compact.catalogue(TEXTS); value = encode(answer(), payload)
    row = value['concepts'][0]
    if fault == 'unknown_id': row['claim_ids'] = ['a99']
    elif fault == 'foreign_concept_id': row['claim_ids'] = [value['concepts'][1]['claim_ids'][0]]
    elif fault == 'missing_ids': del row['claim_ids']
    elif fault == 'duplicate_id': row['claim_ids'] *= 2
    elif fault == 'duplicate_concept': value['concepts'][1] = deepcopy(row)
    else: row['quote'] = 'An invented new statement.'
    with pytest.raises(ValueError): compact.claims_value(json.dumps(value), payload)


@pytest.mark.parametrize('fault', ['id', 'relation', 'removed', 'reordered', 'extra_geometry'])
def test_changed_catalogue_is_rejected_before_selection(fault):
    payload = compact.catalogue(TEXTS); value = encode(answer(), payload)
    if fault == 'id': payload['a']['options'][0]['id'] = 'renamed'
    elif fault == 'relation': payload['a']['options'][0]['relation'] = 'inside'
    elif fault == 'removed': payload['a']['options'].pop()
    elif fault == 'reordered': payload['a']['options'].reverse()
    else: payload['a']['expected_geometry'] = {'above': True}
    with pytest.raises(ValueError): compact.claim_schema(payload)
    with pytest.raises(ValueError): compact.claims_value(json.dumps(value), payload)


def test_catalogue_is_blind_to_artwork_review_and_scores():
    data = {'plan': {'concept_a': TEXTS['a'], 'concept_b': TEXTS['b']}}
    first = compact.claim_input(data | {'geometry': 'above', 'review': 'pass', 'scores': 3})
    second = compact.claim_input(data | {'geometry': 'below', 'review': 'fail', 'scores': 0})
    assert first == second
    assert all(set(option) == {'id', 'subject', 'subject_quote', 'relation', 'reference'}
               for row in first.values() for option in row['options'])
    assert 'quote' not in json.dumps(compact.claim_schema(first))
