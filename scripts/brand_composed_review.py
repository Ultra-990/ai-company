"""Compose grammatical-subject v4 with references/line/background checks v8.

Historical contracts remain unchanged. The bounded English subject validator
is reused, including its fail-closed vocabulary limits; this is not a parser
of arbitrary language or independent visual acceptance.
"""
from copy import deepcopy
import json

from scripts import brand_reference_review as previous
from scripts import brand_spatial_subject_review as subjects

CONTRACT = 'brand-composed-spatial-review.v9'
REVIEW_SCHEMA, PATCH_SCHEMA = previous.REVIEW_SCHEMA, previous.PATCH_SCHEMA
WRITER_SYSTEM = previous.WRITER_SYSTEM
review_value, apply, patch_schema = previous.review_value, previous.apply, previous.patch_schema
claim_input, combine = previous.claim_input, previous.combine
remeasure = subjects.remeasure
REVIEW_SYSTEM = previous.REVIEW_SYSTEM.replace('untested numerical print minima',
    'unsupported claims of tested minimum print sizes') + '''
Distinguish a recommended usage restriction from a claim of completed testing.
"Do not use the full logo below 22 mm" is a designer's minimum-use prescription;
the absence of a render at that size alone does not refute the recommendation.
"Tested and readable at 22 mm" asserts evidence and requires that evidence.
Do not infer a guarantee or a completed measurement from an imperative alone.
Still reject instructions contradicting delivered assets, universal legibility
claims, and instructions to use missing variants, such as removing the symbol
when no separate wordmark-only variant exists. Check the actual entire rule,
including its conditions. A prescription never establishes print readiness.'''
CLAIM_SYSTEM = subjects.CLAIM_SYSTEM + '''
For each claim also return reference: bounds or centers, and reference_quote.
Bounds refers to whole elements; centers is used only for an explicit comparison
of centers or position relative to the other element's center. The relation
still names the quoted SUBJECT's direction relative to the OTHER element.
Do not invert it yourself. A center reference requires an exact nonempty quote
inside the full claim quote and one of above/below/left/right. Other relations
use bounds and an empty reference_quote. Pure alignment without a directional
ordering is unresolved here: use uncertain with bounds, not an invented side.
Also return wordmark_lines for each concept: relation single, multiple,
unspecified or uncertain, plus an exact quote. This concerns the name text only;
a stacked wordmark claims multiple lines, while a symbol above the wordmark
does not. Respect negation. Use unspecified with an empty quote if the number
of text lines is not claimed. Never decide whether the drawing matches.'''
CLAIM_SCHEMA = deepcopy(previous.CLAIM_SCHEMA)
_claim = CLAIM_SCHEMA['properties']['concepts']['items']['properties']['claims']['items']
_claim['required'] += ['subject', 'subject_quote']
_claim['properties'].update(subject={'enum': ['symbol', 'wordmark']},
    subject_quote={'type': 'string', 'maxLength': 100}, relation={'enum': list(subjects.RELATIONS)})


def claims_value(raw, texts):
    from scripts.brand_guide_revision import parse
    value = parse(raw)
    # Reuse v8's exact concept/line-count record validation without asking its
    # legacy spatial validator to interpret the new grammatical fields.
    try:
        lines_only = deepcopy(value)
        for row in lines_only['concepts']:
            row['claims'] = [{'relation': 'unspecified', 'quote': '',
                              'reference': 'bounds', 'reference_quote': ''}]
        previous.claims_value(json.dumps(lines_only), texts)
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError('Structured composed concept claims required') from exc
    grammatical = {'concepts': []}
    for row in value['concepts']:
        if not isinstance(row['claims'], list) or not 1 <= len(row['claims']) <= 3:
            raise ValueError('Bounded grammatical claims required')
        stripped = []
        for claim in row['claims']:
            if (not isinstance(claim, dict) or set(claim) != {'relation', 'quote', 'subject', 'subject_quote', 'reference', 'reference_quote'}
                    or claim['reference'] not in ('bounds', 'centers')
                    or not isinstance(claim['reference_quote'], str) or len(claim['reference_quote']) > 300
                    or not isinstance(claim['quote'], str)):
                raise ValueError('Explicit grammatical subject and bounded reference required')
            if claim['reference'] == 'bounds':
                if claim['reference_quote'] != '': raise ValueError('Bounds reference needs no center quote')
            elif (claim['relation'] not in ('above', 'below', 'left', 'right')
                    or not claim['reference_quote'].strip() or claim['reference_quote'] not in claim['quote']):
                raise ValueError('Center reference needs directional literal evidence')
            stripped.append({key: claim[key] for key in ('subject', 'subject_quote', 'relation', 'quote')})
        grammatical['concepts'].append({'id': row['id'], 'claims': stripped})
    normalized = subjects.claims_value(json.dumps(grammatical), texts)
    for row, original in zip(normalized['concepts'], value['concepts']):
        # v4 deduplicates normalized directions. Do not lose a distinct center
        # reference silently: unsupported duplicate records fail this contract.
        if len(row['claims']) != len(original['claims']):
            raise ValueError('Duplicate normalized directions cannot hide references')
        for claim, source in zip(row['claims'], original['claims']):
            claim.update(reference=source['reference'], reference_quote=source['reference_quote'])
        row['wordmark_lines'] = deepcopy(original['wordmark_lines'])
    return normalized


def expand(data, package):
    # v4 adds its `inside` necessary condition to the same measured geometry;
    # retaining the expanded input also retains v8 centers, lines and palette.
    result = subjects.expand(previous.expand(data, package), package)
    result['review_contract'] = CONTRACT
    return result
