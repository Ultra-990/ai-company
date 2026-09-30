from copy import deepcopy
import json

from jsonschema import Draft202012Validator
import pytest
from scripts import brand_literal_review as protocol


TEXTS = {'a': 'The wordmark sits below the ring.',
         'b': 'The single-line name sits left of the bowl.'}


def answer(texts=TEXTS):
    return {'concepts': [{'id': key, 'claims': [next(c for c in protocol.literal_claims(text)
        if c['subject'] == 'wordmark' and c['relation'] == relation and c['reference'] == 'bounds')],
        'wordmark_lines': {'relation': 'single', 'quote': text} if key == 'b'
                          else {'relation': 'unspecified', 'quote': ''}}
        for key, text, relation in [('a', texts['a'], 'below'), ('b', texts['b'], 'left')]]}


def test_literal_selection_normalizes_subject_without_using_artwork():
    schema = protocol.claim_schema(TEXTS)
    Draft202012Validator.check_schema(schema)
    value = answer()
    Draft202012Validator(schema).validate(value)
    normalized = protocol.claims_value(json.dumps(value), TEXTS)
    assert normalized['concepts'][0]['claims'][0]['relation'] == 'above'
    assert normalized['concepts'][1]['claims'][0]['relation'] == 'right'
    # A false geometric statement is still a grammatical choice. The later
    # independent measurement must refute it; grammar never encodes the image.
    assert any(c['relation'] == 'below' for c in protocol.literal_claims(TEXTS['a']))


@pytest.mark.parametrize('fault', ['quote', 'subject', 'reference', 'direction', 'line_quote', 'other_concept'])
def test_changed_literal_fields_are_rejected_by_grammar_and_replay(fault):
    value = answer(); claim = value['concepts'][0]['claims'][0]
    if fault == 'quote': claim['quote'] = 'Below the ring.'
    elif fault == 'subject': claim['subject_quote'] = 'name'
    elif fault == 'reference': claim.update(reference='centers', reference_quote=TEXTS['a'])
    elif fault == 'direction': claim['relation'] = 'side_by_side'
    elif fault == 'line_quote': value['concepts'][1]['wordmark_lines']['quote'] = 'Invented line claim'
    else: value['concepts'][0]['id'] = 'b'
    assert not Draft202012Validator(protocol.claim_schema(TEXTS)).is_valid(value)
    with pytest.raises(ValueError, match='source-bound'): protocol.claims_value(json.dumps(value), TEXTS)


def test_paired_geometry_does_not_invent_adjacency_or_claim_absent_subject():
    text = 'A horizontal name paired with a leaf motif.'
    choices = protocol.literal_claims(text)
    assert not any(c['relation'] == 'side_by_side' for c in choices)
    assert all(c['subject_quote'] in c['quote'] for c in choices)
    assert any(c['relation'] == 'unspecified' and c['subject_quote'] == '' for c in choices)


def test_center_reference_requires_explicit_center_language():
    text = 'The symbol sits left of the wordmark center.'
    choices = protocol.literal_claims(text)
    assert any(c['reference'] == 'centers' and c['reference_quote'] == text for c in choices)
    assert not any(c['reference'] == 'centers' for c in protocol.literal_claims('A centered name sits above the ring.'))


def test_unknown_nouns_keep_uncertainty_available_and_cannot_omit_explicit_relation():
    choices = protocol.literal_claims('The wordmark floats above a frond.')
    assert any(c['relation'] == 'uncertain' for c in choices)
    assert not any(c['relation'] == 'unspecified' for c in choices)
    choices = protocol.literal_claims('Quiet abstract gestures evoke morning.')
    assert any(c['relation'] == 'uncertain' for c in choices)


def test_text_bound_and_concept_identity_fail_closed():
    for value in ({'a': TEXTS['a']}, {'a': 'x'*301, 'b': TEXTS['b']}, {'a': None, 'b': TEXTS['b']}):
        with pytest.raises(ValueError): protocol.claim_schema(value)
    value = answer(); value['concepts'][1] = deepcopy(value['concepts'][0])
    # JSON grammar alone cannot enforce uniqueness of per-item ids; replay does.
    with pytest.raises(ValueError): protocol.claims_value(json.dumps(value), TEXTS)
