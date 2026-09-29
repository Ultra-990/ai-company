"""Bounded local geometry repair of a preserved failed synthetic scene.

An exploratory repair of an exposed failure, never a new exam score. The model
authors every changed value. The protected product, copy and palette are literal.
"""
from contextlib import nullcontext
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import product_full_exam as exam
from scripts import product_exam_assessment as assessment
from scripts import product_scene_patch as patch
from scripts import product_visual_revision as revision

product = exam.product


def inputs(package):
    package = Path(package); report = revision.read(package/'report.json')
    case = exam.matching_case(report)
    if (report.get('status') != 'failed' or (case is None and
            (report['brief'] != product.DEFAULT_BRIEF or report['supplier_copy'] != product.DEFAULT_PANELS))):
        raise ValueError('Known failed synthetic package required')
    assessment.bound_artifacts(package, report)
    stages = ['style', 'source', *product.DEFAULT_PANELS]; completed = report['stages']
    if completed != stages[:len(completed)] or not 1 <= len(completed) < len(stages):
        raise ValueError('A failed source or panel stage required')
    stage = stages[len(completed)]
    paths = [package/(name+'-response.json') for name in (stage+'-revision-2', stage+'-revision-1', stage)]
    path = next((p for p in paths if p.is_file()), None)
    if path is None or path.name not in report['artifacts']: raise ValueError('Bound complete rejected response required')
    answer = revision.read(path)
    if (answer['model'], answer['digest']) != (report['model'], report['digest']):
        raise ValueError('Rejected author changed')
    config = product.configuration()
    if (report['model'], report['digest']) != (config['model'], config['digest']):
        raise ValueError('Pinned current local model required')
    return report, case, stage, path, product.parse(answer['content'])


