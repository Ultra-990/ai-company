"""Frozen reserved SVG exercises, with no feedback or training export of answers.

Preparation and evaluation are separate commands. Faults are authored by a local
model before the candidate sees the tasks. Whole-image recreation is reported
separately from exact attribute restoration; neither proves service readiness.
"""
import argparse
import asyncio
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.local_ollama import configuration
from scripts import vector_school as school
from scripts import vector_practice as practice
from scripts import vector_patch_school as patch
from scripts.vector_curriculum import metadata
from scripts.vector_school_contract import RULES, RECREATE_BRIEF, SCHEMA as SVG_SCHEMA, THRESHOLDS, parse_response, compare, layout_issues, validate_svg
from scripts.render_school_svg import render, pdf_checks

SCHEMA = 'vector-reserved-exam.v1'


def reference(path):
    report = practice.read(path)
    if (report.get('schema') not in {'vector-school.v1', 'vector-structured-source.v1'}
            or report.get('role') != 'source' or report.get('status') != 'reference_ready'
            or metadata(report)['data_split'] not in {'validation', 'test'}):
        raise ValueError('Completed reserved reference required')
    rendered = school.authenticate(path, report)
    review = practice.read(path.parent/'reference-review.json')
    if (review.get('schema') != 'vector-evaluation-reference-review.v1'
            or review.get('source_sha256') != school.checksum(path)
            or review.get('reviewer') != 'assistant_direct_visual_review'
            or review.get('decision') != 'usable_reserved_reference'
            or not isinstance(review.get('notes'), str) or len(review['notes']) < 20
            or layout_issues(rendered['layout'])):
        raise ValueError('Independent reserved reference approval required')
    return report, school.checked(path.parent/'artwork.svg').read_bytes().decode('utf-8'), rendered


def prepare(source_path):
    source_report, source, measured = reference(source_path)
    resources = school.check_idle()
    out = Path(tempfile.mkdtemp(prefix='exam-', dir=school.ROOT))
    config = configuration() | {'format': patch.EDIT_SCHEMA, 'num_ctx': 8192, 'num_predict': 400,
                                'num_thread': 4, 'timeout_seconds': 120}
    report = {'schema': SCHEMA, 'status': 'preparing', **metadata(source_report),
              'source_report': str(source_path), 'source_sha256': school.checksum(source_path),
              'reference_review_sha256': school.checksum(source_path.parent/'reference-review.json'),
              'fault_config': config, 'resources_before': resources, 'cases': [], 'thresholds': THRESHOLDS,
              'implementation_sha256': {name: school.checksum(Path(__file__).parent/name) for name in
                  ('vector_exam.py', 'vector_practice.py', 'vector_school_contract.py', 'render_school_svg.py')},
              'training_exported': False, 'training_started': False, 'production_changed': False}
    school.save(out/'report.json', report)
    print(json.dumps({'exam': str(out/'report.json')}), flush=True)
    for index in range(24):
        folder = out/f'case-{index:02d}'; folder.mkdir()
        case = practice.plan(source, index)
        entry = {'id': index, 'kind': 'attribute_restoration', 'case': case}
        try:
            request = practice.fault_request(source, case, source_path)
            raw = practice.call(config, request, folder, 'fault')
            faulty = practice.apply_fault(source, raw, case)
            (folder/'faulty.svg').write_text(faulty)
            school.check_idle()
            fault_render = asyncio.run(render(faulty, folder, purpose='controlled_fault_input'))
            school.save(folder/'fault-render.json', fault_render)
            pupil = practice.repair_request(faulty, measured, fault_render, case, request['image'])
            school.save(folder/'request.json', pupil)
            entry['status'] = 'ready'
        except Exception as exc:
            entry.update(status='invalid_input', error_type=type(exc).__name__, error=str(exc)[:240])
        entry['artifacts'] = {p.name: school.checksum(p) for p in folder.iterdir() if p.is_file()}
        report['cases'].append(entry); school.save(out/'report.json', report)
        print(json.dumps({'prepared': index, 'status': entry['status']}), flush=True)
        if entry['status'] != 'ready': break  # never silently drop an inconvenient case
    if len(report['cases']) == 24 and all(c['status'] == 'ready' for c in report['cases']):
        folder = out/'case-24'; folder.mkdir()
        school.save(folder/'request.json', {'system': RULES, 'user': RECREATE_BRIEF,
            'image': {'path': str(source_path.parent/'preview.png'), 'sha256': school.checksum(source_path.parent/'preview.png')}})
        report['cases'].append({'id': 24, 'kind': 'whole_recreation', 'status': 'ready',
                               'artifacts': {'request.json': school.checksum(folder/'request.json')}})
        report['status'] = 'frozen'
    else:
        report['status'] = 'preparation_failed'
    school.save(out/'report.json', report)
    return out, report


