"""Bounded dark-background caution on top of the measured alignment review.

This is a conservative English-language screen, not general semantic analysis.
Even a prohibition mentioning a dark background is routed to clarification:
the automatic path only accepts guidance grounded in the delivered paper.
No extra model calls or render passes are introduced.
"""
import re
from scripts import brand_spatial_alignment_review as previous

CONTRACT = 'brand-background-evidence-review.v6'
REVIEW_SCHEMA, CLAIM_SCHEMA = previous.REVIEW_SCHEMA, previous.CLAIM_SCHEMA
CLAIM_SYSTEM, PATCH_SCHEMA = previous.CLAIM_SYSTEM, previous.PATCH_SCHEMA
review_value, claims_value = previous.review_value, previous.claims_value
claim_input, apply, patch_schema = previous.claim_input, previous.apply, previous.patch_schema
remeasure = previous.remeasure
REVIEW_SYSTEM = previous.REVIEW_SYSTEM + '''
Review each alternative in a usage rule separately, including clauses joined by
"or". Correct ink selection does not establish suitability for the stated
background. Use the measured palette evidence; do not approve an unspecified
dark-background application merely because the monochrome ink matches.'''
WRITER_SYSTEM = previous.WRITER_SYSTEM + '''
For a flagged background rule, ground the replacement in the actual supplied
paper and ink. No dark-background variant has been independently established;
do not add a reversed variant or claims about untested background categories.
Choose the complete replacement sentence yourself.'''


def luminance(color):
    if not re.fullmatch(r'#[0-9a-fA-F]{6}', color): raise ValueError('RGB palette required')
    channels = [int(color[i:i+2], 16)/255 for i in (1, 3, 5)]
    linear = [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in channels]
    return sum(a*b for a, b in zip(linear, (.2126, .7152, .0722)))


def expand(data, package):
    result = previous.expand(data, package)
    result['review_contract'] = CONTRACT
    ink, paper = (luminance(data['plan'][key]) for key in ('monochrome_ink', 'paper'))
    result['background_evidence'] = {
        'monochrome_ink': data['plan']['monochrome_ink'], 'paper': data['plan']['paper'],
        'monochrome_on_paper_contrast': round((max(ink, paper)+.05)/(min(ink, paper)+.05), 4),
        'ink_luminance': ink, 'dark_background_variant_verified': False,
        'scope': 'Declared sRGB palette arithmetic; not a print measurement or proof for unspecified backgrounds.'}
    return result


def background_findings(data):
    if luminance(data['plan']['monochrome_ink']) > .1: return []
    findings = []
    for index, rule in enumerate(data['plan']['guidelines']):
        # Do not silently accept a negation: its scope is not parsed by this
        # bounded screen. Uncertain is distinct from a proven contradiction.
        if not re.search(r'\b(?:dark|black)\b[^.!?;]{0,60}\b(?:backgrounds?|surfaces?|stocks?)\b|'
                         r'\b(?:backgrounds?|surfaces?|stocks?)\b[^.!?;]{0,60}\b(?:dark|black)\b', rule, re.I):
            continue
        findings.append({'index': index, 'kind': 'unverified_dark_background_scope', 'quote': rule,
            'monochrome_ink': data['plan']['monochrome_ink'],
            'measurement': 'Dark monochrome ink and an unspecified dark background reference; permission/negation scope needs clarification using the delivered paper.'})
    return findings


def combine(review, claims, data):
    result, findings = previous.combine(review, claims, data)
    for finding in background_findings(data):
        findings.append(finding)
        row = next(r for r in result['reviews'] if r['index'] == finding['index'])
        if row['verdict'] == 'supported': row['verdict'] = 'uncertain'
        row['reason'] = 'Background scope is unverified; ground this rule in the supplied ink and paper.'
    return result, findings
