"""Bounded handoff from reviewed intake to the isolated corpus trainer.

The runner is deliberately boring: it asks the deterministic gate first,
captures the exact command and output in a private directory, and never
promotes weights or changes production routing. A refused handoff is a normal
result while validation, test, and rollback evidence are incomplete.
"""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import tempfile

from scripts.learning_training_gate import decision
from scripts.prepare_training_data import unique_object

REPO = Path(__file__).resolve().parents[1]
TRAINER = REPO / 'scripts' / 'train_vision_corpus.py'
PRIVATE_ROOT = Path('/home/marcin/ai-company-workspaces/learning-autopilot')


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def integration_status():
    """Return evidence that the concrete trainer handoff is registered."""
    if TRAINER.is_symlink() or not TRAINER.is_file():
        return {'ready': False, 'reason': 'trainer_script_missing'}
    return {'ready': True, 'trainer': str(TRAINER), 'trainer_sha256': digest(TRAINER),
            'command': ['--state', '<state>', '--exam', '<validation-exam>', '--run'],
            'promotion': 'disabled'}


def _regular(path, label):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'{label} must be a regular file')
    return path


def invoke(state_path, exam_path, *, output_root=PRIVATE_ROOT, run=False):
    """Gate and optionally invoke the research trainer.

    ``run=False`` is a read-only planning mode used by the intake cycle and
    tests. Even in run mode the trainer writes a research adapter only; this
    wrapper has no code path that promotes it.
    """
    state_path = _regular(state_path, 'Intake state')
    exam_path = _regular(exam_path, 'Validation exam')
    state = json.loads(state_path.read_text(), object_pairs_hook=unique_object)
    gate = decision(state)
    contract = integration_status()
    result = {'schema': 'learning-trainer-handoff.v1', 'state_sha256': digest(state_path),
              'exam_sha256': digest(exam_path), 'gate': gate, 'integration': contract,
              'training_started': False, 'automatic_promotion': False,
              'production_changed': False}
    if not gate['eligible']:
        result['status'] = 'refused_by_gate'
        return result
    if not contract['ready']:
        result['status'] = 'refused_missing_trainer'
        return result
    command = [str(REPO / '.venv/bin/python'), str(TRAINER), '--state', str(state_path),
               '--exam', str(exam_path), '--run']
    result['command'] = command
    if not run:
        result['status'] = 'ready_to_invoke'
        return result
    output_root = Path(output_root)
    if output_root.is_symlink():
        raise ValueError('Private output root cannot be a symlink')
    output_root.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='trainer-handoff-', dir=output_root))
    env = os.environ.copy()
    for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS'):
        env.pop(key, None)
    log = out / 'trainer.log'
    result['output'] = str(out)
    result['training_started'] = True
    with log.open('w') as stream:
        process = subprocess.run(command, cwd=REPO, env=env, stdout=stream,
                                 stderr=subprocess.STDOUT, timeout=2430, check=False)
    result['exit_code'] = process.returncode
    result['status'] = 'completed' if process.returncode == 0 else 'failed'
    result['log_sha256'] = digest(log)
    result['automatic_promotion'] = False
    result['production_changed'] = False
    (out / 'handoff.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--exam', type=Path, required=True)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    print(json.dumps(invoke(args.state, args.exam, run=args.run), ensure_ascii=False))
