"""Frozen, offline evaluation catalog. Contents are data, never host-executed."""
from hashlib import sha256
import json
from pathlib import Path

SUITE = Path(__file__).resolve().parents[1]/'datasets/qwen/evaluation/repair-suite-001.json'
CHECKSUM = 'fb5f375568d738d238d8f5a9cc5a33923b82cea1150780d884835bab7a7ce41d'
ROLE_SUITE = SUITE.with_name('role-suite-001.json')
ROLE_CHECKSUM = '611d1d2fbaaae6071b81f4b7e108fcc3f45e353622e1e12c86f6d053e03d5578'


def load_suite():
    raw = SUITE.read_bytes()
    if sha256(raw).hexdigest() != CHECKSUM:
        raise ValueError('Evaluation suite changed: create a separately versioned suite')
    suite = json.loads(raw)
    if suite['version'] != 'repair-evaluation.v1' or suite['usage'] != 'evaluation_only':
        raise ValueError('Invalid evaluation suite')
    return suite


def load_role_suite():
    raw=ROLE_SUITE.read_bytes()
    if sha256(raw).hexdigest()!=ROLE_CHECKSUM:
        raise ValueError('Role evaluation suite changed: create a new version')
    suite=json.loads(raw)
    if suite['version']!='role-evaluation.v1' or suite['usage']!='evaluation_only':
        raise ValueError('Invalid role suite')
    return suite


def reserved_cases():
    return load_suite()['cases']+load_role_suite()['cases']
