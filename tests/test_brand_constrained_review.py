from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

from jsonschema import Draft202012Validator
import pytest

from scripts import brand_constrained_review as review
from scripts import brand_composed_review as previous

UNSPECIFIED = {'relation': 'unspecified', 'quote': 'A warm abstract motif.', 'subject': 'symbol',
    'subject_quote': '', 'reference': 'bounds', 'reference_quote': ''}
DIRECTION = {'relation': 'below', 'quote': 'The wordmark sits below the ring.', 'subject': 'wordmark',
    'subject_quote': 'wordmark', 'reference': 'bounds', 'reference_quote': ''}
CENTER = {'relation': 'left', 'quote': 'The name sits left of the symbol center.', 'subject': 'wordmark',
    'subject_quote': 'name', 'reference': 'centers', 'reference_quote': 'symbol center'}
ITEM = review.CLAIM_SCHEMA['properties']['concepts']['items']['properties']['claims']['items']


@pytest.mark.parametrize('value', [UNSPECIFIED, DIRECTION, CENTER])
def test_three_valid_grammatical_reference_branches(value):
    Draft202012Validator.check_schema(review.CLAIM_SCHEMA)
    Draft202012Validator(ITEM).validate(value)
    assert sum(Draft202012Validator(branch).is_valid(value) for branch in ITEM['anyOf']) == 1
    raw = {'concepts': [{'id': key, 'claims': [value], 'wordmark_lines': {'relation': 'unspecified', 'quote': ''}}
                        for key in ('a', 'b')]}
    texts = {key: value['quote'] for key in ('a', 'b')}
    Draft202012Validator(review.CLAIM_SCHEMA).validate(raw)
    assert review.claims_value(json.dumps(raw), texts) == previous.claims_value(json.dumps(raw), texts)


@pytest.mark.parametrize('value', [
    UNSPECIFIED | {'subject_quote': 'wordmark'},
    UNSPECIFIED | {'reference': 'centers'},
    UNSPECIFIED | {'reference_quote': 'center'},
    DIRECTION | {'subject_quote': ''},
    DIRECTION | {'quote': ''},
    DIRECTION | {'reference_quote': 'center'},
    CENTER | {'reference_quote': ''},
    CENTER | {'relation': 'surrounds'},
])
def test_eight_cross_field_contradictions_are_disallowed_by_decoder_schema(value):
    assert not Draft202012Validator(ITEM).is_valid(value)
    old_item = previous.CLAIM_SCHEMA['properties']['concepts']['items']['properties']['claims']['items']
    assert Draft202012Validator(old_item).is_valid(value)  # The old grammar stays unchanged.


def test_v10_reuses_all_validation_and_reviewer_logic():
    for name in ('claims_value', 'review_value', 'apply', 'patch_schema', 'combine', 'remeasure',
                 'claim_input', 'REVIEW_SYSTEM', 'WRITER_SYSTEM', 'CLAIM_SYSTEM', 'REVIEW_SCHEMA', 'PATCH_SCHEMA'):
        assert getattr(review, name) is getattr(previous, name)
    old = deepcopy(previous.CLAIM_SCHEMA)
    assert 'anyOf' not in old['properties']['concepts']['items']['properties']['claims']['items']
    assert review.CONTRACT != previous.CONTRACT


def test_schema_does_not_replace_literal_semantic_validation():
    value = DIRECTION | {'subject_quote': 'invented noun'}
    Draft202012Validator(ITEM).validate(value)
    raw = {'concepts': [{'id': key, 'claims': [value], 'wordmark_lines': {'relation': 'unspecified', 'quote': ''}}
                        for key in ('a', 'b')]}
    with pytest.raises(ValueError):
        review.claims_value(json.dumps(raw), {key: value['quote'] for key in ('a', 'b')})


def test_constrained_cli_is_explicit_without_replacing_v9():
    result = subprocess.run([sys.executable, 'scripts/brand_school.py', '--help'],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
    assert '--revise-constrained-text' in result.stdout and '--revise-composed-text' in result.stdout
