import json
import pytest
from scripts import brand_spatial_subject_review as subject


def claim(role, noun, relation, quote):
    return {'subject': role, 'subject_quote': noun, 'relation': relation, 'quote': quote}


def test_inversion_is_arithmetic_not_model_normalization():
    texts = {'a': 'The text is placed to the right of the mark.', 'b': 'A bowl sits below the name.'}
    raw = {'concepts': [
        {'id': 'a', 'claims': [claim('wordmark', 'text', 'right', texts['a'])]},
        {'id': 'b', 'claims': [claim('symbol', 'bowl', 'below', texts['b'])]},
    ]}
    value = subject.claims_value(json.dumps(raw), texts)
    assert value['concepts'][0]['claims'][0]['relation'] == 'left'
    assert value['concepts'][1]['claims'][0]['relation'] == 'below'


@pytest.mark.parametrize('fault', ['opposite_word', 'wrong_role', 'invented_noun'])
def test_literal_direction_and_explicit_role_are_checked(fault):
    texts = {'a': 'A bowl sits below the name.', 'b': 'The text sits inside a ring.'}
    first = claim('symbol', 'bowl', 'below', texts['a'])
    if fault == 'opposite_word': first['relation'] = 'above'
    elif fault == 'wrong_role': first['subject'] = 'wordmark'
    else: first['subject_quote'] = 'wordmark'
    raw = {'concepts': [{'id': 'a', 'claims': [first]},
        {'id': 'b', 'claims': [claim('wordmark', 'text', 'inside', texts['b'])]}]}
    with pytest.raises(ValueError): subject.claims_value(json.dumps(raw), texts)


def test_literal_object_can_express_the_valid_inverse_of_enclosure():
    texts = {'a': 'A ring encloses the restaurant name.', 'b': 'The wordmark is inside an oval border.'}
    raw = {'concepts': [
        {'id': 'a', 'claims': [claim('wordmark', 'the restaurant name', 'inside', texts['a'])]},
        {'id': 'b', 'claims': [claim('wordmark', 'The wordmark', 'inside', texts['b'])]},
    ]}
    normalized = subject.claims_value(json.dumps(raw), texts)
    assert [c['claims'][0]['relation'] for c in normalized['concepts']] == ['surrounds', 'surrounds']


def test_unspecified_can_quote_nonspatial_source_but_cannot_hide_direction():
    texts = {'a': 'An abstract sun motif suggests a relaxed mood.', 'b': 'A bowl sits below the name.'}
    raw = {'concepts': [
        {'id': 'a', 'claims': [claim('symbol', '', 'unspecified', texts['a'])]},
        {'id': 'b', 'claims': [claim('symbol', 'bowl', 'below', texts['b'])]},
    ]}
    assert subject.claims_value(json.dumps(raw), texts)['concepts'][0]['claims'][0]['relation'] == 'unspecified'
    raw['concepts'][1]['claims'] = [claim('symbol', '', 'unspecified', '')]
    with pytest.raises(ValueError, match='cannot be omitted'): subject.claims_value(json.dumps(raw), texts)
