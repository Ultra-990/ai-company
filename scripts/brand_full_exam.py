"""Frozen full restaurant identity comparison; no training or manual revisions."""
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import brand_school as brand

CONTRACT = 'brand-full-package-exam.v1'
CASES = (
    {'id': 'tide-hearth', 'name': 'Tide & Hearth',
     'concept': 'Fictional casual harbor restaurant serving fish and vegetable suppers. Calm, welcoming and coastal without luxury crests or generic fork/knife clip art.',
     'audience': 'Local adults and visitors meeting for an unhurried evening meal.'},
    {'id': 'ember-yard', 'name': 'Ember Yard',
     'concept': 'Fictional neighborhood restaurant serving wood-fired vegetables and flatbreads. Bold, sociable and straightforward without luxury crests or generic fork/knife clip art.',
     'audience': 'Friends and families sharing informal evening meals.'},
    {'id': 'willow-breakfast', 'name': 'Willow Breakfast',
     'concept': 'Fictional daytime restaurant serving breakfast and seasonal plant-forward lunches. Bright, approachable and relaxed without luxury crests or generic fork/knife clip art.',
     'audience': 'Neighbors meeting for breakfast or a leisurely lunch.'},
)
ARMS = {'baseline': 'bounded-default.v1', 'deliberate': 'qwen-deliberate-trial.v1'}


def definition(case):
    if case not in CASES: raise ValueError('Frozen brand case required')
    brief = deepcopy(brand.DEFAULT_BRIEF)
    domain = case['id'].replace('-', '')+'.example'
    brief.update(restaurant_name=case['name'], family='brand-exam-'+case['id'], split='test',
        concept=case['concept'], audience=case['audience'], qualification_exam=CONTRACT,
        contacts=['Reservations by email', 'hello@'+domain, domain])
    return brief


@contextmanager
def exercise_context(brief):
    if brief != brand.DEFAULT_BRIEF and brief not in [definition(c) for c in CASES]:
        from scripts import brand_workflow_exam as workflow
        if brief not in [workflow.definition(c) for c in workflow.CASES]:
            from scripts import brand_delivery_exam as delivery
            if brief not in ([delivery.definition(c) for c in delivery.CASES]
                             + [delivery.definition(c, strict=True) for c in delivery.STRICT_CASES]
                             + [delivery.definition(c, complete=True) for c in delivery.COMPLETE_CASES]):
                raise ValueError('Known frozen synthetic brand brief required')
    previous = brand.BRIEF
    brand.BRIEF = deepcopy(brief)
    try: yield
    finally: brand.BRIEF = previous


def run():
    from scripts import verify_brand_package as verifier
    resources = brand.school.check_idle()
    out = Path(tempfile.mkdtemp(prefix='brand-exam-', dir=brand.ROOT))
    cfg = brand.configuration()
    manifest = {'schema': CONTRACT, 'cases': [definition(c) for c in CASES], 'arms': ARMS,
        'model': cfg['model'], 'digest': cfg['digest'], 'manual_hints_allowed': False,
        'continuations_allowed': False, 'training_export_allowed': False,
        'shared_budget': {'num_ctx': 16384, 'num_predict': 8192, 'num_thread': 4,
                          'timeout_seconds': 180, 'max_calls_per_stage': 3, 'max_stages': 5}}
    brand.school.save(out/'exam.json', manifest)
    implementation = out/'implementation'; implementation.mkdir()
    for name in ('brand_full_exam.py', 'verify_brand_package.py', 'brand_school.py', 'render_school_svg.py',
                 'vector_structured_source.py', 'vector_school_contract.py'):
        shutil.copyfile(Path(__file__).parent/name, implementation/name)
    shutil.copyfile(Path(__file__).resolve().parents[1]/'app/services/local_ollama.py', implementation/'local_ollama.py')
    report = {'schema': CONTRACT, 'status': 'running', 'cases': [], 'resources_before': resources,
        'exam_sha256': brand.school.checksum(out/'exam.json'), 'training_exported': False,
        'production_changed': False, 'autonomy_qualified': False, 'independent_visual_review_required': True}
    started = time.monotonic()
    def save():
        report['elapsed_seconds'] = round(time.monotonic()-started, 3)
        report['artifacts'] = {str(p.relative_to(out)): brand.school.checksum(p)
            for p in out.rglob('*') if p.is_file() and p.name != 'report.json'}
        brand.school.save(out/'report.json', report)
    save(); print(json.dumps({'output': str(out)}), flush=True)
    try:
        for index, brief in enumerate(manifest['cases']):
            entry = {'family': brief['family'], 'arms': {}}; report['cases'].append(entry)
            with exercise_context(brief):
                for arm in (('baseline', 'deliberate') if index % 2 == 0 else ('deliberate', 'baseline')):
                    package, result = brand.run(sampling_profile=ARMS[arm], matched_exam_budget=True)
                    if ((result['model'], result['digest']) != (manifest['model'], manifest['digest'])
                            or any(result['config'][k] != manifest['shared_budget'][k]
                                   for k in ('num_ctx', 'num_predict', 'num_thread', 'timeout_seconds'))):
                        raise ValueError('Matched brand model or budget changed')
                    passed = result['status'] == 'pending_independent_visual_review'
                    if passed: brand.school.save(package/'verification.json', verifier.verify(package))
                    entry['arms'][arm] = {'package': str(package), 'report_sha256': brand.school.checksum(package/'report.json'),
                        'technical_pass': passed, 'elapsed_seconds': result['elapsed_seconds'], 'error': result.get('error')}
                    save(); print(json.dumps({'case': brief['restaurant_name'], 'arm': arm, **entry['arms'][arm]}), flush=True)
        report.update(status='completed', scores={a: sum(c['arms'][a]['technical_pass'] for c in report['cases']) for a in ARMS})
    except Exception as exc:
        report.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:600])
    finally: save()
    print(json.dumps({'report': str(out/'report.json'), 'status': report['status'], 'scores': report.get('scores')}), flush=True)
    return out, report


