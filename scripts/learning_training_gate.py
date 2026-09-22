"""Deterministic gate for future unattended adapter training.

This module decides whether an intake snapshot is eligible to invoke the
isolated trainer. It never starts a process, loads weights, or promotes an
adapter. Missing evidence is a refusal, not an inferred approval.
"""
from pathlib import Path
import json

from scripts.prepare_training_data import MINIMUMS, unique_object

REQUIRED = ('independently_reviewed_train', 'registered_validation',
            'registered_test', 'matched_baseline_evaluation', 'rollback_plan',
            'trainer_integration')


def decision(state):
    if not isinstance(state, dict) or state.get('schema') != 'learning-autopilot.v1':
        return {'eligible': False, 'reasons': ['recognized_intake_snapshot_required']}
    counts = state.get('counts')
    reasons = []
    if not isinstance(counts, dict):
        reasons.append('counts_required')
    else:
        for split in ('train', 'validation', 'test'):
            value = counts.get(split)
            if type(value) is not int or value < MINIMUMS[split]:
                reasons.append(f'{split}_minimum_not_met')
    if state.get('errors'):
        reasons.append('intake_errors_present')
    if state.get('phase') != 'ready_for_training':
        reasons.append('intake_not_marked_ready_for_training')
    requirements = state.get('training_requirements', {})
    for key in REQUIRED:
        if requirements.get(key) is not True:
            reasons.append(key+'_missing')
    if state.get('training_started') is True:
        reasons.append('training_already_started_in_snapshot')
    return {'eligible': not reasons, 'reasons': reasons,
            'action': 'invoke_isolated_trainer' if not reasons else 'continue_reviewed_intake'}


def read(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Training gate snapshot must be a regular file')
    return decision(json.loads(path.read_text(), object_pairs_hook=unique_object))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('state', type=Path)
    args = parser.parse_args()
    print(json.dumps(read(args.state), ensure_ascii=False))
