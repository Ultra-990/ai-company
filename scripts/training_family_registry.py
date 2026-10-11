"""Pinned training-only family registry for future evaluation loaders."""
from hashlib import sha256
import json
from pathlib import Path
import re

REGISTRY = Path(__file__).resolve().parents[1] / 'datasets/qwen/training-only-families-001.json'
CHECKSUM = 'bebefeea28d1e9c501041db272f80ec994e35f4bafd02f7e3642e04cdb737195'


def load_training_only_families():
    raw = REGISTRY.read_bytes()
    if sha256(raw).hexdigest() != CHECKSUM:
        raise ValueError('Training-only family registry changed: create a new version')
    value = json.loads(raw)
    if (not isinstance(value, dict) or set(value) != {'version', 'usage', 'families'}
            or value['version'] != 'training-only-families.v1'
            or value['usage'] != 'evaluation_exclusion'
            or not isinstance(value['families'], list) or not value['families']):
        raise ValueError('Invalid training-only family registry')
    result = set()
    for row in value['families']:
        if (not isinstance(row, dict) or set(row) != {'id', 'reason'}
                or not isinstance(row['id'], str)
                or not re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,99}', row['id'])
                or not isinstance(row['reason'], str) or not row['reason'].strip()
                or row['id'] in result):
            raise ValueError('Invalid training-only family entry')
        result.add(row['id'])
    return result


def assert_evaluation_families_allowed(cases):
    """Fail closed when an evaluation suite uses any exposed training family."""
    reserved = load_training_only_families()
    if cases is None or isinstance(cases,(str,bytes,dict)):
        raise ValueError('Evaluation cases must be a sequence of cases')
    try:
        items=list(cases)
        families = [case['family'] if isinstance(case, dict) else case for case in items]
    except (KeyError, TypeError):
        raise ValueError('Evaluation cases require explicit family identifiers') from None
    if any(not isinstance(family, str) or not family for family in families):
        raise ValueError('Evaluation cases require explicit family identifiers')
    overlap = sorted(set(families) & reserved)
    if overlap:
        raise ValueError('Evaluation suite contains a training-only family')
    return True
