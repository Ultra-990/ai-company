"""Reuse an independently measured and reviewed literal local source repair.

Continuation of the SAME failed synthetic brief only, never an exam lesson or
a fresh qualification run. The complete panel package needs its own review.
"""
import json
from pathlib import Path
from contextlib import nullcontext

from scripts import product_patch_pilot as pilot

product = pilot.product
CONTRACT = 'reviewed-local-source-repair.v1'


def load(folder):
    folder = Path(folder); read = pilot.revision.read; checksum = product.school.checksum
    report = read(folder/'report.json'); judgment = read(folder/'independent-review.json')
    if (report.get('schema') != 'product-geometry-patch-pilot.v1'
            or report.get('contract') != pilot.patch.CONTRACT or report.get('stage') != 'source'
            or report.get('status') != 'pending_independent_review'
            or report.get('source_contour_contract') != product.silhouette.CONTRACT
            or any(report.get(k) is not False for k in ('training_exported', 'exam_score_changed', 'whole_package_accepted', 'production_changed'))):
        raise ValueError('Completed current source repair required')
    pilot.assessment.bound_artifacts(folder, report)
    if (judgment.get('schema') != 'product-source-patch-independent-review.v1'
            or judgment.get('decision') != 'approved_targeted_source_repair'
            or judgment.get('reviewer') != 'assistant_direct_visual_review'
            or judgment.get('report_sha256') != checksum(folder/'report.json')
            or any(judgment.get(k) is not False for k in ('training_exported', 'exam_score_changed', 'whole_package_accepted'))):
        raise ValueError('Bound independent positive source review required')
    image = report['accepted_layout']+'/preview.png'
    if (image not in report['artifacts'] or judgment.get('inspected_images') != {image: checksum(pilot.revision.bounded(folder/image))}):
        raise ValueError('Reviewed source image changed')
    evidence_path = pilot.revision.bounded(Path(judgment['evidence_report']))
    evidence = read(evidence_path)
    if (checksum(evidence_path) != judgment['evidence_report_sha256']
            or evidence.get('schema') != 'product-geometry-patch-evidence.v1'
            or evidence.get('report_sha256') != checksum(folder/'report.json')
            or evidence.get('source_report_sha256') != report['source_report_sha256']
            or evidence.get('stage') != 'source'
            or any(evidence.get(k) is not True for k in ('literal_edits_replayed', 'feedback_remeasured', 'local_author_verified'))):
        raise ValueError('Independently remeasured source patch evidence required')
    pilot.assessment.bound_artifacts(evidence_path.parent, evidence)
    package = Path(report['source_package'])
    if checksum(pilot.revision.bounded(package/'report.json')) != report['source_report_sha256']:
        raise ValueError('Original failed package changed')
    original, case, stage, response, current = pilot.inputs(package)
    if stage != 'source' or response.name != report['source_response'] or checksum(response) != report['source_response_sha256']:
        raise ValueError('Repair must derive from the original rejected source')
    style_raw = product.accepted_raw(package, 'style'); style = product.style_value(style_raw)
    attempts = report['attempts']
    if not 1 <= len(attempts) <= 3 or evidence['attempts'] != len(attempts):
        raise ValueError('Bound source repair budget required')
    with pilot.exam.exercise_context(case) if case else nullcontext():
        for index, entry in enumerate(attempts):
            name = 'patch-'+str(index)+'-response.json'
            answer = read(folder/name)
            if (name not in report['artifacts'] or entry['response_sha256'] != checksum(folder/name)
                    or (answer['model'], answer['digest']) != (original['model'], original['digest'])):
                raise ValueError('Patch author or response changed')
            try:
                changed = pilot.patch.apply(current, answer['content'])
                product.compile_scene(json.dumps(changed), style)
            except ValueError:
                if entry['status'] != 'rejected' or index == len(attempts)-1: raise
                continue
            current = changed
        svg = product.compile_scene(json.dumps(current), style)
    if (report['accepted_attempt'] != len(attempts)-1 or attempts[-1]['status'] != 'measured_pass'
            or current != read(folder/'accepted-scene.json') or svg != (folder/'accepted.svg').read_text()):
        raise ValueError('Source must preserve literal original plus model patch values')
    return {'contract': CONTRACT, 'repair': str(folder), 'repair_report_sha256': checksum(folder/'report.json'),
        'review_sha256': checksum(folder/'independent-review.json'), 'evidence_report_sha256': checksum(evidence_path),
        'original_package': str(package), 'original_report_sha256': checksum(package/'report.json'),
        'brief': original['brief'], 'supplier_copy': original['supplier_copy'], 'style_raw': style_raw, 'scene': current,
        'model': original['model'], 'digest': original['digest'], 'training_exported': False, 'exam_score_changed': False}


def verify_binding(folder, report):
    path = Path(folder)/'source-repair.json'
    if (report.get('source_repair_contract') != CONTRACT or report.get('inherited_stages') != ['style', 'source']
            or report['artifacts'].get('source-repair.json') != product.school.checksum(pilot.revision.bounded(path))):
        raise ValueError('Bound inherited source repair required')
    value = pilot.revision.read(path)
    if (load(value['repair']) != value or (value['model'], value['digest']) != (report['model'], report['digest'])
            or value['brief'] != report['brief'] or value['supplier_copy'] != report['supplier_copy']):
        raise ValueError('Source repair replaced the original brief or local author')
    if any(Path(folder).glob('source*-response.json')) or any(Path(folder).glob('style*-response.json')):
        raise ValueError('Inherited source repair must not fabricate new style/source responses')
    return value
