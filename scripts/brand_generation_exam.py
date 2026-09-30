"""Fresh complete jobs comparing profiles at generation, with common downstream checks."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import time
from scripts import brand_delivery_exam as delivery
from scripts import brand_reference_review as protocol
from scripts import brand_generation_audit as audit

b, art, text, evidence = delivery.b, delivery.artwork, delivery.text_repair, delivery.evidence
CONTRACT = 'brand-generation-delivery-exam.v1'
LITERAL_CONTRACT = 'brand-generation-delivery-exam.v2'
ARMS = {'baseline': 'bounded-default.v1', 'deliberate': 'qwen-deliberate-trial.v1'}
CASES = (
    {'id': 'cinder-corner', 'name': 'Cinder Corner',
     'concept': 'Fictional neighborhood restaurant serving grilled vegetables, beans and flatbreads. Warm and sociable, with a restrained flame or hearth motif; no luxury crests or fork/knife clip art.',
     'audience': 'Neighbors and friends sharing casual evening meals.'},
    {'id': 'reed-bay', 'name': 'Reed Bay',
     'concept': 'Fictional riverside lunch room serving fish, rice and vegetable plates. Calm and approachable, with a restrained reed or water motif; no luxury crests or fork/knife clip art.',
     'audience': 'Local workers and walkers stopping for an informal lunch.'},
    {'id': 'pear-common', 'name': 'Pear Common',
     'concept': 'Fictional daytime restaurant serving orchard-fruit breakfasts, soups and warm sandwiches. Welcoming and practical, with a restrained pear or branch motif; no luxury crests or fork/knife clip art.',
     'audience': 'Families and neighbors gathering for relaxed breakfast or lunch.'},
)
BUDGET = {'num_ctx': 16384, 'num_predict': 8192, 'num_thread': 4, 'timeout_seconds': 180}
LITERAL_CASES = (
    {'id': 'poppy-wharf', 'name': 'Poppy Wharf',
     'concept': 'Fictional waterside cafe serving seed bread, soup and fresh vegetable bowls. Friendly and practical, with a restrained seed or water motif; no luxury crests or fork/knife clip art.',
     'audience': 'Local residents and visitors stopping for a relaxed lunch.'},
    {'id': 'olive-bench', 'name': 'Olive Bench',
     'concept': 'Fictional neighborhood restaurant serving roasted vegetables, fish and warm flatbread. Calm and welcoming, with a restrained olive or branch motif; no luxury crests or fork/knife clip art.',
     'audience': 'Neighbors and small groups sharing informal evening meals.'},
    {'id': 'juniper-hearth', 'name': 'Juniper Hearth',
     'concept': 'Fictional small restaurant serving baked roots, mushroom soup and grain plates. Warm and approachable, with a restrained juniper or hearth motif; no luxury crests or fork/knife clip art.',
     'audience': 'Local families and workers gathering for an unhurried meal.'},
)
V2_REVIEW_FILES = {'brand_spatial_subject_review.py', 'brand_composed_review.py',
                   'brand_constrained_review.py', 'brand_literal_review.py',
                   'brand_compact_review.py'}


def review_protocol(literal=False):
    if literal:
        from scripts import brand_compact_review
        return brand_compact_review
    return protocol


def definition(case, *, literal=False):
    if case not in (LITERAL_CASES if literal else CASES): raise ValueError('Frozen generation-comparison case required')
    result = deepcopy(b.DEFAULT_BRIEF); domain = case['id'].replace('-', '')+'.example'
    result.update(restaurant_name=case['name'], family=('brand-generation-v2-' if literal else 'brand-generation-v1-')+case['id'],
        split='test', concept=case['concept'], audience=case['audience'], qualification_exam=LITERAL_CONTRACT if literal else CONTRACT,
        contacts=['Reservations by email', 'hello@'+domain, domain])
    return result


def manifest(config, *, literal=False):
    return {'schema': LITERAL_CONTRACT if literal else CONTRACT,
        'briefs': [definition(c, literal=literal) for c in (LITERAL_CASES if literal else CASES)], 'profiles': ARMS,
        'model': config['model'], 'digest': config['digest'], 'generation_budget': BUDGET,
        'artwork_budget': BUDGET, 'artwork_profile': ARMS['baseline'], 'text_budget': delivery.TEXT,
        'max_generation_calls': 15, 'max_artwork_calls': 9, 'max_text_calls': 5,
        'source_contract': 'brand-scoped-scene.v1', 'visibility_contract': art.SOURCE_VISIBLE_CONTRACT,
        'artwork_contract': art.VISIBLE_CONTRACT, 'text_contract': review_protocol(literal).CONTRACT,
        'independent_source_per_arm': True, 'manual_hints_allowed': False, 'training_export_allowed': False}


def run(*, literal=False):
    from scripts.brand_full_exam import exercise_context
    resources = b.school.check_idle(); frozen = manifest(b.configuration(), literal=literal)
    out = Path(tempfile.mkdtemp(prefix='generation-exam-', dir=b.ROOT))
    b.school.save(out/'exam.json', frozen); code = out/'implementation'; code.mkdir()
    files = set(delivery.implementation_files(complete=True)) | {'brand_generation_exam.py', 'brand_reference_review.py', 'brand_generation_audit.py'}
    if literal: files |= V2_REVIEW_FILES
    for name in sorted(files):
        path = Path(__file__).parent/name if name != 'local_ollama.py' else Path(__file__).parents[1]/'app/services/local_ollama.py'
        shutil.copyfile(path, code/name)
    report = {'schema': frozen['schema'], 'status': 'running', 'resources_before': resources,
        'exam_sha256': b.school.checksum(out/'exam.json'), 'cases': [], 'training_exported': False,
        'production_changed': False, 'autonomy_qualified': False}
    started = time.monotonic()
    def save():
        report['elapsed_seconds'] = round(time.monotonic()-started, 3)
        report['artifacts'] = {str(p.relative_to(out)): b.school.checksum(p)
            for p in out.rglob('*') if p.is_file() and p.name != 'report.json'}
        b.school.save(out/'report.json', report)
    save(); print(json.dumps({'output': str(out)}), flush=True)
    try:
        for index, brief in enumerate(frozen['briefs']):
            case = {'family': brief['family'], 'arms': {}}; report['cases'].append(case)
            for arm in (('baseline', 'deliberate') if index % 2 == 0 else ('deliberate', 'baseline')):
                with exercise_context(brief):
                    source, original = b.run(sampling_profile=ARMS[arm], matched_exam_budget=True, visible_shapes=True)
                outcome = {'source': str(source), 'source_report_sha256': b.school.checksum(source/'report.json'),
                    'artwork': None, 'text': None, 'candidate': None, 'status': original['status']}
                case['arms'][arm] = outcome; save()
                try: art.source_values(source)
                except ValueError: outcome['source_repairable'] = False
                else:
                    outcome['source_repairable'] = True
                    package, result = art.run(source, matched_budget=True, visible_shapes=True)
                    outcome.update(artwork=str(package), artwork_report_sha256=b.school.checksum(package/'report.json'), status=result['status'])
                    if result['status'] == 'pending_independent_visual_review':
                        b.school.save(package/'verification.json', evidence.verify(package))
                        folder, result = text.run(package, spatial='compact' if literal else 'reference', warm=True)
                        outcome.update(text=str(folder), text_report_sha256=b.school.checksum(folder/'report.json'), status=result['status'])
                        if result['status'] == 'pending_independent_review':
                            b.school.save(folder/'verification.json', text.verify(folder)); outcome['candidate'] = str(folder)
                        elif result['status'] == 'no_repair_requested':
                            b.school.save(folder/'verification.json', text.verify_review_only(folder)); outcome['candidate'] = str(package)
                save(); print(json.dumps({'case': brief['restaurant_name'], 'arm': arm, **outcome}), flush=True)
        report.update(status='completed', technical_scores={a: sum(bool(c['arms'][a]['candidate']) for c in report['cases']) for a in ARMS})
    except Exception as exc:
        report.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:600])
    finally: save()
    print(json.dumps({'output': str(out), 'status': report['status'], 'technical_scores': report.get('technical_scores')}), flush=True)
    return out, report


def verify(out):
    out = Path(out); read, checksum = evidence.read, b.school.checksum
    report, frozen = read(out/'report.json'), read(out/'exam.json')
    literal = report.get('schema') == LITERAL_CONTRACT
    selected_protocol = review_protocol(literal)
    if (report.get('schema') not in (CONTRACT, LITERAL_CONTRACT) or report.get('status') != 'completed'
            or frozen != manifest(frozen, literal=literal) or checksum(out/'exam.json') != report['exam_sha256']
            or any(report.get(k) is not False for k in ('training_exported', 'production_changed', 'autonomy_qualified'))
            or [c['family'] for c in report['cases']] != [c['family'] for c in frozen['briefs']]):
        raise ValueError('Complete frozen generation comparison required')
    seen = set()
    def bound(folder, value):
        for name, digest in value['artifacts'].items():
            path = evidence.bounded(folder/name)
            if not path.resolve().is_relative_to(folder.resolve()) or checksum(path) != digest:
                raise ValueError('Generation comparison evidence changed')
    def stage(path, digest, budget, profile, think, kind):
        folder = Path(path); value = read(folder/'report.json')
        if folder.resolve() in seen or checksum(folder/'report.json') != digest:
            raise ValueError('Independent unchanged sources and stages required')
        seen.add(folder.resolve()); bound(folder, value)
        if ((value['model'], value['digest']) != (frozen['model'], frozen['digest'])
                or (value['config'].get('model'), value['config'].get('digest')) != (frozen['model'], frozen['digest'])
                or any(value['config'].get(k) != v for k, v in budget.items())
                or value['config'].get('sampling_profile') != profile or value['config'].get('think') is not think):
            raise ValueError('Equal budgets and pinned declared profiles required')
        files = list((folder/'implementation').iterdir())
        required = audit.IMPLEMENTATION[kind]
        if literal and kind == 'text': required = required | V2_REVIEW_FILES
        if ({p.name for p in files} != required or
                {name.removeprefix('implementation/') for name in value['artifacts'] if name.startswith('implementation/')} != required):
            raise ValueError('Complete contract-specific implementation snapshot required')
        for file in files:
            if file.read_bytes() != evidence.bounded(out/'implementation'/file.name).read_bytes():
                raise ValueError('Implementation changed during generation comparison')
        return folder, value
    bound(out, report); scores = dict.fromkeys(ARMS, 0); audited = []
    for case, brief in zip(report['cases'], frozen['briefs']):
        if set(case['arms']) != set(ARMS): raise ValueError('Both independently generated arms required')
        for arm, outcome in case['arms'].items():
            source, original = stage(outcome['source'], outcome['source_report_sha256'], BUDGET, ARMS[arm], arm == 'deliberate', 'source')
            if (original['brief'] != brief or original.get('scene_contract') != frozen['source_contract']
                    or original.get('visibility_contract') != frozen['visibility_contract']
                    or original.get('status') not in ('failed', 'needs_revision', 'pending_independent_visual_review')
                    or any(k in original for k in ('repair_contract', 'scene_recovery_contract'))
                    or not 1 <= len(list(source.glob('*-request.json'))) <= 15):
                raise ValueError('Fresh visible source with bounded attempts required')
            checked = {'family': brief['family'], 'arm': arm, 'source': audit.source(source, original)}
            audited.append(checked)
            try: art.source_values(source); eligible = True
            except ValueError: eligible = False
            if original['status'] == 'pending_independent_visual_review' and not eligible:
                raise ValueError('Completed source evidence failed independent verification')
            if outcome['source_repairable'] is not eligible: raise ValueError('Source eligibility changed')
            candidate = None; status = original['status']
            if eligible:
                package, result = stage(outcome['artwork'], outcome['artwork_report_sha256'], BUDGET, ARMS['baseline'], False, 'artwork')
                origin = read(package/'repair-origin.json')
                if (result['brief'] != brief or result['repair_contract'] != art.VISIBLE_CONTRACT or origin.get('schema') != art.VISIBLE_CONTRACT
                        or Path(origin['source']).resolve() != source.resolve() or origin['source_report_sha256'] != outcome['source_report_sha256']
                        or origin['max_additional_model_calls'] != 9 or origin['fresh_exam'] is not False):
                    raise ValueError('Common bounded downstream artwork stage required')
                checked['artwork'] = audit.artwork(package, result, source)
                status = result['status']
                if status == 'pending_independent_visual_review':
                    evidence.verify(package)
                    folder, result = stage(outcome['text'], outcome['text_report_sha256'], delivery.TEXT, ARMS['baseline'], False, 'text')
                    if (Path(result['package']).resolve() != package.resolve() or result['source_report_sha256'] != outcome['artwork_report_sha256']
                            or result['review_contract'] != selected_protocol.CONTRACT or result['max_model_calls'] != 5):
                        raise ValueError('Common bounded downstream text stage required')
                    checked['text'] = audit.guide(folder, result, package, protocol=selected_protocol)
                    status = result['status']
                    if status == 'pending_independent_review':
                        text.verify(folder, use_recorded_render=True); candidate = str(folder)
                    elif status == 'no_repair_requested':
                        delivery.check_no_text_repair(folder, package, protocol=selected_protocol)
                        _, data = text.inputs(package)
                        text.recorded_render(folder, package, selected_protocol.expand(data, package)); candidate = str(package)
                    elif status not in ('failed', 'needs_revision'): raise ValueError('Terminal text stage required')
                elif status not in ('failed', 'needs_revision') or outcome['text'] is not None:
                    raise ValueError('Terminal artwork stage required')
            elif outcome['artwork'] is not None or outcome['text'] is not None:
                raise ValueError('Unusable source cannot enter downstream stages')
            if outcome['candidate'] != candidate or outcome['status'] != status:
                raise ValueError('Generation comparison outcome changed')
            scores[arm] += int(candidate is not None)
    if report['technical_scores'] != scores: raise ValueError('Generation comparison score changed')
    return {'schema': frozen['schema'], 'report_sha256': checksum(out/'report.json'), 'technical_scores': scores,
        'post_run_audit': {'schema': audit.CONTRACT, 'stages': audited,
            'auditor_implementation_sha256': {Path(__file__).name: checksum(Path(__file__)),
                Path(audit.__file__).name: checksum(Path(audit.__file__))},
            'scope': 'Literal requests, model identity, bounded terminal chains and recorded-validator replay; no protection against coordinated rewriting of all evidence and hashes.'},
        'independent_sources': len(report['cases'])*2, 'render_evidence': 'verified_previous_independent_renders',
        'independent_review_required': True, 'autonomy_qualified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--run', action='store_true'); action.add_argument('--literal-exam', action='store_true'); action.add_argument('--verify', type=Path)
    args = parser.parse_args()
    if args.verify: print(json.dumps(verify(args.verify), indent=2))
    else:
        _, result = run(literal=args.literal_exam); raise SystemExit(int(result['status'] != 'completed'))