def load_exam(path):
    report = practice.read(path)
    if (report.get('schema') != SCHEMA or report.get('status') != 'frozen' or report.get('thresholds') != THRESHOLDS
            or [c.get('id') for c in report.get('cases', [])] != list(range(25))):
        raise ValueError('Complete frozen 25-case exam required')
    source_path = school.checked(Path(report['source_report']))
    school.require_checksum(source_path, report['source_sha256'])
    school.require_checksum(source_path.parent/'reference-review.json', report['reference_review_sha256'])
    source_report, source, measured = reference(source_path)
    if metadata(source_report) != metadata(report): raise ValueError('Exam split changed')
    expected_image = {'path': str(source_path.parent/'preview.png'), 'sha256': school.checksum(source_path.parent/'preview.png')}
    for entry in report['cases']:
        folder = path.parent/f"case-{entry['id']:02d}"
        if entry['status'] != 'ready': raise ValueError('Incomplete case')
        names = ({'request.json'} if entry['id'] == 24 else
                 {'fault-request.json', 'fault-response.json', 'faulty.svg', 'fault-render.json', 'preview.png', 'preview.pdf', 'request.json'})
        if set(entry['artifacts']) != names: raise ValueError('Complete case evidence required')
        for name, digest in entry['artifacts'].items(): school.require_checksum(folder/name, digest)
        if entry['id'] == 24:
            expected = {'system': RULES, 'user': RECREATE_BRIEF, 'image': expected_image}
            if entry['kind'] != 'whole_recreation': raise ValueError('Whole recreation is mandatory')
        else:
            case = practice.plan(source, entry['id'])
            if entry['kind'] != 'attribute_restoration' or entry['case'] != case: raise ValueError('Frozen fault plan changed')
            if practice.read(folder/'fault-request.json') != practice.fault_request(source, case, source_path):
                raise ValueError('Fault request changed')
            response = practice.read(folder/'fault-response.json')
            if any(response[key] != report['fault_config'][key] for key in ('model', 'digest')):
                raise ValueError('Fault author changed')
            faulty = practice.apply_fault(source, response['content'], case)
            if faulty.encode() != (folder/'faulty.svg').read_bytes(): raise ValueError('Fault is not the model operation')
            expected = practice.repair_request(faulty, measured, practice.read(folder/'fault-render.json'), case, expected_image)
        if practice.read(folder/'request.json') != expected: raise ValueError('Pupil request changed')
    return report, source, measured


def replay(raw, entry, folder):
    if entry['kind'] == 'attribute_restoration':
        faulty = (folder/'faulty.svg').read_bytes().decode('utf-8')
        result, edits = patch.apply_edits(faulty, raw, [entry['case']['element']])
        if len(edits) != 1 or edits[0]['attribute'] != entry['case']['attribute']:
            raise ValueError('Only the declared attribute may be repaired')
    else:
        result = parse_response(raw)
    return result


def score(raw, entry, folder, source, measured, reference_image, output):
    result = replay(raw, entry, folder)
    (output/'artwork.svg').write_text(result)
    school.check_idle()
    rendered = asyncio.run(render(result, output))  # strict deliverable PDF checks
    school.save(output/'render.json', rendered)
    comparison = compare(measured['layout'], rendered['layout'], reference_image, output/'preview.png')
    exact = result.encode() == source.encode()
    return {'comparison': comparison, 'byte_exact': exact,
            'passed': comparison['mechanical_checks_passed'] and (exact if entry['kind'] == 'attribute_restoration' else True)}


