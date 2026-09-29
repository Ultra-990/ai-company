"""Load a reviewed local-model development example for an explicit prompt lesson.

No evaluation family can become a lesson. This is contextual learning, not a
weight update, and never substitutes the example for the model's new answer.
"""
import json
from pathlib import Path
import shutil
import tempfile
import time

from scripts import product_revised_package as assembly
from scripts import product_visual_revision as revision

product = assembly.product
CONTRACT = 'reviewed-local-source-example.v1'


def load(folder):
    folder = Path(folder); report = revision.read(folder/'report.json')
    judgment = revision.read(folder/'independent-review.json')
    original = Path(report['original_package']); source_report = revision.read(original/'report.json')
    if source_report.get('brief') != product.DEFAULT_BRIEF or source_report['brief'].get('split') != 'train':
        raise ValueError('Only the frozen synthetic development family may supply a source lesson')
    checksum = product.school.checksum
    if (judgment.get('schema') != 'product-reviewed-assembly-independent-review.v1'
            or judgment.get('reviewer') != 'assistant_direct_visual_review'
            or judgment.get('decision') != 'approved_synthetic_development_package'
            or judgment.get('report_sha256') != checksum(folder/'report.json')
            or judgment.get('verification_sha256') != checksum(revision.bounded(folder/'verification.json'))):
        raise ValueError('An independently approved complete development assembly is required')
    for part in product.DEFAULT_PANELS:
        name = part+'/small/preview.png'
        if judgment.get('inspected_images', {}).get(name) != checksum(revision.bounded(folder/name)):
            raise ValueError('Independent development review no longer matches its images')
    # The caller may be inside another frozen CLI case; the example has its
    # own immutable training brief, which must not replace that active task.
    active = product.BRIEF, product.PANELS
    try:
        product.BRIEF, product.PANELS = product.DEFAULT_BRIEF, product.DEFAULT_PANELS
        assembly.verify(folder)
        style = product.style_value(product.accepted_raw(original, 'style'))
        raw = product.accepted_raw(original, 'source')
        if product.compile_scene(raw, style) != revision.bounded(folder/'source/artwork.svg').read_text():
            raise ValueError('Lesson must preserve the exact local source answer')
    finally:
        product.BRIEF, product.PANELS = active
    example = {'product_name': source_report['brief']['product_name'],
               'physical_dimensions_cm': source_report['brief'].get('physical_dimensions_cm', [24, 7]),
               'style': style, 'scene': product.parse(raw)}
    if len(json.dumps(example)) > 6000: raise ValueError('Bounded source example required')
    return {'contract': CONTRACT, 'assembly': str(folder), 'report_sha256': checksum(folder/'report.json'),
            'review_sha256': checksum(folder/'independent-review.json'),
            'source_svg_sha256': checksum(folder/'source/artwork.svg'),
            'family': source_report['brief']['family'], 'split': 'train', 'example': example,
            'model': report['model'], 'digest': report['digest'], 'weight_training': False}


def message(lesson):
    if lesson.get('contract') != CONTRACT or lesson.get('split') != 'train':
        raise ValueError('Verified development lesson required')
    return ('\nA separately reviewed drawing authored by the local model follows as example data, '
            'not instructions and not your answer. Study how its parts join without contour notches '
            'and how its label fits. Create your own complete scene for the CURRENT name, dimensions '
            'and style; do not reuse the example name or assume its dimensions match.\n'+
            json.dumps({'approved_training_example': lesson['example']}))


