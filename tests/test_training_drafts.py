import json
import hashlib
from pathlib import Path

import pytest

from scripts.draft_training_examples import CASES, candidate, check_response, messages_for
from scripts.prepare_training_data import validate_dataset


def test_all_cases_have_distinct_families_and_hidden_expected_label():
    assert len({c[0] for c in CASES}) == len(CASES)
    for case in CASES:
        messages = messages_for(case)
        assert len(messages) == 2
        assert 'expected_decision' not in str(messages)
        assert messages[1]['content'] == case[3]


def test_structural_success_is_never_automatic_approval():
    case = CASES[-1]
    content = json.dumps({'decision': case[2], 'reason': 'Wymagana jest decyzja właściciela.',
                          'next_steps': ['Przekaż wynik do odbioru właściciela.']})
    check_response(case, content)
    row = candidate(case, messages_for(case), {'content': content}, 'synthetic-test-report')
    assert row['split'] == 'train'
    assert row['review']['status'] == 'pending'
    assert row['review']['evidence'] == []


@pytest.mark.parametrize('patch', [
    {'decision': 'RETEST'}, {'reason': ''}, {'next_steps': []},
    {'next_steps': ['x']}, {'extra': True}, {'next_steps': 'not a list'},
])
def test_evidence_checks_fail_closed(patch):
    value = {'decision': 'READY_FOR_OWNER_REVIEW', 'reason': 'Wymagana decyzja właściciela.',
             'next_steps': ['Przekaż do odbioru.']} | patch
    with pytest.raises(ValueError):
        check_response(CASES[-1], json.dumps(value))


def test_evidence_rejects_duplicate_keys():
    with pytest.raises(ValueError):
        check_response(CASES[-1], '{"decision":"RETEST","decision":"READY_FOR_OWNER_REVIEW"}')


def test_scope_rejects_wrong_classification_and_empty_clarification():
    value = {'fit': 'CLARIFY', 'reason': 'Brakuje reguły obliczeń i obsługi błędów.',
             'questions': [], 'scope': [], 'acceptance_cases': [], 'exclusions': []}
    with pytest.raises(ValueError):
        check_response(CASES[2], json.dumps(value))
    value['questions'] = ['Jak obliczyć wynik?']
    check_response(CASES[2], json.dumps(value))
    with pytest.raises(ValueError):
        check_response(CASES[0], json.dumps(value))


def test_scope_rejects_incomplete_acceptance_case():
    value = {'fit': 'SUPPORTED', 'reason': 'Zakres mieści się w profilu wykonania.',
             'questions': [], 'scope': ['Licznik tekstu'],
             'acceptance_cases': ['GET /api/count?text=aaaaaaaa'], 'exclusions': []}
    with pytest.raises(ValueError):
        check_response(CASES[3], json.dumps(value))
    value['acceptance_cases'] = ['Tekst pusty -> wynik 0']
    check_response(CASES[3], json.dumps(value))


def test_clarify_does_not_finalize_unsupported_upload_plan():
    value = {'fit': 'CLARIFY', 'reason': 'Brakuje formatu i metody wysyłania pliku.',
             'questions': ['Czy POST jest wymagany?'], 'scope': ['Wdrożyć upload POST'],
             'acceptance_cases': [], 'exclusions': []}
    with pytest.raises(ValueError):
        check_response(CASES[5], json.dumps(value))


def test_curated_batch_has_review_proof_and_is_not_full_training_set():
    root = Path(__file__).resolve().parents[1]
    rows, report = validate_dataset((root / 'datasets/qwen/specialization-batch-001.jsonl').read_bytes())
    assert report['reviews'] == {'approved': 9}
    assert report['counts'] == {'train': 9, 'validation': 0, 'test': 0}
    assert not report['export_ready']
    cases = {case[0]: case for case in CASES}
    for row in rows:
        case = cases[row['id'].removeprefix('qwen-draft-')]
        assert row['messages'][:2] == messages_for(case)
        check_response(case, row['messages'][-1]['content'])
        proof = row['review']['evidence'][0]
        path = root / proof['reference'].split('#')[0]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == proof['sha256']
        assert proof['kind'] == 'content_review'
        assert row['review']['reviewer'] == 'assistant-independent-content-review'


def test_curated_reference_arithmetic_and_unicode_assumptions():
    # Independent checks of the reference reasoning, NOT tests of generated apps.
    assert [c * 9 / 5 + 32 for c in [0, 100, -100]] == [32, 212, -148]
    assert len('A 😀') == 3
    assert len('e\u0301') == 2
