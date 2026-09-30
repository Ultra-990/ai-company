"""Keep center-to-center claims separate from whole-wordmark bounds."""
from copy import deepcopy
import json
from scripts import brand_wordmark_review as previous

CONTRACT = 'brand-spatial-reference-review.v8'
REVIEW_SCHEMA = previous.REVIEW_SCHEMA
REVIEW_SYSTEM = previous.REVIEW_SYSTEM + '''
For any center/alignment statement consult explicit measured_centers, which
are computed from renderer bounds, before deciding. Do not infer centering
from the wordmark's own text-anchor or the original plan. The symbol and
wordmark have separate measured centers. A lower x is left; a lower y is
above. These facts do not establish the semantic identity of a shape.'''
WRITER_SYSTEM, PATCH_SCHEMA = previous.WRITER_SYSTEM, previous.PATCH_SCHEMA
review_value, apply, patch_schema = previous.review_value, previous.apply, previous.patch_schema
claim_input, remeasure = previous.claim_input, previous.remeasure
CLAIM_SYSTEM = previous.CLAIM_SYSTEM + '''
For each spatial claim also identify its reference: bounds or centers.
Use bounds for ordinary placement relative to the whole wordmark, including
above/below/left/right, adjacency, enclosure and overlap. Use centers ONLY
when the sentence explicitly compares center positions or places the symbol
relative to the wordmark's center. For centers, reference_quote must be an
exact nonempty substring of that claim's quote establishing the center
reference. Compare symbol center to wordmark center on the stated axis;
this does not assert separation of the full bounding boxes. Centers can
only accompany above/below/left/right. Other claims use bounds with an
empty reference_quote. Do not infer centers merely to rescue a statement;
use an uncertain relation for unresolved language.'''
CLAIM_SCHEMA = deepcopy(previous.CLAIM_SCHEMA)
_claim = CLAIM_SCHEMA['properties']['concepts']['items']['properties']['claims']['items']
_claim['required'] += ['reference', 'reference_quote']
_claim['properties'].update(reference={'enum': ['bounds', 'centers']},
    reference_quote={'type': 'string', 'maxLength': 300})


def legacy_claims(value, *, omit_centers=False):
    result = deepcopy(value)
    for row in result['concepts']:
        row['claims'] = [{k: v for k, v in c.items() if k not in ('reference', 'reference_quote')}
            for c in row['claims'] if not omit_centers or c['reference'] == 'bounds']
        if not row['claims']: row['claims'] = [{'relation': 'unspecified', 'quote': ''}]
    return result


def claims_value(raw, texts):
    from scripts.brand_guide_revision import parse
    value = parse(raw)
    # Validate the established record counts, exact quotes and line claims.
    try:
        previous.claims_value(json.dumps(legacy_claims(value)), texts)
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError('Structured concept references required') from exc
    for row in value['concepts']:
        for claim in row['claims']:
            if (set(claim) != {'relation', 'quote', 'reference', 'reference_quote'}
                    or claim['reference'] not in ('bounds', 'centers')
                    or not isinstance(claim['reference_quote'], str)
                    or len(claim['reference_quote']) > 300):
                raise ValueError('Explicit bounded spatial reference required')
            if claim['reference'] == 'bounds':
                if claim['reference_quote'] != '': raise ValueError('Bounds reference needs no center quote')
            elif (claim['relation'] not in ('above', 'below', 'left', 'right')
                    or not claim['reference_quote'].strip()
                    or claim['reference_quote'] not in claim['quote']):
                raise ValueError('Center reference needs directional literal evidence')
    return value


def expand(data, package):
    result = previous.expand(data, package)
    result['review_contract'] = CONTRACT
    result['measured_centers'] = {}
    for key, geometry in result['spatial_measurements'].items():
        l, t, r, b = geometry['symbol_bounds']; x, y, u, v = geometry['wordmark_bounds']
        result['measured_centers'][key] = {'symbol': [(l+r)/2, (t+b)/2],
            'wordmark': [(x+u)/2, (y+v)/2],
            'symbol_minus_wordmark': [(l+r-x-u)/2, (t+b-y-v)/2],
            'scope': 'Centers of measured SVG bounds; x rightward, y downward. Not a recognition of symbol meaning.'}
    return result


def combine(review, claims, data):
    result, findings = previous.combine(review, legacy_claims(claims, omit_centers=True), data)
    for concept in claims['concepts']:
        index = 4 if concept['id'] == 'a' else 5
        geometry = data['spatial_measurements'][concept['id']]
        l, t, r, b = geometry['symbol_bounds']; x, y, u, v = geometry['wordmark_bounds']
        dx, dy = (l+r-x-u)/2, (t+b-y-v)/2
        conditions = {'left': dx < 0, 'right': dx > 0, 'above': dy < 0, 'below': dy > 0}
        for claim in concept['claims']:
            if claim['reference'] != 'centers' or conditions[claim['relation']]: continue
            findings.append({'index': index, 'kind': 'measured_center_reference_contradiction',
                'relation': claim['relation'], 'quote': claim['quote'],
                'reference_quote': claim['reference_quote'], 'symbol_minus_wordmark_center': [dx, dy]})
            row = next(v for v in result['reviews'] if v['index'] == index)
            row.update(verdict='unsupported', reason='The explicit center-position claim contradicts measured symbol and wordmark centers.')
    return result, findings
