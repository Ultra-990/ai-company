"""Fresh complete jobs with paired legacy/expanded metadata repair budgets.

Each fresh source is model-authored once and shared unchanged between the two
metadata arms. This paired design is explicit; arms are not independent source
generations. No manual hints, training exports or autonomous approval.
"""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import time

from scripts import brand_school as brand
from scripts import brand_guide_revision as revision

CONTRACT = 'brand-paired-workflow-exam.v1'
CASES = (
    {'id': 'cedar-lunch', 'name': 'Cedar Lunch',
     'concept': 'Fictional neighborhood lunch restaurant serving seasonal vegetable plates and grain bowls. Calm, accessible and fresh in visual tone; no luxury crests or fork/knife clip art.',
     'audience': 'Neighbors taking a relaxed midday break.'},
    {'id': 'copper-oven', 'name': 'Copper Oven',
     'concept': 'Fictional casual restaurant serving oven-baked vegetables and shared flatbreads. Warm, sociable and straightforward; no luxury crests or fork/knife clip art.',
     'audience': 'Friends and families sharing an informal evening meal.'},
    {'id': 'harbor-plate', 'name': 'Harbor Plate',
     'concept': 'Fictional harbor restaurant serving fish and vegetable suppers. Welcoming, relaxed and coastal; no luxury crests or fork/knife clip art.',
     'audience': 'Local adults and visitors meeting for a quiet supper.'},
)
ARMS = {'legacy': False, 'expanded': True}


def definition(case):
    if case not in CASES: raise ValueError('Frozen full workflow case required')
    brief = deepcopy(brand.DEFAULT_BRIEF); domain = case['id'].replace('-', '')+'.example'
    brief.update(restaurant_name=case['name'], family='brand-workflow-'+case['id'], split='test',
        concept=case['concept'], audience=case['audience'], qualification_exam=CONTRACT,
        contacts=['Reservations by email', 'hello@'+domain, domain])
    return brief


def run():
    from scripts import brand_full_exam as original_exam
    resources = brand.school.check_idle()
    out = Path(tempfile.mkdtemp(prefix='workflow-exam-', dir=brand.ROOT))
    config = brand.configuration()
    manifest = {'schema': CONTRACT, 'briefs': [definition(c) for c in CASES],
        'model': config['model'], 'digest': config['digest'], 'shared_original_per_pair': True,
        'generation_budget': {'num_ctx': 8192, 'num_predict': 4096, 'num_thread': 4, 'timeout_seconds': 180},
        'repair_budget': {'num_ctx': 8192, 'num_predict': 1800, 'num_thread': 4, 'timeout_seconds': 90},
        'max_calls_per_generation_stage': 3, 'max_metadata_calls_per_arm': 3,
        'manual_hints_allowed': False, 'training_export_allowed': False}
    brand.school.save(out/'exam.json', manifest)
    code = out/'implementation'; code.mkdir()
    for name in ('brand_school.py', 'brand_full_exam.py', 'brand_workflow_exam.py', 'brand_guide_revision.py',
                 'brand_plan_review.py', 'verify_brand_package.py', 'render_school_svg.py',
                 'vector_structured_source.py', 'vector_school_contract.py'):
        shutil.copyfile(Path(__file__).parent/name, code/name)
    shutil.copyfile(Path(__file__).resolve().parents[1]/'app/services/local_ollama.py', code/'local_ollama.py')
    report = {'schema': CONTRACT, 'status': 'running', 'resources_before': resources,
        'exam_sha256': brand.school.checksum(out/'exam.json'), 'cases': [],
        'training_exported': False, 'autonomy_qualified': False, 'independent_review_required': True}
    started = time.monotonic()
    def save():
        report['elapsed_seconds'] = round(time.monotonic()-started, 3)
        report['artifacts'] = {str(p.relative_to(out)): brand.school.checksum(p)
            for p in out.rglob('*') if p.is_file() and p.name != 'report.json'}
        brand.school.save(out/'report.json', report)
    save(); print(json.dumps({'output': str(out)}), flush=True)
    try:
        for index, brief in enumerate(manifest['briefs']):
            with original_exam.exercise_context(brief):
                source, generated = brand.run()
            entry = {'family': brief['family'], 'source': str(source),
                'source_report_sha256': brand.school.checksum(source/'report.json'), 'arms': {}}
            report['cases'].append(entry); save()
            if generated['status'] != 'pending_independent_visual_review': continue
            revision.evidence.verify(source)
            for arm in (('legacy', 'expanded') if index % 2 == 0 else ('expanded', 'legacy')):
                package, result = revision.run(source, expanded=ARMS[arm])
                candidate = None
                if result['status'] == 'pending_independent_review':
                    brand.school.save(package/'verification.json', revision.verify(package)); candidate = str(package)
                elif result['status'] == 'no_repair_requested': candidate = str(source)
                entry['arms'][arm] = {'revision': str(package), 'report_sha256': brand.school.checksum(package/'report.json'),
                    'candidate': candidate, 'status': result['status'], 'elapsed_seconds': result['elapsed_seconds']}
                save(); print(json.dumps({'case': brief['restaurant_name'], 'arm': arm, **entry['arms'][arm]}), flush=True)
        report['status'] = 'completed'
        report['technical_scores'] = {a: sum(bool(c['arms'].get(a, {}).get('candidate')) for c in report['cases']) for a in ARMS}
    except Exception as exc:
        report.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:600])
    finally: save()
    print(json.dumps({'report': str(out/'report.json'), 'status': report['status'], 'technical_scores': report.get('technical_scores')}), flush=True)
    return out, report


