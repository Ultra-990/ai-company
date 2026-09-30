"""Require every explicit wordmark line-count phrase to be accounted for.

Spatial choices remain the complete source-only v11 catalogue encoded by v12.
The additional line catalogue is also derived only from source text. It never
consults artwork or selects an answer from geometry.
"""
from copy import deepcopy
import json
import re

from jsonschema import Draft202012Validator
from scripts import brand_compact_review as previous
from scripts import brand_literal_review as literal

CONTRACT = 'brand-explicit-lines-review.v13'
REVIEW_SYSTEM, WRITER_SYSTEM = previous.REVIEW_SYSTEM, previous.WRITER_SYSTEM
REVIEW_SCHEMA, PATCH_SCHEMA = previous.REVIEW_SCHEMA, previous.PATCH_SCHEMA
review_value, apply, patch_schema = previous.review_value, previous.apply, previous.patch_schema
combine, remeasure = previous.combine, previous.remeasure
CLAIM_SYSTEM = previous.CLAIM_SYSTEM + '''
For each concept select exactly one wordmark_line_id from its separate source
catalogue. An explicit line-count phrase cannot be omitted as unspecified.
"Stacked wordmark" and "two-line wordmark" concern the restaurant-name lines;
a symbol stacked above or below a name does not. Respect negation: "not a
stacked wordmark" is not a positive multiple-line claim. Choose uncertain when
the supplied source-bound interpretations do not justify a positive count.
The catalogue contains no facts about the drawing. Do not judge geometry.'''


def line_options(text, key):
    if not isinstance(text, str) or not 20 <= len(text) <= 300:
        raise ValueError('Bounded complete concept text required')
    lower = text.lower(); relations = []
    line_form = r'(?:stacked|(?:single|one|two|multi)[- ]line)'
    negated = (re.search(r'\bnot\s+(?:a\s+)?'+line_form+r'\s+(?:wordmark|name)\b', lower)
               or re.search(r'\b(?:wordmark|name)\s+(?:is\s+)?not\s+'+line_form+r'\b', lower))
    single = re.search(r'\b(?:single[- ]line|one[- ]line)\s+(?:wordmark|name)\b|\b(?:wordmark|name)\s+(?:(?:is\s+)?set\s+|is\s+)?(?:on|in)\s+one\s+line\b', lower)
    multiple = re.search(r'\b(?:two|multi)[- ]line\s+(?:wordmark|name)\b|\bstacked\s+(?:wordmark|name)\b|\b(?:wordmark|name)\s+(?:uses|is\s+set\s+(?:on|in))\s+two\s+lines\b', lower)
    if single and not negated: relations.append('single')
    if multiple and not negated: relations.append('multiple')
    explicit = bool(single or multiple or negated)
    if explicit: relations.append('uncertain')
    else: relations.append('unspecified')
    return [{'id': key+'l'+str(index).zfill(2), 'relation': relation,
             'quote': '' if relation == 'unspecified' else text}
            for index, relation in enumerate(dict.fromkeys(relations))]


def catalogue(texts):
    result = deepcopy(previous.catalogue(texts))
    for key in ('a', 'b'):
        result[key]['line_options'] = line_options(result[key]['text'], key)
    return result


def claim_input(data):
    return catalogue(previous.original_texts(previous.claim_input(data)))


def original_texts(payload):
    if (not isinstance(payload, dict) or set(payload) != {'a', 'b'} or
            any(not isinstance(row, dict) or set(row) != {'text', 'options', 'line_options'}
                for row in payload.values())):
        raise ValueError('Original texts and complete lexical catalogues required')
    texts = {key: payload[key]['text'] for key in ('a', 'b')}
    if payload != catalogue(texts):
        raise ValueError('Lexical catalogue, line catalogue or IDs changed')
    return texts


def claim_schema(payload):
    original_texts(payload); rows = []
    for key in ('a', 'b'):
        rows.append({'type': 'object', 'additionalProperties': False,
            'required': ['id', 'claim_ids', 'wordmark_line_id'], 'properties': {
                'id': {'const': key},
                'claim_ids': {'type': 'array', 'minItems': 1, 'maxItems': 3, 'uniqueItems': True,
                              'items': {'enum': [c['id'] for c in payload[key]['options']]}},
                'wordmark_line_id': {'enum': [c['id'] for c in payload[key]['line_options']]}}})
    return {'type': 'object', 'additionalProperties': False, 'required': ['concepts'],
            'properties': {'concepts': {'type': 'array', 'minItems': 2, 'maxItems': 2,
                                       'items': {'anyOf': rows}}}}


def decode(raw, payload):
    from scripts.brand_guide_revision import parse
    texts = original_texts(payload); value = parse(raw)
    if next(Draft202012Validator(claim_schema(payload)).iter_errors(value), None) is not None:
        raise ValueError('Select only supplied spatial and wordmark-line IDs')
    if {row['id'] for row in value['concepts']} != {'a', 'b'}:
        raise ValueError('Exactly one selection for each original concept required')
    decoded = {'concepts': []}
    for row in value['concepts']:
        key = row['id']; compact = previous.catalogue(texts)
        spatial = {option['id']: claim for option, claim in
                   zip(compact[key]['options'], literal.literal_claims(texts[key]))}
        lines = {option['id']: option for option in payload[key]['line_options']}
        line = lines[row['wordmark_line_id']]
        decoded['concepts'].append({'id': key,
            'claims': [deepcopy(spatial[choice]) for choice in row['claim_ids']],
            'wordmark_lines': {'relation': line['relation'], 'quote': line['quote']}})
    return decoded, texts


def claims_value(raw, payload):
    decoded, texts = decode(raw, payload)
    return literal.claims_value(json.dumps(decoded), texts)


def expand(data, package):
    result = previous.expand(data, package)
    result['review_contract'] = CONTRACT
    return result
