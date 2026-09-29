"""Read-only integrity and outcome assessment of a complete frozen product exam."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import product_full_exam as exam
from scripts import product_visual_revision as revision

product = exam.product


def bound_artifacts(folder, report):
    for name, digest in report['artifacts'].items():
        path = Path(folder)/name
        if not path.resolve().is_relative_to(Path(folder).resolve()):
            raise ValueError('Artifact outside its package')
        if product.school.checksum(revision.bounded(path)) != digest:
            raise ValueError('Bound artifact changed: '+name)


def assess(path):
    path = Path(path)
    report = revision.read(path/'report.json'); manifest = revision.read(path/'exam.json')
    if (report.get('schema') != 'product-full-package-exam-result.v1' or report.get('status') != 'completed'
            or manifest.get('schema') not in exam.CATALOGS
            or product.school.checksum(path/'exam.json') != report['exam_sha256']):
        raise ValueError('Completed unchanged frozen exam required')
    version = manifest['schema']
    if (manifest['cases'] != [exam.definition(case) for case in exam.CATALOGS[version]] or manifest['arms'] != exam.ARMS
            or manifest['training_export_allowed'] is not False or manifest['manual_hints_allowed'] is not False
            or manifest['manual_product_edits_allowed'] is not False or manifest['continuations_allowed'] is not False):
        raise ValueError('Exam cases, arms or independent evaluation controls changed')
    bound_artifacts(path, report)
    if [case['id'] for case in report['cases']] != [case['id'] for case in manifest['cases']]:
        raise ValueError('Exactly three frozen cases in original order required')
    scores = {arm: 0 for arm in exam.ARMS}; outcomes = []
    seen = set()
    for case, frozen in zip(report['cases'], manifest['cases'], strict=True):
        if set(case['arms']) != set(exam.ARMS): raise ValueError('Both matched arms required')
        for arm, outcome in case['arms'].items():
            folder = Path(outcome['package'])
            package = revision.read(folder/'report.json')
            if folder.resolve() in seen: raise ValueError('Each case/arm requires its own execution')
            seen.add(folder.resolve())
            if (product.school.checksum(folder/'report.json') != outcome['report_sha256']
                    or package['brief'] != frozen['brief'] or package['supplier_copy'] != frozen['supplier_copy']):
                raise ValueError('Case result binding changed')
            bound_artifacts(folder, package)
            if any(key in package for key in ('resumed_from', 'recomposed_from', 'inherited_stages')):
                raise ValueError('Fresh independent complete execution required')
            config = package['config']
            if ((package['model'], package['digest']) != (manifest['model'], manifest['digest'])
                    or config['sampling_profile'] != exam.ARMS[arm]
                    or config.get('think') is not (arm == 'deliberate')):
                raise ValueError('Matched model or sampling profile changed')
            for key in ('num_ctx', 'num_predict', 'num_thread', 'timeout_seconds'):
                if config[key] != manifest['shared_budget'][key]: raise ValueError('Unequal exam budget')
            for name in ('product_infographic_school.py', 'product_callouts.py', 'brand_school.py',
                         'product_model_feedback.py', 'render_school_svg.py', 'vector_school_contract.py',
                         *(('product_silhouette.py',) if manifest['shared_controls'].get('source_instruction_contract') else ()),
                         *(('product_paint_separation.py',) if manifest['shared_controls'].get('product_paint_contract') else ()),
                         *(('product_source_lesson.py',) if manifest['shared_controls'].get('source_lesson_contract') else ()),
                         *(('local_ollama.py',) if version != exam.LEGACY_VERSION else ())):
                if (revision.bounded(folder/'implementation'/name).read_bytes()
                        != revision.bounded(path/'implementation'/name).read_bytes()):
                    raise ValueError('Implementation changed during the frozen exam')
            controls = manifest['shared_controls']
            for field in ('source_instruction_contract', 'source_contour_contract', 'product_paint_contract', 'source_lesson_contract'):
                if package.get(field) != controls.get(field): raise ValueError('Case source controls changed')
            if controls.get('source_lesson_contract'):
                from scripts import product_source_lesson as lesson
                saved_lesson = revision.read(folder/'source-lesson.json')
                if ('source-lesson.json' not in package['artifacts'] or saved_lesson != manifest.get('source_lesson')
                        or saved_lesson != lesson.load(saved_lesson['assembly'])):
                    raise ValueError('Exam source lesson differs between arms or from reviewed training data')
                if (folder/'source-request.json').exists(): lesson.verify_binding(folder, package)
            elif manifest.get('source_lesson') is not None:
                raise ValueError('Undeclared source lesson in exam manifest')
            if package.get('supplier_copy_contract', product.LEGACY_COPY) != controls.get('supplier_copy_contract', product.LEGACY_COPY):
                raise ValueError('Case supplier copy contract changed')
            for field, control in (('source_fidelity_contract', 'source_contract'),
                                   ('panel_fidelity_contract', 'panel_contract'),
                                   ('placement_contract', 'placement_contract'),
                                   ('annotation_contract', 'annotation_contract')):
                if package[field] != controls[control]: raise ValueError('Case acceptance contract changed')
            if package['instruction_contract'] != 'focused-stages.v1' or package['correction_contract'] != 'legacy-text.v1':
                raise ValueError('Case instruction or feedback arm changed')
            recovery = 'bounded-incomplete-retry.v1' if version != exam.LEGACY_VERSION else None
            if package.get('transport_recovery_contract') != recovery:
                raise ValueError('Case incomplete-answer recovery contract changed')
            requests = sorted(folder.glob('*-request.json')); responses = sorted(folder.glob('*-response.json'))
            if (outcome['model_requests'] != len(requests) or outcome['model_calls'] != len(responses)
                    or not 1 <= len(requests) <= 18 or len(responses) > len(requests)):
                raise ValueError('Stage-call accounting changed')
            for request in requests:
                data = revision.read(request)
                # brand.call records prompts/schema, while the package binds
                # its common config and the unchanged caller implementation.
                if set(data) != {'system', 'user', 'format'}:
                    raise ValueError('Unexpected request channel or format')
            passed = package['status'] == 'pending_independent_review'
            if package['status'] not in ('pending_independent_review', 'failed') or outcome['measured_pass'] is not passed:
                raise ValueError('Outcome does not match bounded execution')
            if passed: product.verify(folder)
            scores[arm] += int(passed)
            outcomes.append({'case': case['id'], 'arm': arm, 'package': str(folder), 'measured_pass': passed,
                             'model_requests': len(requests), 'elapsed_seconds': package['elapsed_seconds']})
    if scores != report['scores']: raise ValueError('Exam score differs from verified outcomes')
    return {'schema': 'product-full-package-exam-assessment.v1', 'exam_report_sha256': product.school.checksum(path/'report.json'),
            'integrity_verified': True, 'scores': scores, 'cases': outcomes, 'matched_budget': True,
            'independent_visual_review_required': True, 'autonomy_qualified': False,
            'training_exported': False, 'production_changed': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('exam', type=Path)
    args = parser.parse_args()
    print(json.dumps(assess(args.exam), ensure_ascii=False, indent=2))
