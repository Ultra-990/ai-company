"""Complete product delivery with bounded factual headline repair and assembly.

The final package remains pending independent visual/semantic review. Known
source completion never changes a historical exam, exports training data or
claims fresh qualification. Every creative change is a literal local answer.
"""
from copy import deepcopy
from pathlib import Path
import json
import shutil
import tempfile
import time

from scripts import product_headline_repair as repair
from scripts import product_revised_package as assembly

probe, product = repair.probe, repair.product
CONTRACT = 'product-complete-delivery-workflow.v1'
BUDGET = {'initial_review': 1, 'panels': 4, 'writer_calls_per_panel': 3,
    'reviewer_calls_per_panel': 3, 'final_review': 1, 'maximum_headline_calls': 26,
    'maximum_generation_calls': 18}


def binding(folder):
    folder = Path(folder)
    return {'directory': str(folder), 'report_sha256': product.school.checksum(probe.revision.bounded(folder/'report.json'))}


def bound(value):
    folder = Path(value['directory'])
    if binding(folder) != value: raise ValueError('Child stage report changed')
    return folder


def selected_data(package, review_folder, repair_folder=None):
    original, data, initial = repair.review_inputs(Path(package), Path(review_folder))
    initial_report = probe.revision.read(Path(review_folder)/'report.json')
    limits = {'sampling_profile': 'bounded-default.v1', 'think': False,
        'num_ctx': 8192, 'num_predict': 2048, 'num_thread': 4, 'timeout_seconds': 90}
    if initial_report.get('max_model_calls') != 1 or any(initial_report['config'].get(k) != v for k, v in limits.items()):
        raise ValueError('Initial review must retain its frozen one-call configuration')
    selected = deepcopy(data)
    if repair_folder is not None:
        folder = Path(repair_folder); repair.verify(folder)
        report = probe.revision.read(folder/'report.json')
        if (report.get('max_writer_calls_per_panel') != 3 or report.get('max_reviewer_calls_per_panel') != 3
                or any(report['config'].get(k) != v for k, v in (limits | {'num_predict': 512}).items())):
            raise ValueError('Repair must retain existing per-panel budgets and configuration')
        if Path(report['package']).resolve() != Path(package).resolve():
            raise ValueError('Repair belongs to a different complete package')
        for entry in report['panels']:
            scene = probe.revision.read(folder/entry['panel']/'accepted-scene.json')
            next(row for row in selected['panels'] if row['panel'] == entry['panel'])['headline'] = scene['texts'][0]['text']
    return original, selected, initial


def final_review(out, data, config):
    raw = product.brand.call(out, 'final-review', probe.SYSTEM, json.dumps(data), probe.schema(), config)
    value = probe.validate(raw, data)
    product.school.save(out/'final-review.json', value)
    return value


def call_counts(out, report):
    generated = report.get('generated_here', False)
    source = bound(report['source']) if report.get('source') else None
    counts = {'generation': len(list(source.glob('*-request.json'))) if generated and source else 0,
        'initial_review': 0, 'repair': 0, 'final_review': len(list(Path(out).glob('final-review-request.json')))}
    if report.get('initial_review'):
        counts['initial_review'] = len(list(bound(report['initial_review']).glob('*-request.json')))
    if report.get('repair'):
        counts['repair'] = len(list(bound(report['repair']).rglob('*-request.json')))
    counts['headlines'] = counts['initial_review']+counts['repair']+counts['final_review']
    if (counts['generation'] > BUDGET['maximum_generation_calls'] or counts['initial_review'] > 1
            or counts['repair'] > 24 or counts['final_review'] > 1 or counts['headlines'] > 26):
        raise ValueError('Complete workflow exceeded frozen model-call budget')
    return counts


