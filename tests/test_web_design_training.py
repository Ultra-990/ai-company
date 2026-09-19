import json
from hashlib import sha256
from pathlib import Path

import pytest

from scripts.draft_web_design_training import CASES, FIELDS, candidate, validate_response
from scripts.prepare_training_data import validate_dataset


def response():
    return {field: ['Konkretna decyzja projektowa.', 'Drugie kryterium do sprawdzenia.'] for field in FIELDS}


def test_candidate_is_pending_train_only():
    row = candidate(CASES[0], json.dumps(response()), 'synthetic-fixture')
    _, gate = validate_dataset(json.dumps(row).encode())
    assert row['review']['status'] == 'pending'
    assert row['split'] == 'train' and row['skill'] == 'planning'
    assert not gate['export_ready'] and row['review']['evidence'] == []


@pytest.mark.parametrize('invalid', [None, [], {}, {'art_direction': []}])
def test_bad_response(invalid):
    with pytest.raises(ValueError):
        validate_response(json.dumps(invalid))


def test_duplicate_key_rejected():
    with pytest.raises(ValueError):
        validate_response('{"layout":[],"layout":[]}')


@pytest.mark.parametrize('items', ['bad', ['one'], [4, 5], ['x'*501]*2])
def test_bad_decisions(items):
    value = response()
    value['layout'] = items
    with pytest.raises(ValueError):
        validate_response(json.dumps(value))


def test_unique_original_cases():
    assert len(CASES) == len({case[0] for case in CASES}) == 6
    assert len({case[1] for case in CASES}) == 6


def test_curated_design_records_have_real_review_hash():
    root = Path(__file__).resolve().parents[1]
    rows, gate = validate_dataset((root/'datasets/qwen/web-design-batch-001.jsonl').read_bytes())
    assert len(rows) == 2 and not gate['export_ready']
    for row in rows:
        assert row['split'] == 'train' and row['skill'] == 'planning'
        assert row['review']['status'] == 'approved'
        validate_response(row['messages'][-1]['content'])
        for proof in row['review']['evidence']:
            assert sha256((root/proof['reference']).read_bytes()).hexdigest() == proof['sha256']
