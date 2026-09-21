"""Periodic collection and CPU audit of reviewed learning data; never self-approve.

This first stage does not yet schedule weight updates. Its report explicitly
lists missing data and trainer/evaluation integration instead of rerunning tiny
research pilots or mistaking a successful data audit for training.
"""
import argparse
from datetime import datetime, timezone
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import interior_learning_records as interior
from scripts import vector_learning_records as vector
from scripts.check_vision_training_inputs import verify_bundle
from scripts.prepare_training_data import MINIMUMS, unique_object

REPO = Path(__file__).resolve().parents[1]
ROOT = Path('/home/marcin/ai-company-workspaces/learning-autopilot')


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    temporary.replace(path)


def sources():
    """Only explicit independent review artifacts; no client/production DB scan."""
    return [('vector', path) for path in sorted(vector.school.ROOT.glob('patch-*/experience.json'))] + [
        ('interior', path) for path in sorted(interior.school.ROOT.glob('inspect-*/teacher-judgments.json'))]


def collect(kind, path):
    if kind == 'vector':
        archived = vector.read(path)
        report = Path(archived['source']['report']); review = Path(archived['review']['path'])
        if archived != vector.patch.experience(report, review):
            raise ValueError('Archived experience changed')
        if archived['split'] != 'train': return [], None
        rows, _ = vector.collect(report, review)
        return rows, lambda: vector.export([path])
    if kind == 'interior':
        rows, _ = interior.collect(path.parent/'report.json', path)
        return rows, lambda: interior.export(path.parent/'report.json', path)
    raise ValueError('Unknown collector')


def audit(bundle):
    env = os.environ.copy()
    for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS'):
        env.pop(key, None)
    result = subprocess.run([str(REPO/'.venv/bin/python'), str(REPO/'scripts/check_vision_training_inputs.py'),
                             str(bundle), '--run'], cwd=REPO, env=env, capture_output=True,
                            text=True, timeout=150, check=False)
    # Keep actual failure output private. No retry in the same cycle.
    (bundle/'automatic-audit.log').write_text(result.stdout+'\n'+result.stderr)
    if result.returncode: raise RuntimeError('CPU input audit failed; inspect private automatic-audit.log')
    output = json.loads(result.stdout.strip().splitlines()[-1], object_pairs_hook=unique_object)
    report_path = interior.school.bounded_path(Path(output['report']))
    report = interior.read(report_path)
    if report.get('status') != 'passed' or report.get('training_started') is not False:
        raise ValueError('Not a successful input-only audit')
    return {'path': str(report_path), 'sha256': digest(report_path)}


def cached_valid(entry, expected):
    try:
        bundle = Path(entry['bundle'])
        if verify_bundle(bundle) != expected: return False
        proof = entry['audit']; path = interior.school.bounded_path(Path(proof['path']))
        if digest(path) != proof['sha256']: return False
        report = interior.read(path)
        raw = interior.school.bounded_path(path.parent/'input.json').read_bytes()
        data = json.loads(raw, object_pairs_hook=unique_object)
        return (sha256(raw).hexdigest() == report['input_sha256'] and data == {'bundle': str(bundle), 'rows': expected}
                and report['status'] == 'passed' and report['training_started'] is False
                and [row['id'] for row in report['records']] == [row['id'] for row in expected])
    except (OSError, ValueError, KeyError, TypeError): return False


def cycle():
    previous = {}
    if (ROOT/'state.json').exists():
        previous = json.loads((ROOT/'state.json').read_text(), object_pairs_hook=unique_object)
    cache = previous.get('entries', {})
    entries, errors, skipped, accepted = {}, [], [], {}
    audits_started = 0
    discovered = sources()
    if len(discovered) > 500: raise ValueError('Review intake limit reached; split the collection explicitly')
    for kind, path in discovered:
        key = kind+':'+str(path)
        try:
            rows, export = collect(kind, path)
            if not rows:
                skipped.append({'source': key, 'reason': 'no_approved_train_records'}); continue
            if any(row['id'] in accepted for row in rows):
                raise ValueError('Duplicate approved example; not counted twice')
            entry = cache.get(key, {})
            if not cached_valid(entry, rows):
                if audits_started >= 2:
                    skipped.append({'source': key, 'reason': 'next_cycle_cpu_audit_limit'}); continue
                audits_started += 1
                bundle = export()
                if verify_bundle(bundle) != rows: raise ValueError('Export differs from approved input')
                entry = {'bundle': str(bundle), 'audit': audit(bundle)}
                if not cached_valid(entry, rows): raise ValueError('Audit does not bind this exact bundle')
            entries[key] = entry
            accepted.update({row['id']: row for row in rows})
        except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.TimeoutExpired) as exc:
            errors.append({'source': key, 'error_type': type(exc).__name__, 'detail': str(exc)[:240]})
    counts = {'train': len(accepted), 'validation': 0, 'test': 0}
    report = {'schema': 'learning-autopilot.v1', 'checked_at': datetime.now(timezone.utc).isoformat(),
              'phase': 'collecting_reviewed_data', 'counts': counts,
              'families': sorted({row['family'] for row in accepted.values()}),
              'minimums': MINIMUMS, 'missing': {key: max(0, value-counts[key]) for key, value in MINIMUMS.items()},
              'entries': entries, 'skipped': skipped, 'errors': errors,
              'training_started': False, 'automatic_weight_training_available': False,
              'model_promotion_enabled': False, 'production_changed': False,
              'next_requirements': ['broader independently reviewed training data',
                                    'registered separate validation and test data',
                                    'corpus trainer with matched baseline/adapter evaluation'],
              'limitation': 'Automatic intake and CPU input audits only. Counts cover this multimodal intake, '
                            'not every historical text dataset or evaluation suite. No automatic self-approval.'}
    save(ROOT/'state.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    if not args.once:
        print(json.dumps({'collection_started': False, 'training_started': False})); return 0
    if any(p.is_symlink() for p in (ROOT, *ROOT.parents)):
        raise ValueError('Non-symlink private workspace required')
    ROOT.mkdir(exist_ok=True)
    with (ROOT/'cycle.lock').open('a') as lock:
        try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({'status': 'another_cycle_holds_lock'})); return 0
        result = cycle()
    print(json.dumps({key: result[key] for key in ('phase', 'counts', 'missing', 'training_started')}, ensure_ascii=False))
    return 0 if not result['errors'] else 1


if __name__ == '__main__': raise SystemExit(main())