def evaluate(path, resume=None):
    exam, source, measured = load_exam(path); school.check_idle()
    config = configuration() | {'num_ctx': 8192, 'num_thread': 4, 'timeout_seconds': 180}
    if resume is None:
        out = Path(tempfile.mkdtemp(prefix='exam-answer-', dir=school.ROOT))
        report = {'schema': 'vector-exam-answer.v1', 'status': 'running', **metadata(exam),
                  'exam': str(path), 'exam_sha256': school.checksum(path), 'config': config, 'results': [],
                  'training_exported': False, 'training_started': False, 'production_changed': False,
                  'service_readiness_proven': False, 'implementation_sha256': school.checksum(Path(__file__))}
    else:
        report = verify_answers(resume, allow_interrupted=True); out = resume.parent
        if (report['status'] != 'interrupted' or report['exam'] != str(path) or report['config'] != config
                or not report['results'] or report['results'][-1].get('error_type') not in {'OSError', 'RuntimeError'}):
            raise ValueError('Only an unchanged infrastructure-interrupted exam may resume')
        last = report['results'][-1]
        archive = out/f"interruption-{len(report.get('interruptions', []))+1:03d}"; archive.mkdir()
        shutil.copyfile(resume, archive/'report.json')
        original = out/f"case-{last['id']:02d}"; backup = archive/original.name; backup.mkdir()
        for name in last['artifacts']: shutil.copyfile(original/name, backup/name)
        report.setdefault('interruptions', []).append({'snapshot': str(archive/'report.json'),
            'sha256': school.checksum(archive/'report.json'), 'case': last['id'],
            'resumed_implementation_sha256': school.checksum(Path(__file__))})
        report['results'].pop(); report['status'] = 'running'
    school.save(out/'report.json', report)
    print(json.dumps({'answers': str(out/'report.json')}), flush=True)
    for entry in exam['cases'][len(report['results']):]:
        folder = path.parent/f"case-{entry['id']:02d}"; output = out/f"case-{entry['id']:02d}"; output.mkdir(exist_ok=resume is not None)
        request = practice.read(folder/'request.json'); started = time.monotonic()
        result = {'id': entry['id'], 'kind': entry['kind'], 'status': 'started'}
        try:
            fmt = patch.EDIT_SCHEMA if entry['kind'] == 'attribute_restoration' else SVG_SCHEMA
            limit = 400 if entry['kind'] == 'attribute_restoration' else 2400
            if resume is not None and (output/'answer-response.json').exists():
                if practice.read(output/'answer-request.json') != request: raise ValueError('Preserved request changed')
                captured = practice.read(output/'answer-response.json')
                if any(captured[key] != config[key] for key in ('model', 'digest')): raise ValueError('Preserved author changed')
                raw = captured['content']; result['reused_captured_response'] = True
            else:
                raw = practice.call(config | {'format': fmt, 'num_predict': limit}, request, output, 'answer')
            result.update(score(raw, entry, folder, source, measured, Path(request['image']['path']), output), status='scored')
        except Exception as exc:
            result.update(status='failed', passed=False, error_type=type(exc).__name__, error=str(exc)[:240])
        result['seconds'] = round(time.monotonic()-started, 3)
        result['artifacts'] = {p.name: school.checksum(p) for p in output.iterdir() if p.is_file()}
        report['results'].append(result); school.save(out/'report.json', report)
        print(json.dumps({'answered': entry['id'], 'status': result['status'], 'passed': result['passed']}), flush=True)
        if result.get('error_type') not in {None, 'ValueError'}: break
    load_exam(path); school.require_checksum(path, report['exam_sha256'])
    report['status'] = 'completed' if len(report['results']) == 25 else 'interrupted'
    report['totals'] = {kind: {'passed': sum(r['passed'] for r in report['results'] if r['kind'] == kind),
                             'answered': sum(r['kind'] == kind for r in report['results'])}
                        for kind in ('attribute_restoration', 'whole_recreation')}
    school.save(out/'report.json', report)
    return out, report


