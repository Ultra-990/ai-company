"""Replay one bound failed synthetic request to diagnose wire/token limits.

This is a separate transport observation. It never resumes a package, changes
exam scores, accepts artwork, exports training data or reveals reasoning text.
"""
import asyncio
from pathlib import Path
import shutil
import tempfile

from app.services.local_ollama import OllamaProvider
from scripts import product_infographic_school as product
from scripts import product_full_exam as exam
from scripts import product_exam_assessment as assessment
from scripts import product_visual_revision as revision


def audit_callouts(package):
    """Re-measure one rejected panel, keeping its old score and exact SVG."""
    package = Path(package); previous = revision.read(package/'report.json')
    case = exam.matching_case(previous)
    if previous.get('status') != 'failed' or case is None:
        raise ValueError('Failed frozen synthetic exam package required')
    assessment.bound_artifacts(package, previous)
    stages = ['style', 'source', *product.PANELS]
    completed = previous['stages']
    if completed != stages[:len(completed)] or len(completed) >= len(stages):
        raise ValueError('Failed model stage required')
    stage = stages[len(completed)]
    if stage not in product.PANELS: raise ValueError('A rejected panel is required')
    layouts = sorted(package.glob(stage+'-layout-*'), key=lambda p: int(p.name.rsplit('-', 1)[1]))
    if not layouts: raise ValueError('A preserved rendered answer is required')
    with exam.exercise_context(case):
        style = product.style_value(product.accepted_raw(package, 'style'))
        source = product.compile_scene(product.accepted_raw(package, 'source'), style)
        placement = previous['placement_contract']
        responses = [package/(name+'-response.json') for name in (stage+'-revision-2', stage+'-revision-1', stage)]
        response_path = next((p for p in responses if p.is_file()), None)
        if response_path is None or response_path.name not in previous['artifacts']:
            raise ValueError('Bound rejected local response required')
        answer = revision.read(response_path)
        if (answer['model'], answer['digest']) != (previous['model'], previous['digest']):
            raise ValueError('Rejected response author changed')
        svg = product.compile_scene(answer['content'], style, panel=stage, product=source, placement_contract=placement)
        if svg != revision.bounded(layouts[-1]/'artwork.svg').read_text():
            raise ValueError('Preserved panel differs from latest local answer')
        product.school.check_idle()
        out = Path(tempfile.mkdtemp(prefix='callout-audit-', dir=product.ROOT))
        (out/'artwork.svg').write_text(svg)
        measured = asyncio.run(product.render(svg, out, profile=product.panel_profile(placement), png_scale=.4))
        product.school.save(out/'render.json', measured)
        base = product.quality_issues(measured, panel=True, panel_contrast=True, placement_contract=placement, line_check=True)
        report = {'schema': 'product-failed-callout-audit.v1', 'source_package': str(package),
                  'source_report_sha256': product.school.checksum(package/'report.json'), 'stage': stage,
                  'rejected_response_sha256': product.school.checksum(response_path),
                  'svg_sha256': product.school.checksum(layouts[-1]/'artwork.svg'),
                  'old_contract': previous['annotation_contract'], 'current_contract': product.callouts.CONTRACT,
                  'old_issues': base+product.callouts.issues(measured, stage, style, contract=previous['annotation_contract']),
                  'current_issues': base+product.callouts.issues(measured, stage, style),
                  'model_called': False, 'exam_score_changed': False, 'training_exported': False,
                  'whole_package_accepted': False}
        report['artifacts'] = {p.name: product.school.checksum(p) for p in out.iterdir() if p.is_file()}
        product.school.save(out/'report.json', report)
    print(product.json.dumps({'report': str(out/'report.json'), 'old_issues': report['old_issues'], 'current_issues': report['current_issues']}))
    return out, report


def probe_input(package):
    package = Path(package)
    report = revision.read(package/'report.json')
    if (report.get('status') != 'failed' or exam.matching_case(report) is None
            or report.get('error') not in ('invalid_stream', 'truncated_output', 'incomplete_stream', 'stream_size_limit')):
        raise ValueError('Frozen synthetic exam with a recorded transport failure required')
    assessment.bound_artifacts(package, report)
    pending = [p for p in package.glob('*-request.json') if not p.with_name(p.name.replace('-request.json', '-response.json')).exists()]
    if len(pending) != 1 or pending[0].name not in report['artifacts']:
        raise ValueError('Exactly one bound unfinished request required')
    request = revision.read(pending[0])
    if set(request) != {'system', 'user', 'format'}: raise ValueError('Bound text/schema request required')
    config = report['config']
    expected = product.configuration()
    if ((config['model'], config['digest']) != (expected['model'], expected['digest'])
            or config.get('sampling_profile') != 'qwen-deliberate-trial.v1' or config.get('think') is not True):
        raise ValueError('Pinned explicit reasoning trial required')
    for key, lower, upper in (('num_ctx', 2048, 16384), ('num_predict', 32, 8192), ('num_thread', 1, 4), ('timeout_seconds', 10, 180)):
        if type(config[key]) is not int or not lower <= config[key] <= upper: raise ValueError('Bounded probe config required')
    return report, pending[0], request


def run(package):
    package = Path(package)
    previous, request_path, request = probe_input(package)
    resources = product.school.check_idle()
    out = Path(tempfile.mkdtemp(prefix='stream-probe-', dir=product.ROOT))
    shutil.copyfile(request_path, out/'request.json')
    code = out/'implementation'; code.mkdir()
    shutil.copyfile(Path(__file__), code/Path(__file__).name)
    shutil.copyfile(Path(__file__).resolve().parents[1]/'app/services/local_ollama.py', code/'local_ollama.py')
    report = {'schema': 'product-stream-probe.v1', 'status': 'running', 'source_package': str(package),
              'source_report_sha256': product.school.checksum(package/'report.json'),
              'source_request': request_path.name, 'source_request_sha256': product.school.checksum(request_path),
              'prior_error': previous['error'], 'config': previous['config'], 'resources_before': resources,
              'artwork_accepted': False, 'exam_score_changed': False, 'training_exported': False,
              'production_changed': False, 'intermediate_reasoning_saved': False}
    product.school.save(out/'report.json', report)
    print(product.json.dumps({'output': str(out)}), flush=True)
    try:
        result = OllamaProvider(previous['config'] | {'format': request['format']}).complete([
            {'role': 'system', 'content': request['system']}, {'role': 'user', 'content': request['user']}])
        product.school.save(out/'response.json', result)
        report.update(status='transport_completed', stream_bytes=result['stream_bytes'],
                      old_wire_budget_exceeded=result['stream_bytes'] > 1024*1024,
                      elapsed_seconds=result['elapsed_seconds'], eval_count=result['eval_count'])
    except Exception as exc:
        report.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:300])
    report['artifacts'] = {str(p.relative_to(out)): product.school.checksum(p) for p in out.rglob('*') if p.is_file() and p.name != 'report.json'}
    product.school.save(out/'report.json', report)
    print(product.json.dumps({key: report[key] for key in ('status', 'stream_bytes', 'old_wire_budget_exceeded', 'error') if key in report}), flush=True)
    return out, report
