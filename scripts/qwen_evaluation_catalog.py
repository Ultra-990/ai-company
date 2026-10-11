"""Frozen, offline evaluation catalog. Contents are data, never host-executed."""
from hashlib import sha256
import json
from pathlib import Path
from scripts.training_family_registry import assert_evaluation_families_allowed

SUITE = Path(__file__).resolve().parents[1]/'datasets/qwen/evaluation/repair-suite-001.json'
CHECKSUM = 'fb5f375568d738d238d8f5a9cc5a33923b82cea1150780d884835bab7a7ce41d'
ROLE_SUITE = SUITE.with_name('role-suite-001.json')
ROLE_CHECKSUM = '611d1d2fbaaae6071b81f4b7e108fcc3f45e353622e1e12c86f6d053e03d5578'
REVIEWER_SUITE = SUITE.with_name('reviewer-suite-001.json')
REVIEWER_CHECKSUM = 'ecf12bb97cde6807db52dba36431588a21f858bcc9d1f25c43fa6dec8eaded75'
EVIDENCE_CURRICULUM_CHECKSUM = (
    '9c1e1b37b80a21dddad0e55cf65c8273bf96ea0c6b330341ac700473244462b8')


def load_suite():
    raw = SUITE.read_bytes()
    if sha256(raw).hexdigest() != CHECKSUM:
        raise ValueError('Evaluation suite changed: create a separately versioned suite')
    suite = json.loads(raw)
    if suite['version'] != 'repair-evaluation.v1' or suite['usage'] != 'evaluation_only':
        raise ValueError('Invalid evaluation suite')
    assert_evaluation_families_allowed(suite['cases'])
    return suite


def load_role_suite():
    raw=ROLE_SUITE.read_bytes()
    if sha256(raw).hexdigest()!=ROLE_CHECKSUM:
        raise ValueError('Role evaluation suite changed: create a new version')
    suite=json.loads(raw)
    if suite['version']!='role-evaluation.v1' or suite['usage']!='evaluation_only':
        raise ValueError('Invalid role suite')
    assert_evaluation_families_allowed(suite['cases'])
    return suite


def load_evidence_calibration_reservations():
    """Expose held-out prompts without trusting a mutable module constant."""
    from scripts import evidence_calibration_data as evidence

    cases = evidence.cases()
    serialized = json.dumps(cases, ensure_ascii=False, sort_keys=True,
                            separators=(',', ':')).encode()
    if sha256(serialized).hexdigest() != EVIDENCE_CURRICULUM_CHECKSUM:
        raise ValueError('Evidence calibration curriculum changed: create a new version')
    held_out = [case for case in cases if case['split'] in ('validation', 'test')]
    if len(held_out) != 18:
        raise ValueError('Evidence calibration reservation count changed')
    assert_evaluation_families_allowed(held_out)
    return [{'id': case['id'], 'family': case['family'],
             'brief': evidence.messages_for(case)[1]['content'],
             'usage': 'evaluation_only'} for case in held_out]


def reserved_cases():
    return (load_suite()['cases'] + load_role_suite()['cases']
            + load_reviewer_suite()['cases']
            + load_evidence_calibration_reservations())


def load_reviewer_suite():
    raw=REVIEWER_SUITE.read_bytes()
    if sha256(raw).hexdigest()!=REVIEWER_CHECKSUM:
        raise ValueError('Reviewer evaluation changed: create a new version')
    suite=json.loads(raw)
    if suite['version']!='reviewer-evaluation.v1' or suite['usage']!='evaluation_only':
        raise ValueError('Invalid reviewer suite')
    assert_evaluation_families_allowed(suite['cases'])
    return suite