def run(package, *, sampling_profile='bounded-default.v1'):
    if sampling_profile not in ('bounded-default.v1', 'qwen-deliberate-trial.v1'):
        raise ValueError('Known bounded repair profile required')
    package = Path(package)
    previous, case, stage, input_path, current = inputs(package)
    resources = product.school.check_idle()
    out = Path(tempfile.mkdtemp(prefix='patch-pilot-', dir=product.ROOT))
    thinking = sampling_profile == 'qwen-deliberate-trial.v1'
    config = product.configuration() | {'sampling_profile': sampling_profile, 'think': thinking,
        'num_ctx': 16384, 'num_predict': 8192 if thinking else 1200, 'num_thread': 4, 'timeout_seconds': 180}
    report = {'schema': 'product-geometry-patch-pilot.v1', 'status': 'running', 'contract': patch.CONTRACT,
        'source_package': str(package), 'source_report_sha256': product.school.checksum(package/'report.json'),
        'source_response': input_path.name, 'source_response_sha256': product.school.checksum(input_path),
        'stage': stage, 'config': config, 'resources_before': resources, 'attempts': [],
        'source_contour_contract': product.silhouette.CONTRACT if stage == 'source' else None,
        'annotation_contract': product.callouts.CONTRACT if stage != 'source' else None,
        'supplier_copy_contract': product.COPY_CONTRACT,
        'training_exported': False, 'exam_score_changed': False, 'whole_package_accepted': False,
        'production_changed': False, 'independent_visual_review_required': True}
    implementation = out/'implementation'; implementation.mkdir()
    for name in ('product_patch_pilot.py', 'product_scene_patch.py', 'product_infographic_school.py',
                 'product_callouts.py', 'product_silhouette.py', 'brand_school.py', 'render_school_svg.py', 'vector_school_contract.py'):
        shutil.copyfile(Path(__file__).parent/name, implementation/name)
    shutil.copyfile(Path(__file__).resolve().parents[1]/'app/services/local_ollama.py', implementation/'local_ollama.py')
    product.school.save(out/'initial-scene.json', current)
    product.school.save(out/'report.json', report)
    print(json.dumps({'output': str(out)}), flush=True)
    started = time.monotonic()
    try:
        with exam.exercise_context(case) if case else nullcontext():
            style = product.style_value(product.accepted_raw(package, 'style'))
            is_panel = stage in product.PANELS
            source = product.compile_scene(product.accepted_raw(package, 'source'), style) if is_panel else None
            placement = previous['placement_contract']
            validate = product.checked_scene(out, 'repair', style, panel=stage if is_panel else None,
                product=source, placement_contract=placement, annotation_contract=product.callouts.CONTRACT if is_panel else None,
                source_contour=not is_panel, copy_contract=product.COPY_CONTRACT)
            # Syntax defects need a different operation; only a rendered,
            # measured failure is a valid starting point for geometry patches.
            try:
                validate(json.dumps(current))
            except product.feedback.SceneFailure as exc:
                error = str(exc); measured = exc.measured or {}
            else:
                raise ValueError('Preserved scene has no current measured geometry defect')
            report['initial_error'] = error
            patch_error = None
            for attempt in range(3):
                name = 'patch-'+str(attempt)
                product.school.save(out/(name+'-before.json'), current)
                profile = product.PROFILES[product.panel_profile(placement) if is_panel else 'product_source']
                data = {'brief': product.BRIEF, 'style': style, 'stage': stage,
                    'canvas': [profile['width'], profile['height']], 'text_margin': profile['margin'],
                    'font_size': [44, 130] if is_panel else [24, 80],
                    'geometry_conventions': 'Text x is its anchor; y is the baseline. Respect the complete measured text box, not only its anchor.',
                    'scene': current, 'independent_error': error,
                    'measurements': {key: measured[key] for key in ('layout', 'shape_layout', 'group_layout') if key in measured}}
                if patch_error is not None: data['previous_patch_rejection'] = patch_error
                if is_panel: data['product_reference'] = revision.read(package/'product-reference.json')
                user = json.dumps(data)
                if len(user) > 16000: raise ValueError('Bounded geometry repair input required')
                raw = product.brand.call(out, name, patch.INSTRUCTION, user, patch.schema(current), config)
                entry = {'attempt': attempt, 'request_sha256': product.school.checksum(out/(name+'-request.json')),
                         'response_sha256': product.school.checksum(out/(name+'-response.json'))}
                report['attempts'].append(entry)
                try:
                    changed = patch.apply(current, raw)
                    product.school.save(out/(name+'-after.json'), changed)
                    # A complete compiler check precedes accepting this edited
                    # scene as the next patch input.
                    svg = product.compile_scene(json.dumps(changed), style, panel=stage if is_panel else None,
                        product=source, placement_contract=placement, copy_contract=product.COPY_CONTRACT)
                    current = changed
                    validate(json.dumps(current))
                except ValueError as exc:
                    if isinstance(exc, product.feedback.SceneFailure):
                        error = str(exc); measured = exc.measured or {}; patch_error = None
                    else:
                        patch_error = str(exc)
                    entry.update(status='rejected', error=str(exc))
                    product.school.save(out/(name+'-feedback.json'), entry)
                    if attempt == 2: raise
                    continue
                entry['status'] = 'measured_pass'
                product.school.save(out/'accepted-scene.json', current)
                (out/'accepted.svg').write_text(svg)
                report.update(status='pending_independent_review', accepted_attempt=attempt,
                              accepted_layout='repair-layout-'+str(len(list(out.glob('repair-layout-*')))-1))
                break
    except Exception as exc:
        report.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:1000])
    finally:
        report['elapsed_seconds'] = round(time.monotonic()-started, 3)
        report['artifacts'] = {str(p.relative_to(out)): product.school.checksum(p) for p in out.rglob('*') if p.is_file() and p.name != 'report.json'}
        product.school.save(out/'report.json', report)
    print(json.dumps({'report': str(out/'report.json'), 'status': report['status'], 'error': report.get('error')}), flush=True)
    return out, report


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    parser.add_argument('--sampling-profile', choices=('bounded-default.v1', 'qwen-deliberate-trial.v1'), default='bounded-default.v1')
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if args.run:
        _, result = run(args.package, sampling_profile=args.sampling_profile)
        raise SystemExit(int(result['status'] == 'failed'))
    else:
        _, _, stage, _, _ = inputs(args.package)
        print(json.dumps({'model_called': False, 'repair_stage': stage, 'contract': patch.CONTRACT}))
