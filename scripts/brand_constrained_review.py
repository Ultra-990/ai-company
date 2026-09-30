"""Constrain grammatical/reference field combinations without changing v9 logic."""
from copy import deepcopy
from scripts import brand_composed_review as previous

CONTRACT = 'brand-constrained-spatial-review.v10'
REVIEW_SYSTEM, WRITER_SYSTEM, CLAIM_SYSTEM = previous.REVIEW_SYSTEM, previous.WRITER_SYSTEM, previous.CLAIM_SYSTEM
REVIEW_SCHEMA, PATCH_SCHEMA = previous.REVIEW_SCHEMA, previous.PATCH_SCHEMA
review_value, claims_value = previous.review_value, previous.claims_value
apply, patch_schema = previous.apply, previous.patch_schema
claim_input, combine, remeasure = previous.claim_input, previous.combine, previous.remeasure

CLAIM_SCHEMA = deepcopy(previous.CLAIM_SCHEMA)
_claims = CLAIM_SCHEMA['properties']['concepts']['items']['properties']['claims']
_base = _claims['items']
_unspecified = deepcopy(_base)
_unspecified['properties'].update(relation={'const': 'unspecified'}, subject_quote={'const': ''},
    reference={'const': 'bounds'}, reference_quote={'const': ''})
_bounds = deepcopy(_base)
_bounds['properties'].update(
    relation={'enum': [relation for relation in previous.subjects.RELATIONS if relation != 'unspecified']},
    subject_quote={'type': 'string', 'minLength': 1, 'maxLength': 100},
    quote={'type': 'string', 'minLength': 1, 'maxLength': 300},
    reference={'const': 'bounds'}, reference_quote={'const': ''})
_centers = deepcopy(_bounds)
_centers['properties'].update(relation={'enum': ['above', 'below', 'left', 'right']},
    reference={'const': 'centers'}, reference_quote={'type': 'string', 'minLength': 1, 'maxLength': 300})
_claims['items'] = {'anyOf': [_unspecified, _bounds, _centers]}


def expand(data, package):
    result = previous.expand(data, package)
    result['review_contract'] = CONTRACT
    return result
