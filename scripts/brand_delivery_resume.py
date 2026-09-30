"""Continue a frozen delivery exam after resource interruption, without retries of model failures.

Completed stages remain byte-bound to the original report. An interrupted art
stage may restart only if it made zero additional author calls. Earlier failed
model attempts retain their original result; no extra generation budget is added.
"""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import time

from scripts import brand_delivery_exam as exam
from scripts.brand_full_exam import exercise_context

CONTRACT = 'brand-delivery-resource-continuation.v1'
RESOURCE_ERRORS = {'active_containers', 'gpu_memory_unavailable', 'ollama_not_confirmed_idle', 'comfyui_busy_or_unknown'}


def bound(folder, report):
    for name, digest in report['artifacts'].items():
        p = exam.evidence.bounded(folder/name)
        if not p.resolve().is_relative_to(folder.resolve()) or exam.b.school.checksum(p) != digest:
            raise ValueError('Interrupted evidence changed')


def interrupted(source, *, require_live=False):
    read = exam.evidence.read
    report = read(source/'report.json'); frozen = read(source/'exam.json')
    strict = report.get('schema') == exam.STRICT_CONTRACT
    if (report.get('schema') not in (exam.CONTRACT, exam.STRICT_CONTRACT)
            or report.get('status') != 'failed' or report.get('error_type') != 'PreflightFailure'
            or report.get('error') not in RESOURCE_ERRORS or 'resource_continuation' in report
            or frozen != exam.manifest(frozen, strict=strict)
            or exam.b.school.checksum(source/'exam.json') != report['exam_sha256']):
        raise ValueError('One original frozen resource interruption required')
    bound(source, report)
    if [c['family'] for c in report['cases']] != [v['family'] for v in frozen['briefs'][:len(report['cases'])]]:
        raise ValueError('Original ordered case prefix required')
    if require_live:
        for name in exam.CODE + (('brand_background_review.py',) if strict else ()):
            live = Path(exam.__file__).parent/name if name != 'local_ollama.py' else Path(exam.__file__).parents[1]/'app/services/local_ollama.py'
            if live.read_bytes() != read_bytes(source/'implementation'/name):
                raise ValueError('Frozen implementation changed; cannot continue exam')
    return report, frozen, strict


def read_bytes(path):
    return exam.evidence.bounded(path).read_bytes()


def can_restart_art(outcome):
    folder = Path(outcome['artwork']); value = exam.evidence.read(folder/'report.json')
    origin = exam.evidence.read(folder/'repair-origin.json')
    bound(folder, value)
    if (exam.b.school.checksum(folder/'report.json') != outcome['artwork_report_sha256']
            or value.get('status') != 'failed' or value.get('error_type') != 'PreflightFailure'
            or value.get('error') not in RESOURCE_ERRORS or origin['repaired_stages']
            or outcome.get('text') is not None or outcome.get('candidate') is not None):
        raise ValueError('Only resource-stopped artwork with zero additional model calls may restart')
    source = Path(origin['source']); original, _, _, _, _ = exam.artwork.source_values(source)
    if exam.b.school.checksum(source/'report.json') != origin['source_report_sha256']:
        raise ValueError('Interrupted artwork source changed')
    # Every retained call must be an exact protected source copy.
    for p in folder.glob('*-request.json'):
        stage = p.name.removesuffix('-request.json')
        for suffix in ('request', 'response'):
            name = stage+'-'+suffix+'.json'
            if name not in original['artifacts'] or read_bytes(folder/name) != read_bytes(source/name):
                raise ValueError('Interrupted artwork contains additional inference')


