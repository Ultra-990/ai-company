import json

from jsonschema import Draft202012Validator
import pytest
from app.services.local_ollama import output_format
from scripts import brand_explicit_lines_review as explicit


CASES = {
    'stacked': ('A centered stacked wordmark in Georgia sits with a restrained reed motif.', {'multiple', 'uncertain'}),
    'two_line': ('A two-line wordmark in Georgia sits beside a restrained reed motif.', {'multiple', 'uncertain'}),
    'single': ('A single-line name in Georgia sits above a restrained reed motif.', {'single', 'uncertain'}),
    'symbol_stack': ('A reed symbol is stacked above the name in a calm centered composition.', {'unspecified'}),
    'negated': ('A centered name in Georgia is not a stacked wordmark beside the reed motif.', {'uncertain'}),
    'negated_two': ('This is not a two-line wordmark beside the restrained reed motif.', {'uncertain'}),
    'negated_single': ('The name is not a single-line name beside the restrained reed motif.', {'uncertain'}),
    'absent': ('A Georgia wordmark accompanies a restrained reed and water motif.', {'unspecified'}),
}


def payload(a=CASES['stacked'][0], b=CASES['symbol_stack'][0]):
    return explicit.catalogue({'a': a, 'b': b})


def selection(value, *, line_a=None, line_b=None):
    rows = []
    for key, chosen in (('a', line_a), ('b', line_b)):
        line = next(o for o in value[key]['line_options'] if o['relation'] == (chosen or value[key]['line_options'][0]['relation']))
        rows.append({'id': key, 'claim_ids': [value[key]['options'][0]['id']], 'wordmark_line_id': line['id']})
    return {'concepts': rows}


def encode(value, payload):
    """Fixture only: encode a known normalized v11 answer as v13 IDs."""
    from scripts import brand_literal_review as literal
    result = {'concepts': []}
    for row in value['concepts']:
        key = row['id']; originals = literal.literal_claims(payload[key]['text'])
        claims = [payload[key]['options'][originals.index(claim)]['id'] for claim in row['claims']]
        line = next(option['id'] for option in payload[key]['line_options']
                    if option['relation'] == row['wordmark_lines']['relation'])
        result['concepts'].append({'id': key, 'claim_ids': claims, 'wordmark_line_id': line})
    return result


@pytest.mark.parametrize('name', CASES)
def test_source_line_catalogue_distinguishes_claims_negation_and_symbol_composition(name):
    text, expected = CASES[name]; options = explicit.line_options(text, 'a')
    assert {row['relation'] for row in options} == expected
    assert all(row['quote'] == ('' if row['relation'] == 'unspecified' else text) for row in options)


def test_explicit_phrase_cannot_be_silently_omitted_but_model_can_choose_uncertain():
    value = payload(); answer = selection(value, line_a='uncertain')
    decoded, _ = explicit.decode(json.dumps(answer), value)
    assert decoded['concepts'][0]['wordmark_lines'] == {'relation': 'uncertain', 'quote': value['a']['text']}
    answer['concepts'][0]['wordmark_line_id'] = 'al99'
    with pytest.raises(ValueError, match='supplied'): explicit.claims_value(json.dumps(answer), value)


def test_compact_spatial_direction_still_decodes_through_v11_inversion():
    text = 'A single-line wordmark sits above a small reed symbol.'
    value = explicit.catalogue({'a': text, 'b': text})
    answer = selection(value, line_a='single', line_b='single')
    for row in answer['concepts']:
        key = row['id']; row['claim_ids'] = [next(o['id'] for o in value[key]['options']
            if o['subject'] == 'wordmark' and o['relation'] == 'above')]
    checked = explicit.claims_value(json.dumps(answer), value)
    # The extractor records subject/relation as written; the unchanged v4/v11
    # validator then converts a wordmark-above-symbol claim to symbol-below-wordmark.
    assert [row['claims'][0]['relation'] for row in checked['concepts']] == ['below', 'below']


def test_v13_schema_fits_real_adapter_at_maximum_source_lengths():
    text = CASES['stacked'][0]+' '+('x'*(300-len(CASES['stacked'][0])-1))
    value = explicit.catalogue({'a': text, 'b': text})
    schema = explicit.claim_schema(value)
    Draft202012Validator.check_schema(schema)
    assert output_format({'format': schema}) == schema
    assert len(json.dumps(schema)) < 3000


@pytest.mark.parametrize('fault', ['geometry', 'line_removed', 'line_relation', 'line_id'])
def test_line_catalogue_is_source_bound_and_contains_no_geometry(fault):
    value = payload(); answer = selection(value)
    if fault == 'geometry': value['a']['expected_lines'] = 2
    elif fault == 'line_removed': value['a']['line_options'].pop()
    elif fault == 'line_relation': value['a']['line_options'][0]['relation'] = 'single'
    else: value['a']['line_options'][0]['id'] = 'changed'
    with pytest.raises(ValueError): explicit.claims_value(json.dumps(answer), value)
