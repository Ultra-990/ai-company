"""Bind extraction choices to source text without consulting artwork or scores."""
from copy import deepcopy
import json
import re

from jsonschema import Draft202012Validator
from scripts import brand_constrained_review as previous
from scripts import brand_spatial_subject_review as subjects

CONTRACT = 'brand-literal-spatial-review.v11'
REVIEW_SYSTEM, WRITER_SYSTEM = previous.REVIEW_SYSTEM, previous.WRITER_SYSTEM
REVIEW_SCHEMA, PATCH_SCHEMA = previous.REVIEW_SCHEMA, previous.PATCH_SCHEMA
review_value, apply, patch_schema = previous.review_value, previous.apply, previous.patch_schema
claim_input, combine, remeasure = previous.claim_input, previous.combine, previous.remeasure
CLAIM_SYSTEM = previous.CLAIM_SYSTEM + '''
The response grammar offers literal source-bound choices. It does not know the
drawing and does not decide which choice expresses the sentence's meaning.
Select the actual subject and relation AS WRITTEN; do not select every offered
choice. The complete concept is used as the quote, including context outside
the particular relation. subject_quote is an exact noun appearing in it.
Preserve all explicit symbol/wordmark directions, ignore internal geometry,
and use uncertain when these choices cannot faithfully express the meaning.
The presence of an offered choice is not evidence that its interpretation is
correct. Do not turn a mention of centers elsewhere into a center comparison.'''


def literal_claims(text):
    if not isinstance(text, str) or not 20 <= len(text) <= 300:
        raise ValueError('Bounded complete concept text required')
    nouns = []
    for role, pattern in (('wordmark', subjects.TEXT_NOUN), ('symbol', subjects.SYMBOL_NOUN)):
        for match in re.finditer(pattern, text, re.I):
            item = (role, match.group())
            if item not in nouns: nouns.append(item)
    choices = []
    def add(candidate):
        # Reuse the existing purely textual constraints. These are possible
        # lexical parses, never assertions that a particular parse is true.
        plain = {k: candidate[k] for k in ('subject', 'subject_quote', 'relation', 'quote')}
        try:
            subjects.claims_value(json.dumps({'concepts': [
                {'id': key, 'claims': [plain]} for key in ('a', 'b')]}), {'a': text, 'b': text})
        except ValueError:
            return
        if candidate not in choices: choices.append(candidate)
    add({'subject': 'wordmark', 'subject_quote': '', 'relation': 'unspecified',
         'quote': '', 'reference': 'bounds', 'reference_quote': ''})
    for role, noun in nouns:
        for relation in subjects.RELATIONS:
            if relation == 'unspecified': continue
            candidate = {'subject': role, 'subject_quote': noun, 'relation': relation,
                         'quote': text, 'reference': 'bounds', 'reference_quote': ''}
            add(candidate)
            if relation in ('above', 'below', 'left', 'right') and re.search(r'\bcent(?:er|re)s?\b', text, re.I):
                add(candidate | {'reference': 'centers', 'reference_quote': text})
    if not nouns:
        # Unknown vocabulary must remain an unresolved claim, not disappear.
        add({'subject': 'symbol', 'subject_quote': text.split()[0], 'relation': 'uncertain',
             'quote': text, 'reference': 'bounds', 'reference_quote': ''})
    if not choices or len(choices) > 64:
        raise ValueError('Bounded literal claim catalogue required')
    return choices


def exact_record(value):
    return {'type': 'object', 'additionalProperties': False, 'required': list(value),
            'properties': {key: {'const': item} for key, item in value.items()}}


def claim_schema(texts):
    if not isinstance(texts, dict) or set(texts) != {'a', 'b'}:
        raise ValueError('Exactly two source concepts required')
    schema = deepcopy(previous.CLAIM_SCHEMA)
    template = schema['properties']['concepts']['items']
    records = []
    for key in ('a', 'b'):
        row = deepcopy(template)
        row['properties']['id'] = {'const': key}
        row['properties']['claims']['items'] = {'anyOf': [exact_record(v) for v in literal_claims(texts[key])]}
        row['properties']['wordmark_lines'] = {'anyOf': [
            exact_record({'relation': 'unspecified', 'quote': ''}),
            *[exact_record({'relation': relation, 'quote': texts[key]})
              for relation in ('single', 'multiple', 'uncertain')]]}
        records.append(row)
    schema['properties']['concepts']['items'] = {'anyOf': records}
    return schema


def claims_value(raw, texts):
    from scripts.brand_guide_revision import parse
    value = parse(raw)
    errors = Draft202012Validator(claim_schema(texts)).iter_errors(value)
    if next(errors, None) is not None:
        raise ValueError('Claims must use the literal source-bound choices')
    return previous.claims_value(raw, texts)


def expand(data, package):
    result = previous.expand(data, package)
    result['review_contract'] = CONTRACT
    return result
