"""Measured spatial review with a conservative check of centering claims."""
import re
from scripts import brand_spatial_review as previous

CONTRACT = 'brand-measured-alignment-review.v5'
REVIEW_SYSTEM, REVIEW_SCHEMA = previous.REVIEW_SYSTEM, previous.REVIEW_SCHEMA
CLAIM_SYSTEM, CLAIM_SCHEMA = previous.CLAIM_SYSTEM, previous.CLAIM_SCHEMA
PATCH_SCHEMA = previous.PATCH_SCHEMA
review_value, claims_value = previous.review_value, previous.claims_value
claim_input, apply, patch_schema = previous.claim_input, previous.apply, previous.patch_schema
remeasure = previous.remeasure
WRITER_SYSTEM = previous.WRITER_SYSTEM + '''
For a concept correction state the depicted symbol and its supported position
relative to the wordmark. Do not add new alignment or aesthetic claims. A symbol
above the wordmark is not necessarily centered over it. Base any centering claim
on matching measured horizontal centers, not the original plan's adjectives.'''


def expand(data, package):
    result = previous.expand(data, package)
    result['review_contract'] = CONTRACT
    return result


def combine(review, claims, data):
    result, findings = previous.combine(review, claims, data)
    for key in ('a', 'b'):
        text = data['plan']['concept_'+key]
        if not re.search(r'\bcent(?:er|re)(?:ed|d)\b', text, re.I): continue
        boxes = data['spatial_measurements'][key]
        a, _, c, _ = boxes['symbol_bounds']; x, _, u, _ = boxes['wordmark_bounds']
        delta = abs((a+c-x-u)/2)
        if delta <= 2: continue
        index = 4 if key == 'a' else 5
        findings.append({'index': index, 'kind': 'unresolved_centering_claim', 'quote': text,
            'symbol_center_x': (a+c)/2, 'wordmark_center_x': (x+u)/2, 'difference_px': delta,
            'measurement': 'Horizontal centers differ by more than 2 rendered pixels; broad centered-layout wording is not independently supported.'})
        row = next(r for r in result['reviews'] if r['index'] == index)
        if row['verdict'] == 'supported': row['verdict'] = 'uncertain'
        row['reason'] = 'Measured horizontal centers differ; clarify the unsupported centering claim.'
    return result, findings