def assess(folder):
    from scripts import verify_brand_package as verifier
    folder = Path(folder); read = verifier.read; checksum = brand.school.checksum
    report, manifest = read(folder/'report.json'), read(folder/'exam.json')
    if (report.get('schema') != CONTRACT or report.get('status') != 'completed'
            or manifest.get('schema') != CONTRACT or manifest.get('cases') != [definition(c) for c in CASES]
            or manifest.get('arms') != ARMS or checksum(folder/'exam.json') != report['exam_sha256']
            or any(manifest.get(k) is not False for k in ('manual_hints_allowed', 'continuations_allowed', 'training_export_allowed'))
            or manifest['shared_budget'] != {'num_ctx': 16384, 'num_predict': 8192, 'num_thread': 4,
                'timeout_seconds': 180, 'max_calls_per_stage': 3, 'max_stages': 5}
            or [c['family'] for c in report['cases']] != [c['family'] for c in manifest['cases']]):
        raise ValueError('Unchanged completed frozen brand exam required')
    def bound(root, value):
        for name, digest in value['artifacts'].items():
            path = verifier.bounded(root/name)
            if not path.resolve().is_relative_to(root.resolve()) or checksum(path) != digest:
                raise ValueError('Exam or candidate artifact changed')
    bound(folder, report); scores = {a: 0 for a in ARMS}; seen = set()
    for case, brief in zip(report['cases'], manifest['cases']):
        if set(case['arms']) != set(ARMS): raise ValueError('Both brand arms required')
        for arm, outcome in case['arms'].items():
            package = Path(outcome['package']); value = read(package/'report.json')
            if (package.resolve() in seen or checksum(package/'report.json') != outcome['report_sha256']
                    or value['brief'] != brief or (value['model'], value['digest']) != (manifest['model'], manifest['digest'])
                    or value['config'].get('sampling_profile') != ARMS[arm]
                    or value['config'].get('think') is not (arm == 'deliberate')
                    or any(value['config'][k] != manifest['shared_budget'][k] for k in ('num_ctx', 'num_predict', 'num_thread', 'timeout_seconds'))
                    or any(k in value for k in ('inherited_stages', 'resumed_from', 'recomposed_from'))):
                raise ValueError('Independent matched brand execution required')
            seen.add(package.resolve()); bound(package, value)
            for name in ('brand_school.py', 'render_school_svg.py', 'vector_structured_source.py', 'vector_school_contract.py', 'local_ollama.py'):
                if verifier.bounded(package/'implementation'/name).read_bytes() != verifier.bounded(folder/'implementation'/name).read_bytes():
                    raise ValueError('Brand implementation changed during comparison')
            passed = value['status'] == 'pending_independent_visual_review'
            if value['status'] not in ('pending_independent_visual_review', 'needs_revision', 'failed') or outcome['technical_pass'] is not passed:
                raise ValueError('Brand technical outcome changed')
            if not 1 <= len(list(package.glob('*-request.json'))) <= 15:
                raise ValueError('Brand call budget changed')
            if passed: verifier.verify(package)
            scores[arm] += int(passed)
    if scores != report['scores']: raise ValueError('Brand score changed')
    return {'schema': CONTRACT, 'report_sha256': checksum(folder/'report.json'), 'integrity_verified': True,
        'technical_scores': scores, 'independent_visual_review_required': True, 'autonomy_qualified': False,
        'training_exported': False}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(); actions.add_argument('--run', action='store_true'); actions.add_argument('--assess', type=Path)
    args = parser.parse_args()
    if args.run:
        _, report = run(); raise SystemExit(int(report['status'] != 'completed'))
    elif args.assess: print(json.dumps(assess(args.assess), indent=2))
    else: print(json.dumps({'cases': [definition(c) for c in CASES], 'model_called': False}))
