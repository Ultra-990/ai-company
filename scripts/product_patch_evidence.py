"""Replay literal local geometry edits and independently remeasure their results.

This verifies a targeted diagnostic repair, never a new exam or whole-package
acceptance. Historical source pilots used contour v1; their code snapshots
determine that contract when explicit metadata is absent.
"""
from contextlib import nullcontext
import json
from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import product_patch_pilot as pilot

product = pilot.product


def assess(folder):
    folder = Path(folder)
    report = pilot.revision.read(folder/'report.json')
    if (report.get('schema') != 'product-geometry-patch-pilot.v1'
            or report.get('contract') != pilot.patch.CONTRACT
            or report.get('status') != 'pending_independent_review'
            or any(report.get(k) is not False for k in
                   ('training_exported', 'exam_score_changed', 'whole_package_accepted', 'production_changed'))):
        raise ValueError('Completed diagnostic geometry pilot required')
    pilot.assessment.bound_artifacts(folder, report)
    checksum = product.school.checksum
    def read(name):
        if name not in report['artifacts']:
            raise ValueError('Missing bound repair evidence: '+name)
        return pilot.revision.read(folder/name)
    package = Path(report['source_package'])
    if checksum(pilot.revision.bounded(package/'report.json')) != report['source_report_sha256']:
        raise ValueError('Original package binding changed')
    previous, case, stage, response_path, initial = (pilot.inputs(package, part=report['explicit_panel'])
        if report.get('explicit_panel') is not None else pilot.inputs(package))
    if (stage != report['stage'] or response_path.name != report['source_response']
            or checksum(response_path) != report['source_response_sha256']
            or read('initial-scene.json') != initial):
        raise ValueError('Repair does not start from the preserved rejected answer')
    attempts = report['attempts']
    if (not 1 <= len(attempts) <= 3 or report['accepted_attempt'] != len(attempts)-1
            or {p.name for p in folder.glob('patch-*-request.json')} !=
               {'patch-'+str(i)+'-request.json' for i in range(len(attempts))}):
        raise ValueError('Repair call budget or accepted attempt changed')
    cfg = report['config']; thinking = cfg.get('sampling_profile') == 'qwen-deliberate-trial.v1'
    if (cfg.get('sampling_profile') not in ('bounded-default.v1', 'qwen-deliberate-trial.v1')
            or (cfg['model'], cfg['digest']) != (previous['model'], previous['digest'])
            or cfg.get('num_ctx') != 16384 or cfg.get('num_predict') != (8192 if thinking else 1200)
            or cfg.get('think') is not thinking or cfg.get('num_thread') != 4 or cfg.get('timeout_seconds') != 180):
        raise ValueError('Bounded repair configuration changed')
    is_panel = stage in product.DEFAULT_PANELS
    contour = report.get('source_contour_contract')
    if not is_panel and contour is None:
        # Only the first preserved implementation is supported implicitly.
        code = (folder/'implementation/product_silhouette.py').read_text()
        if "CONTRACT = 'synthetic-bottle-contour.v1'" not in code or 'LEGACY_CONTRACT' in code:
            raise ValueError('Explicit source contour contract required')
        contour = product.silhouette.LEGACY_CONTRACT
    if not is_panel and contour not in (product.silhouette.LEGACY_CONTRACT, product.silhouette.CONTRACT):
        raise ValueError('Unknown source contour contract')
    annotation = report.get('annotation_contract', product.callouts.CONTRACT if is_panel else None)
    copy = report.get('supplier_copy_contract', product.COPY_CONTRACT)
    paint = report.get('product_paint_contract')
    if paint not in (None, product.paint.CONTRACT) or (paint and not is_panel):
        raise ValueError('Unknown repair paint contract')
    if annotation != (product.callouts.CONTRACT if is_panel else None) or copy != product.COPY_CONTRACT:
        raise ValueError('Unknown repair scene contracts')
    out = Path(tempfile.mkdtemp(prefix='patch-evidence-', dir=product.ROOT))
    with pilot.exam.exercise_context(case) if case else nullcontext():
        style = product.style_value(product.accepted_raw(package, 'style'))
        source = product.compile_scene(product.accepted_raw(package, 'source'), style) if is_panel else None
        placement = previous['placement_contract']
        validate = product.checked_scene(out, 'replay', style, panel=stage if is_panel else None,
            product=source, placement_contract=placement, annotation_contract=annotation,
            source_contour=contour if not is_panel else False, copy_contract=copy, paint_separation=bool(paint))
        current = initial
        try:
            validate(json.dumps(current))
        except product.feedback.SceneFailure as exc:
            error = str(exc); measured = exc.measured or {}
        else:
            raise ValueError('Original scene has no measured defect')
        if error != report['initial_error']:
            raise ValueError('Initial independent diagnostic changed')
        patch_error = None
        for index, entry in enumerate(attempts):
            name = 'patch-'+str(index)
            request = read(name+'-request.json'); response = read(name+'-response.json')
            profile = product.PROFILES[product.panel_profile(placement) if is_panel else 'product_source']
            expected = {'brief': product.BRIEF, 'style': style, 'stage': stage,
                'canvas': [profile['width'], profile['height']], 'text_margin': profile['margin'],
                'font_size': [44, 130] if is_panel else [24, 80],
                'geometry_conventions': 'Text x is its anchor; y is the baseline. Respect the complete measured text box, not only its anchor.',
                'scene': current, 'independent_error': error,
                'measurements': {key: measured[key] for key in ('layout', 'shape_layout', 'group_layout') if key in measured}}
            if patch_error is not None: expected['previous_patch_rejection'] = patch_error
            if is_panel: expected['product_reference'] = pilot.revision.read(package/'product-reference.json')
            if (entry['attempt'] != index or entry['request_sha256'] != checksum(folder/(name+'-request.json'))
                    or entry['response_sha256'] != checksum(folder/(name+'-response.json'))
                    or request != {'system': pilot.patch.INSTRUCTION, 'user': json.dumps(expected), 'format': pilot.patch.schema(current)}
                    or read(name+'-before.json') != current
                    or (response['model'], response['digest']) != (cfg['model'], cfg['digest'])):
                raise ValueError('Repair request, prior scene, feedback or local author changed')
            try:
                changed = pilot.patch.apply(current, response['content'])
                if read(name+'-after.json') != changed:
                    raise RuntimeError('Saved scene differs from literal local edits')
                svg = product.compile_scene(json.dumps(changed), style, panel=stage if is_panel else None,
                    product=source, placement_contract=placement, copy_contract=copy)
                current = changed
                validate(json.dumps(current))
            except ValueError as exc:
                if entry.get('status') != 'rejected' or entry.get('error') != str(exc) or index == len(attempts)-1:
                    raise ValueError('Recorded rejection differs from independent replay') from exc
                if read(name+'-feedback.json') != entry:
                    raise ValueError('Patch feedback changed')
                if isinstance(exc, product.feedback.SceneFailure):
                    error = str(exc); measured = exc.measured or {}; patch_error = None
                else: patch_error = str(exc)
                continue
            if entry.get('status') != 'measured_pass' or index != len(attempts)-1:
                raise ValueError('Calls follow an accepted patch')
        if (read('accepted-scene.json') != current or 'accepted.svg' not in report['artifacts']
                or (folder/'accepted.svg').read_text() != svg):
            raise ValueError('Accepted scene or SVG differs from literal edit replay')
    result = {'schema': 'product-geometry-patch-evidence.v1', 'report_sha256': checksum(folder/'report.json'),
        'source_report_sha256': report['source_report_sha256'], 'stage': stage, 'attempts': len(attempts),
        'literal_edits_replayed': True, 'feedback_remeasured': True, 'local_author_verified': True,
        'unchanged_facts_paint_and_fonts': True, 'source_contour_contract': contour,
        'whole_package_accepted': False, 'independent_visual_review_required': True,
        'exam_score_changed': False, 'training_exported': False,
        'artifacts': {str(p.relative_to(out)): checksum(p) for p in out.rglob('*') if p.is_file()}}
    product.school.save(out/'report.json', result)
    return out, result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pilot', type=Path)
    args = parser.parse_args()
    output, result = assess(args.pilot)
    print(json.dumps({'output': str(output), **{k: v for k, v in result.items() if k != 'artifacts'}}))
