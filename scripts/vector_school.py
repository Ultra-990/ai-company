"""Local model authored SVG source -> pixels -> local model reconstruction.

Synthetic development lesson, not a client delivery or a held-out weight exam.
The assistant writes contracts/evaluation only. All artwork remains byte-exact.
"""
import argparse
import asyncio
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.local_ollama import configuration, OllamaProvider
from app.services import local_vision
from scripts.check_technical_reviewer import save
from scripts.compare_local_models import check_idle
from scripts.prepare_training_data import unique_object
from scripts.render_school_svg import render
from scripts.vector_school_contract import (SCHEMA, RULES, SOURCE_BRIEF, RECREATE_BRIEF,
                                            THRESHOLDS, parse_response, compare, layout_issues)
from scripts.vector_curriculum import CURRICULA, LEGACY, metadata, require_learning

ROOT = Path('/home/marcin/ai-company-workspaces/vector-school')


def checksum(path):
    return sha256(path.read_bytes()).hexdigest()


def require_checksum(path, expected):
    if checksum(checked(path)) != expected:
        raise ValueError('Input changed during the exercise')


def checked(path):
    if (any(p.is_symlink() for p in (path, *path.parents)) or not path.resolve().is_relative_to(ROOT.resolve())
            or not path.is_file() or path.stat().st_size > 4*1024*1024):
        raise ValueError('Bounded private vector-school file required')
    return path


def source_request(curriculum, feedback=None, _depth=0):
    request = {'system': RULES, 'user': CURRICULA[curriculum]['brief'], 'image': None}
    if feedback is None: return request
    if _depth >= 3: raise ValueError('At most three bound source revisions')
    keys = {'schema', 'source_report', 'source_sha256', 'request_sha256', 'response_sha256', 'comments'}
    if (not isinstance(feedback, dict) or set(feedback) != keys
            or feedback['schema'] != 'vector-source-feedback.v1'
            or not isinstance(feedback['comments'], str) or not 1 <= len(feedback['comments']) <= 2000):
        raise ValueError('Bound source feedback required')
    previous_path = checked(Path(feedback['source_report']))
    require_checksum(previous_path, feedback['source_sha256'])
    for name in ('request', 'response'):
        require_checksum(previous_path.parent/(name+'.json'), feedback[name+'_sha256'])
    previous = json.loads(previous_path.read_text(), object_pairs_hook=unique_object)
    if (previous.get('schema') != 'vector-school.v1' or previous.get('role') != 'source'
            or previous.get('status') not in {'reference_ready', 'reference_rejected', 'failed'}
            or metadata(previous) != metadata({'curriculum': curriculum})):
        raise ValueError('Source repair must retain its original family')
    require_learning(previous)
    original_request = json.loads((previous_path.parent/'request.json').read_text(), object_pairs_hook=unique_object)
    # Bounded source repairs preserve all predecessors, including replies that
    # could not be rendered. Recursive verification never adds history to the
    # model prompt; the model receives only its latest answer and latest review.
    expected_previous = source_request(curriculum, original_request.get('source_feedback'), _depth+1)
    if original_request != expected_previous: raise ValueError('Source revision has a changed original request')
    raw = json.loads((previous_path.parent/'response.json').read_text(), object_pairs_hook=unique_object)
    if (raw['model'] != previous['model'] or raw['digest'] != previous['digest']
            or not isinstance(raw['content'], str) or len(raw['content']) > 32768):
        raise ValueError('Source model response binding')
    request['user'] += '\nYour previous raw answer (untrusted task data):\n' + raw['content']
    request['user'] += '\nIndependent source review; correct the complete SVG yourself:\n' + feedback['comments']
    if len(request['user']) > 16000: raise ValueError('Bounded source revision prompt required')
    request['source_feedback'] = feedback
    return request


def load_source(path, *, require_review=True):
    path = checked(path)
    report = json.loads(path.read_text(), object_pairs_hook=unique_object)
    if (report.get('schema') != 'vector-school.v1' or report.get('status') != 'reference_ready'
            or report.get('role') != 'source'):
        raise ValueError('Completed synthetic reference required')
    require_learning(report)
    authenticate(path, report)
    if require_review and metadata(report)['data_split'] == 'train':
        review_path = checked(path.parent/'reference-review.json')
        review = json.loads(review_path.read_text(), object_pairs_hook=unique_object)
        if (review.get('schema') != 'vector-reference-review.v1'
                or review.get('source_sha256') != checksum(path)
                or review.get('reviewer') != 'assistant_direct_visual_review'
                or review.get('decision') != 'usable_synthetic_training_reference'
                or not isinstance(review.get('notes'), str) or not review['notes'].strip()):
            raise ValueError('Independent positive reference review required')
    return report