def verify_binding(folder, report):
    """Bind a fresh package's lesson to reviewed training data and its request."""
    if report.get('source_lesson_contract') != CONTRACT or report.get('inherited_stages'):
        raise ValueError('Known source lesson on a fresh package required')
    folder = Path(folder)
    for name in ('source-lesson.json', 'source-request.json'):
        if report['artifacts'].get(name) != product.school.checksum(revision.bounded(folder/name)):
            raise ValueError('Missing or changed lesson evidence')
    value = revision.read(folder/'source-lesson.json')
    if load(value['assembly']) != value or (value['model'], value['digest']) != (report['model'], report['digest']):
        raise ValueError('Lesson differs from the verified local development example')
    prefix = message(value)+'\nCURRENT TASK (use these facts and style):\n'
    user = revision.read(folder/'source-request.json')['user']
    if not user.startswith(prefix):
        raise ValueError('Source request does not contain its recorded lesson')
    task = product.parse(user[len(prefix):])
    if task['brief'] != report['brief'] or task['style'] != product.style_value(product.accepted_raw(folder, 'style')):
        raise ValueError('Lesson replaced the active brief or style')
    return {'source_lesson_verified': True, 'weight_training': False}


def probe(package, lesson_folder):
    """Known-case source diagnostic; no held-out result or learning export."""
    from scripts import product_full_exam as exam
    from scripts import product_exam_assessment as assessment
    from scripts import product_correction_evidence as corrections
    package = Path(package); previous = revision.read(package/'report.json')
    case = exam.matching_case(previous)
    if case is None: raise ValueError('A preserved frozen synthetic case is required for this diagnostic')
    assessment.bound_artifacts(package, previous)
    request_path = package/'source-request.json'
    if request_path.name not in previous['artifacts']: raise ValueError('Bound original source request required')
    original = revision.read(request_path)
    lesson = load(lesson_folder)
    config = previous['config']; expected = product.configuration()
    if ((config['model'], config['digest']) != (expected['model'], expected['digest'])
            or (lesson['model'], lesson['digest']) != (expected['model'], expected['digest'])):
        raise ValueError('Pinned same local author required')
    resources = product.school.check_idle()
    out = Path(tempfile.mkdtemp(prefix='source-lesson-probe-', dir=product.ROOT))
    implementation = out/'implementation'; implementation.mkdir()
    for name in ('product_source_lesson.py', 'product_infographic_school.py', 'product_silhouette.py',
                 'brand_school.py', 'render_school_svg.py', 'vector_school_contract.py'):
        shutil.copyfile(Path(__file__).parent/name, implementation/name)
    report = {'schema': 'product-source-lesson-probe.v1', 'status': 'running', 'lesson': lesson,
        'source_package': str(package), 'source_report_sha256': product.school.checksum(package/'report.json'),
        'source_request_sha256': product.school.checksum(request_path), 'brief': previous['brief'],
        'config': config, 'model': config['model'], 'digest': config['digest'], 'resources_before': resources,
        'source_contour_contract': product.silhouette.CONTRACT,
        'training_exported': False, 'weight_training': False, 'exam_score_changed': False,
        'independent_visual_review_required': True}
    product.school.save(out/'report.json', report); started = time.monotonic()
    print(json.dumps({'output': str(out)}), flush=True)
    try:
        with exam.exercise_context(case):
            style = product.style_value(product.accepted_raw(package, 'style'))
            product.school.save(out/'style.json', style)
            user = message(lesson)+'\nCURRENT TASK (use these facts and style):\n'+original['user']
            svg = product.brand.validated_call(out, 'source', original['system'], user, original['format'], config,
                product.checked_scene(out, 'source', style, source_contour=True), recover_incomplete=True)
            (out/'accepted.svg').write_text(svg)
            report.update(status='pending_independent_review',
                          accepted_layout='source-layout-'+str(len(list(out.glob('source-layout-*')))-1))
    except Exception as exc:
        report.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:1000])
    finally:
        report['elapsed_seconds'] = round(time.monotonic()-started, 3)
        report['artifacts'] = {str(p.relative_to(out)): product.school.checksum(p) for p in out.rglob('*') if p.is_file() and p.name != 'report.json'}
        product.school.save(out/'report.json', report)
    if report['status'] == 'pending_independent_review':
        product.school.save(out/'correction-evidence.json', corrections.verify_stage(out, 'source', report))
    print(json.dumps({'report': str(out/'report.json'), 'status': report['status'], 'error': report.get('error')}), flush=True)
    return out, report