def verify_answers(path, *, allow_interrupted=False):
    report = practice.read(path)
    count = len(report.get('results', []))
    if (report.get('schema') != 'vector-exam-answer.v1'
            or report.get('status') not in ({'completed', 'interrupted'} if allow_interrupted else {'completed'})
            or not 1 <= count <= 25 or (report['status'] == 'completed' and count != 25)
            or [r.get('id') for r in report.get('results', [])] != list(range(count))):
        raise ValueError('Complete exam answers required')
    exam_path = school.checked(Path(report['exam']))
    school.require_checksum(exam_path, report['exam_sha256'])
    exam, source, measured = load_exam(exam_path)
    if metadata(report) != metadata(exam): raise ValueError('Answer split changed')
    names = {'answer-request.json', 'answer-response.json', 'artwork.svg', 'render.json', 'preview.png', 'preview.pdf'}
    for result, entry in zip(report['results'], exam['cases']):
        output = path.parent/f"case-{entry['id']:02d}"; folder = exam_path.parent/output.name
        if (result.get('kind') != entry['kind'] or type(result.get('passed')) is not bool
                or result.get('status') not in {'scored', 'failed'}
                or set(result.get('artifacts', {}))-names):
            raise ValueError('Bound result fields required')
        for name, digest in result['artifacts'].items(): school.require_checksum(output/name, digest)
        if result['status'] == 'failed':
            if result['passed']: raise ValueError('Failed output cannot pass')
            continue
        if set(result['artifacts']) != names: raise ValueError('Complete scored evidence required')
        request = practice.read(folder/'request.json')
        if practice.read(output/'answer-request.json') != request: raise ValueError('Candidate prompt changed')
        response = practice.read(output/'answer-response.json')
        if any(response[key] != report['config'][key] for key in ('model', 'digest')):
            raise ValueError('Candidate identity changed')
        svg = replay(response['content'], entry, folder)
        if svg.encode() != (output/'artwork.svg').read_bytes(): raise ValueError('Candidate artwork changed')
        rendered = practice.read(output/'render.json')
        if rendered.get('render_purpose') != 'deliverable': raise ValueError('Strict output rendering required')
        pdf_checks(output/'preview.pdf', validate_svg(svg)['texts'])
        comparison = compare(measured['layout'], rendered['layout'], Path(request['image']['path']), output/'preview.png')
        exact = svg.encode() == source.encode()
        passed = comparison['mechanical_checks_passed'] and (exact if entry['kind'] == 'attribute_restoration' else True)
        if (comparison != result['comparison'] or result['byte_exact'] != exact or result['passed'] != passed):
            raise ValueError('Candidate score differs from independent replay')
    totals = {kind: {'passed': sum(r['passed'] for r in report['results'] if r['kind'] == kind),
                     'answered': sum(r['kind'] == kind for r in report['results'])}
              for kind in ('attribute_restoration', 'whole_recreation')}
    if report['totals'] != totals: raise ValueError('Exam totals changed')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare', type=Path); group.add_argument('--evaluate', type=Path)
    group.add_argument('--verify', type=Path)
    group.add_argument('--resume', type=Path)
    parser.add_argument('--run', action='store_true'); args = parser.parse_args()
    if args.verify: print(json.dumps({'verified': str(args.verify), 'totals': verify_answers(args.verify)['totals']}))
    elif not args.run: print(json.dumps({'model_called': False, 'training_started': False}))
    else:
        if args.resume:
            previous = practice.read(args.resume)
            out, report = evaluate(Path(previous['exam']), resume=args.resume)
        else:
            out, report = prepare(args.prepare) if args.prepare else evaluate(args.evaluate)
        print(json.dumps({'report': str(out/'report.json'), 'status': report['status']}))
        raise SystemExit(int(report['status'] not in {'frozen', 'completed'}))