def verify(out):
    out = Path(out); read = revision.evidence.read; checksum = brand.school.checksum
    report = read(out/'report.json'); manifest = read(out/'exam.json')
    expected = {'schema': CONTRACT, 'briefs': [definition(c) for c in CASES],
        'model': manifest['model'], 'digest': manifest['digest'], 'shared_original_per_pair': True,
        'generation_budget': {'num_ctx': 8192, 'num_predict': 4096, 'num_thread': 4, 'timeout_seconds': 180},
        'repair_budget': {'num_ctx': 8192, 'num_predict': 1800, 'num_thread': 4, 'timeout_seconds': 90},
        'max_calls_per_generation_stage': 3, 'max_metadata_calls_per_arm': 3,
        'manual_hints_allowed': False, 'training_export_allowed': False}
    if (report.get('schema') != CONTRACT or report.get('status') != 'completed' or manifest != expected
            or report['exam_sha256'] != checksum(out/'exam.json') or report.get('autonomy_qualified') is not False
            or report.get('training_exported') is not False or [c['family'] for c in report['cases']] != [b['family'] for b in expected['briefs']]):
        raise ValueError('Complete frozen paired workflow required')
    def bound(root, value):
        for name, digest in value['artifacts'].items():
            p = revision.evidence.bounded(root/name)
            if not p.resolve().is_relative_to(root.resolve()) or checksum(p) != digest: raise ValueError('Workflow artifact changed')
    def same_code(root, names):
        for name in names:
            if revision.evidence.bounded(root/'implementation'/name).read_bytes() != revision.evidence.bounded(out/'implementation'/name).read_bytes():
                raise ValueError('Code changed during paired workflow')
    bound(out, report); seen = set(); scores = dict.fromkeys(ARMS, 0)
    for case, brief in zip(report['cases'], expected['briefs']):
        source = Path(case['source']); original = read(source/'report.json')
        if (source.resolve() in seen or original['brief'] != brief or checksum(source/'report.json') != case['source_report_sha256']
                or (original['model'], original['digest']) != (manifest['model'], manifest['digest'])
                or any(original['config'][k] != v for k, v in manifest['generation_budget'].items())):
            raise ValueError('Independent fresh source with frozen generation budget required')
        seen.add(source.resolve()); bound(source, original)
        same_code(source, ('brand_school.py', 'render_school_svg.py', 'vector_structured_source.py', 'vector_school_contract.py', 'local_ollama.py'))
        if (original['status'] not in ('pending_independent_visual_review', 'failed', 'needs_revision')
                or not 1 <= len(list(source.glob('*-request.json'))) <= 15
                or original['config'].get('sampling_profile', 'bounded-default.v1') != 'bounded-default.v1'
                or original['config'].get('think', False) is not False):
            raise ValueError('Bounded terminal baseline source required')
        if original['status'] != 'pending_independent_visual_review':
            if case['arms']: raise ValueError('No repair of an incomplete source allowed')
            continue
        revision.evidence.verify(source)
        if set(case['arms']) != set(ARMS): raise ValueError('Both paired metadata arms required')
        for arm, outcome in case['arms'].items():
            folder = Path(outcome['revision']); value = read(folder/'report.json')
            if (folder.resolve() in seen or checksum(folder/'report.json') != outcome['report_sha256']
                    or Path(value['package']).resolve() != source.resolve() or value['source_report_sha256'] != case['source_report_sha256']
                    or value['status'] != outcome['status'] or value['max_model_calls'] != 3
                    or (value['model'], value['digest']) != (manifest['model'], manifest['digest'])
                    or any(value['config'][k] != v for k, v in manifest['repair_budget'].items())
                    or value['config']['sampling_profile'] != 'bounded-default.v1' or value['config']['think'] is not False
                    or value.get('review_contract') != ('brand-plan-factual-review.v2' if ARMS[arm] else None)
                    or len(list(folder.glob('*-request.json'))) > 3):
                raise ValueError('Matched bounded metadata arm required')
            seen.add(folder.resolve()); bound(folder, value)
            names = ['brand_guide_revision.py', 'brand_school.py', 'verify_brand_package.py', 'local_ollama.py']
            if ARMS[arm]: names.append('brand_plan_review.py')
            same_code(folder, names)
            candidate = None
            if value['status'] == 'pending_independent_review': revision.verify(folder); candidate = str(folder)
            elif value['status'] == 'no_repair_requested':
                original_report, data = revision.inputs(source)
                protocol = revision
                if ARMS[arm]:
                    from scripts import brand_plan_review as protocol
                    data = protocol.expand(data, source)
                if read(folder/'review-request.json') != {'system': protocol.REVIEW_SYSTEM, 'user': json.dumps(data), 'format': protocol.REVIEW_SCHEMA}:
                    raise ValueError('Unchanged factual review required')
                response = read(folder/'review-response.json')
                if (response['model'], response['digest']) != (manifest['model'], manifest['digest']): raise ValueError('Reviewer changed')
                reviewed = protocol.review_value(response['content'])
                if reviewed != read(folder/'review.json') or any(r['verdict'] != 'supported' for r in reviewed['reviews']): raise ValueError('Unrepaired source has unresolved findings')
                if {p.name for p in folder.glob('*-request.json')} != {'review-request.json'}: raise ValueError('Extra call after no-repair verdict')
                candidate = str(source)
            elif value['status'] not in ('failed', 'needs_revision'): raise ValueError('Terminal metadata outcome required')
            if candidate != outcome['candidate']: raise ValueError('Candidate substitution')
            scores[arm] += bool(candidate)
    if scores != report['technical_scores']: raise ValueError('Paired workflow score changed')
    return {'schema': CONTRACT, 'report_sha256': checksum(out/'report.json'), 'technical_scores': scores,
        'shared_original_per_pair': True, 'independent_review_required': True, 'autonomy_qualified': False}