def run(source=None, *, sampling_profile='qwen-deliberate-trial.v1', source_lesson=None):
    if source is not None and source_lesson is not None:
        raise ValueError('An existing package cannot receive a new source lesson')
    resources = product.school.check_idle()
    out = Path(tempfile.mkdtemp(prefix='complete-delivery-', dir=product.ROOT))
    implementation = out/'implementation'; implementation.mkdir()
    for name in ('product_delivery_workflow.py', 'product_headline_probe.py', 'product_headline_repair.py',
                 'product_revised_package.py', 'product_infographic_school.py', 'product_full_exam.py',
                 'product_correction_evidence.py', 'product_visual_revision.py'):
        shutil.copyfile(Path(__file__).with_name(name), implementation/name)
    config = product.configuration() | {'sampling_profile': 'bounded-default.v1', 'think': False,
        'num_ctx': 8192, 'num_predict': 2048, 'num_thread': 4, 'timeout_seconds': 90}
    report = {'schema': CONTRACT, 'status': 'running', 'budgets': deepcopy(BUDGET), 'config': config,
        'resources_before': resources, 'generated_here': source is None, 'source': None,
        'initial_review': None, 'repair': None, 'candidate': None, 'training_exported': False,
        'exam_score_changed': False, 'production_changed': False, 'autonomy_qualified': False,
        'independent_panel_approval': False, 'whole_package_accepted': False,
        'fresh_qualification_exam': False, 'independent_review_required': True}
    started = time.monotonic()
    def persist():
        report['elapsed_seconds'] = round(time.monotonic()-started, 3)
        product.school.save(out/'report.json', report)
    persist(); print(json.dumps({'output': str(out)}), flush=True)
    try:
        if source is None:
            source, generation = product.run(sampling_profile=sampling_profile, functional_callouts=True,
                focused_stages=True, recover_incomplete=True, source_contour=True, source_lesson=source_lesson)
            report['source'] = binding(source); persist()
            if generation['status'] != 'pending_independent_review':
                raise ValueError('Generation stopped before a complete package; no headline work started')
        source = Path(source); product.verify(source)
        report['source'] = binding(source); persist()
        folder, initial_report = probe.run(source)
        report['initial_review'] = binding(folder); persist()
        if initial_report['status'] != 'pending_independent_review': raise ValueError('Initial headline review failed')
        original, _, initial = selected_data(source, folder)
        if (config['model'], config['digest']) != (original['model'], original['digest']):
            raise ValueError('Pinned complete-package author changed')
        if all(row['verdict'] == 'supported' for row in initial['reviews']):
            report.update(candidate=binding(source), status='pending_independent_review', final_review_mode='unchanged_initial_review')
        else:
            repaired, repair_report = repair.run(source, folder)
            report['repair'] = binding(repaired); persist()
            if repair_report['status'] != 'pending_independent_review': raise ValueError('Bounded headline repair failed')
            _, data, _ = selected_data(source, folder, repaired)
            final = final_review(out, data, config)
            report['final_review_mode'] = 'all_selected_headlines'
            if any(row['verdict'] != 'supported' for row in final['reviews']):
                report['status'] = 'needs_revision'
            else:
                candidate, candidate_report = assembly.run(source, candidate_headlines=repaired)
                report['assembly'] = binding(candidate); persist()
                if candidate_report['status'] != 'pending_independent_review': raise ValueError('Candidate assembly failed')
                assembly.verify(candidate)
                report.update(candidate=binding(candidate), status='pending_independent_review')
    except Exception as exc:
        report.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:1000])
    finally:
        try: report['model_calls'] = call_counts(out, report)
        except Exception as exc: report.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:1000])
        report['artifacts'] = {str(p.relative_to(out)): product.school.checksum(p)
            for p in out.rglob('*') if p.is_file() and p.name != 'report.json'}
        persist()
    if report['status'] == 'pending_independent_review':
        try: product.school.save(out/'verification.json', verify(out))
        except Exception as exc:
            report.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:1000]); persist()
    print(json.dumps({'report': str(out/'report.json'), 'status': report['status'], 'candidate': report['candidate']}), flush=True)
    return out, report


def verify(out):
    out = Path(out); read = probe.revision.read
    report = read(out/'report.json')
    if (report.get('schema') != CONTRACT or report.get('status') != 'pending_independent_review'
            or report.get('budgets') != BUDGET
            or report.get('independent_review_required') is not True
            or any(report.get(key) is not False for key in ('training_exported', 'exam_score_changed', 'production_changed',
                'autonomy_qualified', 'independent_panel_approval', 'whole_package_accepted', 'fresh_qualification_exam'))):
        raise ValueError('Complete bounded workflow without acceptance claims required')
    for name, checksum in report['artifacts'].items():
        path = probe.revision.bounded(out/name)
        if not path.resolve().is_relative_to(out.resolve()) or product.school.checksum(path) != checksum:
            raise ValueError('Workflow artifact changed')
    source, initial_folder = bound(report['source']), bound(report['initial_review'])
    repaired = bound(report['repair']) if report['repair'] else None
    original, data, initial = selected_data(source, initial_folder, repaired)
    config = report['config']
    if (config['model'], config['digest']) != (original['model'], original['digest']) or any(config.get(k) != v for k, v in
            {'sampling_profile': 'bounded-default.v1', 'think': False, 'num_ctx': 8192, 'num_predict': 2048, 'num_thread': 4, 'timeout_seconds': 90}.items()):
        raise ValueError('Bounded final review configuration changed')
    candidate = bound(report['candidate'])
    if repaired is None:
        if (candidate != source or report['final_review_mode'] != 'unchanged_initial_review'
                or any(row['verdict'] != 'supported' for row in initial['reviews'])
                or list(out.glob('*-request.json'))):
            raise ValueError('Unchanged candidate must match fully supported source')
        candidate_proof = product.verify(candidate)
    else:
        if report['final_review_mode'] != 'all_selected_headlines' or report.get('assembly') != report['candidate']:
            raise ValueError('Bound complete candidate assembly required')
        expected = {'system': probe.SYSTEM, 'user': json.dumps(data), 'format': probe.schema()}
        if not {'final-review-request.json', 'final-review-response.json', 'final-review.json'} <= report['artifacts'].keys():
            raise ValueError('All final review evidence must be hash-bound')
        if read(out/'final-review-request.json') != expected or {p.name for p in out.glob('*-request.json')} != {'final-review-request.json'}:
            raise ValueError('Final review must cover exact selected headlines without hints')
        response = read(out/'final-review-response.json')
        if (response['model'], response['digest']) != (original['model'], original['digest']): raise ValueError('Final reviewer changed')
        reviewed = probe.validate(response['content'], data)
        if read(out/'final-review.json') != reviewed or any(row['verdict'] != 'supported' for row in reviewed['reviews']):
            raise ValueError('Final package still has rejected headline claims')
        candidate_report = read(candidate/'report.json')
        if (candidate_report.get('schema') != assembly.CANDIDATE_SCHEMA
                or Path(candidate_report['original_package']) != source
                or Path(candidate_report['candidate_headlines']) != repaired):
            raise ValueError('Candidate assembled from different sources')
        candidate_proof = assembly.verify(candidate)
    counts = call_counts(out, report)
    if report['model_calls'] != counts: raise ValueError('Recorded model-call count changed')
    return {'schema': CONTRACT, 'report_sha256': product.school.checksum(out/'report.json'),
        'verified': True, 'candidate': str(candidate), 'candidate_verification': candidate_proof,
        'model_calls': counts, 'literal_authorship_verified': True,
        'independent_review_required': True, 'whole_package_accepted': False,
        'autonomy_qualified': False, 'training_exported': False, 'exam_score_changed': False}
