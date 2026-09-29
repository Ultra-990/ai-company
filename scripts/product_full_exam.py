"""Frozen complete-package comparison, with no per-case teacher intervention.

The two arms share briefs, validators, prompts and maximum budgets. Their
named sampling/thinking profiles differ. Generated answers are evaluation-only
and a measured pass is never a visual acceptance or production qualification.
"""
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import time

from scripts import product_infographic_school as product

LEGACY_VERSION = 'product-full-package-exam.v1'
SECOND_VERSION = 'product-full-package-exam.v2'
VERSION = 'product-full-package-exam.v3'
LEGACY_CASES = (
    {'id': 'breeze-400', 'name': 'BREEZE 400', 'capacity': 400, 'height': 20, 'diameter': 6},
    {'id': 'ridge-750', 'name': 'RIDGE 750', 'capacity': 750, 'height': 22, 'diameter': 8},
    {'id': 'trail-900', 'name': 'TRAIL 900', 'capacity': 900, 'height': 30, 'diameter': 7.5},
)
SECOND_CASES = (
    {'id': 'cove-500', 'name': 'COVE 500', 'capacity': 500, 'height': 21, 'diameter': 7},
    {'id': 'mesa-750', 'name': 'MESA 750', 'capacity': 750, 'height': 23, 'diameter': 8.5},
    {'id': 'peak-900', 'name': 'PEAK 900', 'capacity': 900, 'height': 30, 'diameter': 7.5},
)
CASES = (
    {'id': 'sage-350', 'name': 'SAGE 350', 'capacity': 350, 'height': 18, 'diameter': 6.5},
    {'id': 'glen-650', 'name': 'GLEN 650', 'capacity': 650, 'height': 25, 'diameter': 7.5},
    {'id': 'summit-1000', 'name': 'SUMMIT 1000', 'capacity': 1000, 'height': 32, 'diameter': 8},
)
CATALOGS = {LEGACY_VERSION: LEGACY_CASES, SECOND_VERSION: SECOND_CASES, VERSION: CASES}
ARMS = {'baseline': 'bounded-default.v1', 'deliberate': 'qwen-deliberate-trial.v1'}


def definition(case):
    version = next((version for version, cases in CATALOGS.items() if case in cases), None)
    if version is None: raise ValueError('Code-frozen exam case required')
    brief = deepcopy(product.DEFAULT_BRIEF)
    brief.update(product_name=case['name'], family='full-product-exam-'+case['id'], split='test',
                 physical_dimensions_cm=[case['height'], case['diameter']], qualification_exam=version)
    panels = deepcopy(product.DEFAULT_PANELS)
    panels['capacity'][0] = f"Capacity: {case['capacity']} ml"
    panels['dimensions'] = [f"Height: {case['height']} cm", f"Diameter: {case['diameter']} cm"]
    return {'id': case['id'], 'brief': brief, 'supplier_copy': panels}


def matching_case(report):
    for case in (case for cases in CATALOGS.values() for case in cases):
        frozen = definition(case)
        if report.get('brief') == frozen['brief'] and report.get('supplier_copy') == frozen['supplier_copy']:
            return case
    return None


@contextmanager
def exercise_context(case):
    """CLI-only sequential context; never used by concurrent server requests."""
    frozen = definition(case)
    previous = product.BRIEF, product.PANELS
    product.BRIEF, product.PANELS = frozen['brief'], frozen['supplier_copy']
    try:
        yield frozen
    finally:
        product.BRIEF, product.PANELS = previous


