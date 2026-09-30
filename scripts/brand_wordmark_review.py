"""Extract wordmark line-count claims separately and compare them with actual SVG."""
from copy import deepcopy
import xml.etree.ElementTree as ET
from scripts import brand_background_review as previous

CONTRACT = 'brand-wordmark-lines-review.v7'
REVIEW_SYSTEM, REVIEW_SCHEMA = previous.REVIEW_SYSTEM, previous.REVIEW_SCHEMA
PATCH_SCHEMA, WRITER_SYSTEM = previous.PATCH_SCHEMA, previous.WRITER_SYSTEM
review_value, apply, patch_schema = previous.review_value, previous.apply, previous.patch_schema
claim_input, remeasure = previous.claim_input, previous.remeasure
CLAIM_SYSTEM = previous.CLAIM_SYSTEM + '''
For each concept also extract wordmark_lines: relation is single, multiple,
unspecified or uncertain, with an exact supporting quote. This refers ONLY to
the restaurant-name text layout. A "stacked wordmark" claims multiple lines;
a symbol stacked above a wordmark does not claim multiple text lines. Negations
must be respected: "not a stacked wordmark" does not assert multiple lines.
Use unspecified with an empty quote when no text-line-count claim is present.
Do not judge the artwork and do not correct the original wording.'''
CLAIM_SCHEMA = deepcopy(previous.CLAIM_SCHEMA)
_item = CLAIM_SCHEMA['properties']['concepts']['items']
_item['required'].append('wordmark_lines')
_item['properties']['wordmark_lines'] = {
    'type': 'object', 'additionalProperties': False, 'required': ['relation', 'quote'],
    'properties': {'relation': {'enum': ['single', 'multiple', 'unspecified', 'uncertain']},
                   'quote': {'type': 'string', 'maxLength': 300}}}


def spatial_only(claims):
    return {'concepts': [{k: v for k, v in row.items() if k != 'wordmark_lines'} for row in claims['concepts']]}


def claims_value(raw, texts):
    from scripts.brand_guide_revision import parse
    value = parse(raw)
    if not isinstance(value, dict) or set(value) != {'concepts'} or not isinstance(value['concepts'], list):
        raise ValueError('Concepts with line-count claims required')
    for row in value['concepts']:
        if not isinstance(row, dict) or set(row) != {'id', 'claims', 'wordmark_lines'}:
            raise ValueError('Separate spatial and text-line-count claims required')
        line = row['wordmark_lines']
        if (row['id'] not in texts or not isinstance(line, dict) or set(line) != {'relation', 'quote'}
                or line['relation'] not in ('single', 'multiple', 'unspecified', 'uncertain')
                or not isinstance(line['quote'], str) or len(line['quote']) > 300
                or (line['relation'] == 'unspecified' and line['quote'] != '')
                or (line['relation'] != 'unspecified' and (not line['quote'].strip() or line['quote'] not in texts[row['id']]))):
            raise ValueError('Line-count claims need literal source evidence')
    import json
    previous.claims_value(json.dumps(spatial_only(value)), texts)
    return value


def line_count(svg):
    root = ET.fromstring(svg)
    texts = [e for e in root.iter() if e.tag.rsplit('}', 1)[-1] == 'text']
    # This source contract uses one plain, unwrapped SVG text element per logo.
    # Fail closed if future formats introduce tspans/textPaths or actual newlines.
    if len(texts) != 1 or list(texts[0]) or any(c in (texts[0].text or '') for c in '\r\n'):
        raise ValueError('One plain SVG wordmark required for line-count evidence')
    return 1


def expand(data, package):
    result = previous.expand(data, package)
    result['review_contract'] = CONTRACT
    result['wordmark_line_counts'] = {key: line_count(result['svg_assets']['logo-'+key+'.svg']['svg']) for key in ('a', 'b')}
    return result


def combine(review, claims, data):
    result, findings = previous.combine(review, spatial_only(claims), data)
    for concept in claims['concepts']:
        claim = concept['wordmark_lines']; relation = claim['relation']
        actual = data['wordmark_line_counts'][concept['id']]
        wrong = (relation == 'single' and actual != 1) or (relation == 'multiple' and actual <= 1)
        if not wrong and relation != 'uncertain': continue
        index = 4 if concept['id'] == 'a' else 5
        findings.append({'index': index, 'kind': 'wordmark_line_count_contradiction' if wrong else 'unresolved_wordmark_line_count',
            'quote': claim['quote'], 'claimed': relation, 'actual_lines': actual})
        row = next(r for r in result['reviews'] if r['index'] == index)
        row['verdict'] = 'unsupported' if wrong else 'uncertain'
        row['reason'] = 'The extracted wordmark line-count claim does not match the delivered plain SVG text.'
    return result, findings