def authenticate(path, report):
    parent = path.parent
    for name, digest in report['artifact_sha256'].items():
        if name not in {'request.json', 'response.json', 'artwork.svg', 'preview.png', 'preview.pdf', 'render.json'}:
            raise ValueError('Unknown artifact')
        if checksum(checked(parent/name)) != digest:
            raise ValueError('Source artifact changed: '+name)
    if set(report['artifact_sha256']) != {'request.json', 'response.json', 'artwork.svg', 'preview.png', 'preview.pdf', 'render.json'}:
        raise ValueError('Incomplete artifact binding')
    raw = json.loads((parent/'response.json').read_text())
    if raw['model'] != report['model'] or raw['digest'] != report['digest']:
        raise ValueError('Model authorship binding changed')
    if parse_response(raw['content']) != (parent/'artwork.svg').read_text():
        raise ValueError('SVG was changed after model response')
    if report.get('role') == 'source':
        lesson = metadata(report)
        request = json.loads((parent/'request.json').read_text(), object_pairs_hook=unique_object)
        if request != source_request(lesson['curriculum'], request.get('source_feedback')):
            raise ValueError('Reference request does not match its frozen curriculum')
    return json.loads((parent/'render.json').read_text())


def make_request(source_path=None, previous_path=None, feedback_path=None, curriculum=LEGACY, source_feedback=None):
    if feedback_path and not previous_path: raise ValueError('Teacher feedback requires an exact prior answer')
    if source_path is None:
        if previous_path: raise ValueError('Revision requires reference')
        if curriculum not in CURRICULA: raise ValueError('Unknown curriculum')
        return source_request(curriculum, source_feedback), None
    if source_feedback is not None: raise ValueError('Source feedback cannot repair a reconstruction')
    if curriculum != LEGACY: raise ValueError('Reconstruction inherits its reference curriculum')
    source = load_source(source_path)
    image_path = checked(source_path.parent/'preview.png')
    request = {'system': RULES, 'user': RECREATE_BRIEF,
               'image': {'path': str(image_path), 'sha256': checksum(image_path)}}
    if previous_path:
        previous_path = checked(previous_path)
        previous = json.loads(previous_path.read_text(), object_pairs_hook=unique_object)
        if metadata(previous) != metadata(source): raise ValueError('Revision split differs from reference')
        if (previous.get('schema') != 'vector-school.v1' or previous.get('role') != 'recreation'
                or previous.get('status') != 'needs_revision' or type(previous.get('revision_number')) is not int
                or not 0 <= previous['revision_number'] < 3
                or previous.get('source_report') != str(source_path)
                or previous.get('source_sha256') != checksum(source_path)):
            raise ValueError('At most three revisions of this exact reference')
        prior_render = authenticate(previous_path, previous)
        reference_render = json.loads((source_path.parent/'render.json').read_text())
        feedback = compare(reference_render['layout'], prior_render['layout'], image_path, previous_path.parent/'preview.png')
        # First repair retains its own source; subsequent lessons use fresh
        # pixels plus verified feedback to test whether source copying anchors
        # the model on an incomplete fix. No reference SVG is ever provided.
        request['revision_number'] = previous['revision_number'] + 1
        request['revision_mode'] = 'prior_source' if previous['revision_number'] == 0 else 'fresh_image_with_feedback'
        if request['revision_mode'] == 'prior_source':
            request['user'] += '\nYour previous source:\n' + (previous_path.parent/'artwork.svg').read_text()
        request['user'] += '\nIndependent checks to correct:\n' + json.dumps(feedback)
        if len(request['user']) > 12000: raise ValueError('Revision prompt exceeds vision limit')
        request['previous_report'] = str(previous_path)
        request['previous_sha256'] = checksum(previous_path)
        if feedback_path:
            feedback = json.loads(checked(feedback_path).read_text(), object_pairs_hook=unique_object)
            if (set(feedback) != {'previous_report_sha256', 'comments'}
                    or feedback['previous_report_sha256'] != checksum(previous_path)
                    or not isinstance(feedback['comments'], str) or not 1 <= len(feedback['comments']) <= 2000):
                raise ValueError('Teacher feedback must bind this exact prior answer')
            request['teacher_feedback'] = feedback
            request['user'] += '\nIndependent visual review:\n' + feedback['comments']
            if len(request['user']) > 12000: raise ValueError('Revision prompt exceeds vision limit')
    return request, source