def run():
    resources = product.school.check_idle()
    out = Path(tempfile.mkdtemp(prefix='full-exam-', dir=product.ROOT))
    manifest = {'schema': VERSION, 'cases': [definition(case) for case in CASES],
                'arms': ARMS, 'model': product.configuration()['model'], 'digest': product.configuration()['digest'],
                'shared_budget': {'num_ctx': 16384, 'num_predict': 8192, 'num_thread': 4, 'timeout_seconds': 180,
                                  'max_calls_per_stage': 3, 'max_stages': 6},
                'transport_limits': {'wire_bytes_by_arm': {'baseline': 1048576, 'deliberate': 4194304},
                                     'final_answer_characters': 32000, 'stream_line_bytes': 65536,
                                     'intermediate_reasoning_saved': False},
                'shared_controls': {'focused_stages': True, 'functional_callouts': True, 'visual_feedback': False,
                                    'recover_incomplete': True,
                                    'placement_contract': product.PLACEMENT_CONTRACT,
                                    'source_contract': product.SOURCE_FIDELITY_CONTRACT,
                                    'source_instruction_contract': product.SOURCE_INSTRUCTION_CONTRACT,
                                    'source_contour_contract': product.silhouette.CONTRACT,
                                    'product_paint_contract': product.paint.CONTRACT,
                                    'supplier_copy_contract': product.COPY_CONTRACT,
                                    'panel_contract': product.PANEL_FIDELITY_CONTRACT,
                                    'annotation_contract': product.callouts.CONTRACT},
                'training_export_allowed': False, 'manual_hints_allowed': False, 'manual_product_edits_allowed': False,
                'continuations_allowed': False, 'full_visual_review_required': True,
                'limitations': 'Three synthetic cylindrical bottles; not arbitrary products or approved commercial listings.'}
    product.school.save(out/'exam.json', manifest)
    implementation = out/'implementation'; implementation.mkdir()
    for name in ('product_full_exam.py', 'product_infographic_school.py', 'product_callouts.py',
                 'product_model_feedback.py', 'product_silhouette.py', 'product_paint_separation.py', 'brand_school.py', 'render_school_svg.py', 'vector_school_contract.py'):
        shutil.copyfile(Path(__file__).parent/name, implementation/name)
    shutil.copyfile(Path(__file__).resolve().parents[1]/'app/services/local_ollama.py', implementation/'local_ollama.py')
    report = {'schema': 'product-full-package-exam-result.v1', 'status': 'running', 'cases': [],
              'exam_sha256': product.school.checksum(out/'exam.json'), 'resources_before': resources,
              'training_started': False, 'training_exported': False, 'production_changed': False,
              'visual_acceptance': False, 'autonomy_qualified': False}
    product.school.save(out/'report.json', report)
    print(json.dumps({'output': str(out)}), flush=True)
    started = time.monotonic()
    try:
        for index, case in enumerate(CASES):
            result = {'id': case['id'], 'arms': {}}; report['cases'].append(result)
            order = ('baseline', 'deliberate') if index % 2 == 0 else ('deliberate', 'baseline')
            with exercise_context(case):
                for arm in order:
                    package, generated = product.run(sampling_profile=ARMS[arm], functional_callouts=True,
                        focused_stages=True, visual_feedback=False, matched_exam_budget=True, recover_incomplete=True,
                        source_contour=True)
                    actual = generated['config']
                    for key in ('num_ctx', 'num_predict', 'num_thread', 'timeout_seconds'):
                        if actual[key] != manifest['shared_budget'][key]: raise ValueError('Matched exam budget changed')
                    if (generated['model'], generated['digest']) != (manifest['model'], manifest['digest']):
                        raise ValueError('Pinned exam author changed')
                    passed = generated['status'] == 'pending_independent_review'
                    if passed: product.verify(package)
                    requests = len(list(package.glob('*-request.json')))
                    if requests > 18: raise ValueError('Bounded stage-call limit exceeded')
                    result['arms'][arm] = {'package': str(package), 'report_sha256': product.school.checksum(package/'report.json'),
                        'measured_pass': passed, 'error': generated.get('error'), 'model_calls': len(list(package.glob('*-response.json'))),
                        'model_requests': requests,
                        'elapsed_seconds': generated['elapsed_seconds']}
                    product.school.save(out/'report.json', report)
                    print(json.dumps({'case': case['id'], 'arm': arm, **result['arms'][arm]}), flush=True)
        report.update(status='completed', scores={arm: sum(case['arms'][arm]['measured_pass'] for case in report['cases']) for arm in ARMS})
    except Exception as exc:
        report.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:1500])
    finally:
        report['elapsed_seconds'] = round(time.monotonic()-started, 3)
        report['artifacts'] = {str(p.relative_to(out)): product.school.checksum(p) for p in out.rglob('*') if p.is_file() and p.name != 'report.json'}
        product.school.save(out/'report.json', report)
    print(json.dumps({'report': str(out/'report.json'), 'status': report['status'], 'scores': report.get('scores')}), flush=True)
    return out, report