def run(source):
    source = Path(source); original, frozen, strict = interrupted(source, require_live=True)
    resources = exam.b.school.check_idle()
    out = Path(tempfile.mkdtemp(prefix='delivery-resume-', dir=exam.b.ROOT))
    shutil.copyfile(source/'exam.json', out/'exam.json')
    shutil.copytree(source/'implementation', out/'implementation')
    shutil.copyfile(__file__, out/'continuation-implementation.py')
    report = deepcopy(original)
    for key in ('error', 'error_type', 'artifacts', 'elapsed_seconds'): report.pop(key, None)
    report.update(status='running', resources_before=resources,
        resource_continuation={'schema': CONTRACT, 'source': str(source),
            'source_report_sha256': exam.b.school.checksum(source/'report.json'),
            'zero_inference_restarts': [], 'previous_elapsed_seconds': original['elapsed_seconds']})
    started = time.monotonic()
    def save():
        report['elapsed_seconds'] = round(time.monotonic()-started, 3)
        report['artifacts'] = {str(p.relative_to(out)): exam.b.school.checksum(p) for p in out.rglob('*') if p.is_file() and p.name != 'report.json'}
        exam.b.school.save(out/'report.json', report)
    save(); print(json.dumps({'output': str(out)}), flush=True)
    try:
        for index, brief in enumerate(frozen['briefs']):
            if index < len(report['cases']):
                entry = report['cases'][index]; package_source = Path(entry['source'])
            else:
                with exercise_context(brief): package_source, _ = exam.b.run()
                entry = {'family': brief['family'], 'source': str(package_source),
                    'source_report_sha256': exam.b.school.checksum(package_source/'report.json'), 'arms': {}}
                report['cases'].append(entry)
                try: exam.artwork.source_values(package_source); entry['source_repairable'] = True
                except ValueError: entry['source_repairable'] = False
                save()
            if not entry['source_repairable']: continue
            for arm in (('baseline', 'deliberate') if index % 2 == 0 else ('deliberate', 'baseline')):
                if arm in entry['arms']:
                    prior = entry['arms'][arm]
                    if prior.get('candidate') is not None: continue
                    can_restart_art(prior)
                    report['resource_continuation']['zero_inference_restarts'].append({'family': entry['family'], 'arm': arm, 'original': deepcopy(prior)})
                package, art = exam.artwork.run(package_source, deliberate=exam.ARMS[arm], matched_budget=True, **({'strict_card': True} if strict else {}))
                outcome = {'artwork': str(package), 'artwork_report_sha256': exam.b.school.checksum(package/'report.json'),
                    'text': None, 'candidate': None, 'status': art['status']}
                entry['arms'][arm] = outcome; save()
                if art['status'] == 'pending_independent_visual_review':
                    exam.b.school.save(package/'verification.json', exam.evidence.verify(package))
                    folder, text = exam.text_repair.run(package, spatial='background' if strict else 'alignment', warm=True)
                    outcome.update(text=str(folder), text_report_sha256=exam.b.school.checksum(folder/'report.json'), status=text['status'])
                    if text['status'] == 'pending_independent_review':
                        exam.b.school.save(folder/'verification.json', exam.text_repair.verify(folder)); outcome['candidate'] = str(folder)
                    elif text['status'] == 'no_repair_requested':
                        exam.check_no_text_repair(folder, package, strict=strict); outcome['candidate'] = str(package)
                save(); print(json.dumps({'case': brief['restaurant_name'], 'arm': arm, **outcome}), flush=True)
        report.update(status='completed', technical_scores={a: sum(bool(c['arms'].get(a, {}).get('candidate')) for c in report['cases']) for a in exam.ARMS})
    except Exception as exc:
        report.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:600])
    finally: save()
    return out, report


def verify(out):
    out = Path(out); report = exam.evidence.read(out/'report.json'); record = report['resource_continuation']
    source = Path(record['source']); old, frozen, _ = interrupted(source)
    if (record['schema'] != CONTRACT or exam.b.school.checksum(source/'report.json') != record['source_report_sha256']
            or read_bytes(out/'exam.json') != read_bytes(source/'exam.json')
            or record['previous_elapsed_seconds'] != old['elapsed_seconds']):
        raise ValueError('Continuation origin changed')
    if {p.name for p in (out/'implementation').iterdir()} != {p.name for p in (source/'implementation').iterdir()}:
        raise ValueError('Frozen continuation implementation set changed')
    for p in (source/'implementation').iterdir():
        if read_bytes(out/'implementation'/p.name) != read_bytes(p):
            raise ValueError('Frozen continuation implementation changed')
    expected_restarts = []
    for old_case, new_case in zip(old['cases'], report['cases']):
        if {k: v for k, v in old_case.items() if k != 'arms'} != {k: v for k, v in new_case.items() if k != 'arms'}:
            raise ValueError('An earlier source was regenerated')
        for arm, outcome in old_case['arms'].items():
            if outcome.get('candidate') is not None:
                if new_case['arms'][arm] != outcome: raise ValueError('A completed stage was replaced')
            else:
                can_restart_art(outcome)
                expected_restarts.append({'family': old_case['family'], 'arm': arm, 'original': outcome})
    if record['zero_inference_restarts'] != expected_restarts:
        raise ValueError('Unbound extra restart')
    result = exam.verify(out, use_recorded_render=True)
    return result | {'resource_continuation_verified': True, 'earlier_sources_and_completed_arms_preserved': True,
        'interrupted_additional_model_calls': 0}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--resume', type=Path); group.add_argument('--verify', type=Path)
    args = parser.parse_args()
    if args.resume:
        out, report = run(args.resume)
        print(json.dumps({'output': str(out), 'status': report['status']}), flush=True)
        raise SystemExit(int(report['status'] != 'completed'))
    print(json.dumps(verify(args.verify), indent=2))
