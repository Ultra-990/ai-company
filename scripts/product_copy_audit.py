"""Recheck a preserved rejected response without changing fact order or artwork."""
import asyncio
from contextlib import nullcontext
from pathlib import Path
import tempfile

from scripts import product_exam_assessment as assessment
from scripts import product_full_exam as exam
from scripts import product_visual_revision as revision

product = exam.product


def run(package):
    package = Path(package); previous = revision.read(package/'report.json')
    case = exam.matching_case(previous)
    if (previous.get('status') != 'failed' or (case is None and
            (previous['brief'] != product.DEFAULT_BRIEF or previous['supplier_copy'] != product.DEFAULT_PANELS))):
        raise ValueError('Known failed synthetic package required')
    assessment.bound_artifacts(package, previous)
    stages = ['style', 'source', *product.DEFAULT_PANELS]
    completed = previous['stages']
    if completed != stages[:len(completed)] or not 2 <= len(completed) < len(stages):
        raise ValueError('Failed panel stage required')
    stage = stages[len(completed)]
    responses = [package/(name+'-response.json') for name in (stage+'-revision-2', stage+'-revision-1', stage)]
    path = next((path for path in responses if path.exists()), None)
    if path is None or path.name not in previous['artifacts']:
        raise ValueError('Bound rejected response required')
    answer = revision.read(path)
    if (answer['model'], answer['digest']) != (previous['model'], previous['digest']):
        raise ValueError('Rejected response author changed')
    with exam.exercise_context(case) if case else nullcontext():
        style = product.style_value(product.accepted_raw(package, 'style'))
        source = product.compile_scene(product.accepted_raw(package, 'source'), style)
        options = {'panel': stage, 'product': source, 'placement_contract': previous['placement_contract']}
        try:
            product.compile_scene(answer['content'], style, **options)
        except ValueError as exc:
            old_error = str(exc)
            if not old_error.startswith('Preserve both frozen supplier lines exactly and in order:'):
                raise ValueError('A recorded-order representation defect is required') from exc
        else:
            raise ValueError('Original response already satisfied the legacy copy contract')
        svg = product.compile_scene(answer['content'], style, copy_contract=product.COPY_CONTRACT, **options)
        product.school.check_idle()
        out = Path(tempfile.mkdtemp(prefix='copy-order-audit-', dir=product.ROOT))
        (out/'artwork.svg').write_text(svg)
        measured = asyncio.run(product.render(svg, out, profile=product.panel_profile(previous['placement_contract']), png_scale=.4))
        product.school.save(out/'render.json', measured)
        issues = product.quality_issues(measured, panel=True, panel_contrast=True,
            placement_contract=previous['placement_contract'], line_check=True)
        issues += product.callouts.issues(measured, stage, style)
        report = {'schema': 'product-copy-order-audit.v1', 'source_package': str(package),
            'source_report_sha256': product.school.checksum(package/'report.json'),
            'response': path.name, 'response_sha256': product.school.checksum(path),
            'old_error': old_error, 'copy_contract': product.COPY_CONTRACT,
            'annotation_contract': product.callouts.CONTRACT, 'current_issues': issues,
            'literal_model_values_preserved': True, 'model_called': False,
            'exam_score_changed': False, 'whole_package_accepted': False, 'training_exported': False,
            'artifacts': {p.name: product.school.checksum(p) for p in out.iterdir() if p.is_file()}}
        product.school.save(out/'report.json', report)
    print(product.json.dumps({'report': str(out/'report.json'), 'old_error': old_error, 'current_issues': issues}))
    return out, report