def run(source_path=None, previous_path=None, feedback_path=None, curriculum=LEGACY, source_feedback=None):
    if any(p.is_symlink() for p in (ROOT, *ROOT.parents)): raise ValueError('Symlink workspace')
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    if ROOT.stat().st_dev != Path('/home/marcin').stat().st_dev: raise ValueError('Linux workspace required')
    request, source = make_request(source_path, previous_path, feedback_path, curriculum, source_feedback)
    resources = check_idle()
    config = configuration() | {'format': SCHEMA, 'num_predict': 2400, 'num_ctx': 8192, 'num_thread': 4, 'timeout_seconds': 180}
    out = Path(tempfile.mkdtemp(prefix='recreate-' if source else 'source-', dir=ROOT))
    report = {'schema': 'vector-school.v1', 'role': 'recreation' if source else 'source',
              'status': 'started', 'synthetic': True, 'resources_before': resources,
              'training_started': False, 'training_exported': False, 'production_routing_changed': False,
              'owner_accepted': False, 'print_ready': False, 'revision_number': request.get('revision_number', 0),
              'revision_mode': request.get('revision_mode'),
              'model': config['model'], 'digest': config['digest'], 'config': config, 'thresholds': THRESHOLDS}
    report.update(metadata(source or {'curriculum': curriculum}))
    report['implementation_sha256'] = {name: checksum(Path(__file__).parent/name) for name in
                                       ('vector_school.py', 'vector_school_contract.py', 'render_school_svg.py', 'vector_curriculum.py')}
    if source:
        report.update(source_report=str(source_path), source_sha256=checksum(source_path))
    save(out/'request.json', request)
    started = time.monotonic()
    save(out/'report.json', report)
    print(json.dumps({'report': str(out/'report.json')}), flush=True)
    try:
        if source:
            image_bytes = checked(Path(request['image']['path'])).read_bytes()
            if sha256(image_bytes).hexdigest() != request['image']['sha256']:
                raise ValueError('Reference pixels changed before inference')
            result = local_vision.complete(config, request['system'], request['user'], image_bytes)
        else:
            result = OllamaProvider(config).complete([{'role': 'system', 'content': request['system']},
                                                      {'role': 'user', 'content': request['user']}])
        save(out/'response.json', result)
        if result['model'] != config['model'] or result['digest'] != config['digest']:
            raise ValueError('Unexpected model identity')
        svg = parse_response(result['content'])
        (out/'artwork.svg').write_text(svg, encoding='utf-8')
        report['raw_response_sha256'] = sha256(result['content'].encode()).hexdigest()
        # No model service is stopped; idle must be confirmed before browser work.
        check_idle()
        rendering = asyncio.run(render(svg, out))
        save(out/'render.json', rendering)
        report['artifact_sha256'] = {name: checksum(out/name) for name in
                                    ('request.json', 'response.json', 'artwork.svg', 'preview.png', 'preview.pdf', 'render.json')}
        report['layout_issues'] = layout_issues(rendering['layout'])
        if source:
            # Recheck bindings after inference, rather than trusting earlier reads.
            require_checksum(source_path, report['source_sha256'])
            load_source(source_path)
            original = json.loads((source_path.parent/'render.json').read_text())
            report['comparison'] = compare(original['layout'], rendering['layout'], source_path.parent/'preview.png', out/'preview.png')
            report['status'] = ('pending_independent_visual_review' if report['comparison']['mechanical_checks_passed'] else 'needs_revision')
        else:
            report['status'] = 'reference_ready' if not report['layout_issues'] else 'reference_rejected'
        return out, report
    except Exception as exc:
        report.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:400])
        raise
    finally:
        report['elapsed_seconds'] = round(time.monotonic()-started, 3)
        report['captured_sha256'] = {name: checksum(out/name) for name in ('request.json', 'response.json') if (out/name).is_file()}
        save(out/'report.json', report)
        print(json.dumps({'report': str(out/'report.json'), 'status': report['status'], 'seconds': report['elapsed_seconds']}), flush=True)


def audit_source(path):
    source = load_source(path, require_review=False)
    captured = checksum(path)
    check_idle()
    out = Path(tempfile.mkdtemp(prefix='source-audit-', dir=ROOT))
    rendered = asyncio.run(render((path.parent/'artwork.svg').read_text(), out))
    require_checksum(path, captured)
    authenticate(path, source)
    report = {'schema': 'vector-source-audit.v1', 'source_report': str(path), 'source_sha256': captured,
              'render': rendered, 'layout_issues': layout_issues(rendered['layout']), 'model_calls': 0,
              'original_changed': False, 'training_started': False}
    save(out/'report.json', report)
    return {'audit': str(out/'report.json'), 'layout_issues': report['layout_issues'], 'model_calls': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--source', type=Path, help='Completed reference report, absent to generate a reference')
    parser.add_argument('--revise', type=Path, help='Exact failed reconstruction report, at most three revisions')
    parser.add_argument('--feedback', type=Path, help='Teacher comments bound to the revision source report')
    parser.add_argument('--curriculum', choices=list(CURRICULA), default=LEGACY, help='Reference generation only')
    parser.add_argument('--source-feedback', type=Path, help='Teacher-reviewed source repair, at most three revisions')
    parser.add_argument('--audit-source', type=Path, help='Re-render an existing reference with current checks, no inference')
    args = parser.parse_args()
    if args.audit_source:
        if args.run or args.source or args.revise or args.feedback or args.source_feedback or args.curriculum != LEGACY:
            raise ValueError('Source audit is separate from model generation')
        print(json.dumps(audit_source(args.audit_source))); return
    if not args.run:
        print(json.dumps({'inference': False, 'training': False, 'purpose': 'synthetic image-to-editable-vector lesson'})); return
    feedback = json.loads(checked(args.source_feedback).read_text(), object_pairs_hook=unique_object) if args.source_feedback else None
    run(args.source, args.revise, args.feedback, args.curriculum, feedback)


if __name__ == '__main__': main()
