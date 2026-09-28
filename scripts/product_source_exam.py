"""Frozen new synthetic briefs for paired source-generation evaluation.

Same model, style, brief, schema, sampler and three-call limit in both arms.
Only the combined/focused instruction changes. This small source-only exam
cannot establish delivery quality or autonomous commercial readiness.
"""
import json
import asyncio
from pathlib import Path
import shutil
import tempfile
import time

from app.services.local_ollama import configuration
from scripts import brand_school as brand
from scripts import product_infographic_school as product
from scripts import vector_school as school

EXAM_VERSION = 'product-source-new-briefs.v1'
CASES = (
    {'product_name': 'SUMMIT 700', 'family': 'summit-source-exam-001'},
    {'product_name': 'RIVER 450', 'family': 'river-source-exam-001'},
    {'product_name': 'GROVE 800', 'family': 'grove-source-exam-001'},
)


def audit(path):
    """Apply today's checks separately; never rewrite an earlier exam score."""
    path = Path(path)
    if (any(p.is_symlink() for p in (path, *path.parents))
            or not path.resolve().is_relative_to(product.ROOT.resolve())):
        raise ValueError('Private source exam required')
    previous = json.loads((path/'report.json').read_text())
    manifest = json.loads((path/'exam.json').read_text())
    if (previous['status'] != 'completed' or manifest['schema'] != EXAM_VERSION
            or previous['exam_sha256'] != school.checksum(path/'exam.json')):
        raise ValueError('Completed unchanged exam required')
    for name, digest in previous['artifacts'].items():
        entry = path/name
        if (any(p.is_symlink() for p in (entry, *entry.parents))
                or not entry.resolve().is_relative_to(path.resolve()) or school.checksum(entry) != digest):
            raise ValueError('Exam artifact changed')
    out = Path(tempfile.mkdtemp(prefix='source-exam-audit-', dir=product.ROOT))
    report = {'schema': 'product-source-exam-audit.v1', 'source_report_sha256': school.checksum(path/'report.json'),
              'source_exam': str(path), 'contract': product.SOURCE_FIDELITY_CONTRACT, 'cases': [],
              'model_called': False, 'training_exported': False, 'visual_acceptance': False}
    original = product.BRIEF
    try:
        for brief, case in zip(manifest['cases'], previous['cases'], strict=True):
            if brief['family'] != case['family']: raise ValueError('Exam family order changed')
            product.BRIEF = brief
            source_folder = path/brief['family']
            style = product.style_value((source_folder/'style.json').read_text())
            for arm, result in case['arms'].items():
                if not result['measured_pass']: continue
                folder = out/(brief['family']+'-'+arm); folder.mkdir()
                source = source_folder/arm/'accepted.svg'
                svg = source.read_text(); (folder/'artwork.svg').write_text(svg)
                measured = asyncio.run(product.render(svg, folder, profile='product_source'))
                school.save(folder/'render.json', measured)
                issues = product.quality_issues(measured) + product.source_fidelity_issues(
                    measured, label_check=True, label_bounds=True, style=style)
                report['cases'].append({'family': brief['family'], 'arm': arm, 'source_sha256': school.checksum(source),
                                        'issues': issues, 'measured_pass': not issues})
    finally:
        product.BRIEF = original
    report['artifacts'] = {str(p.relative_to(out)): school.checksum(p) for p in out.rglob('*') if p.is_file()}
    school.save(out/'report.json', report)
    print(json.dumps({'report': str(out/'report.json'), 'cases': report['cases']}), flush=True)
    return out, report


def run():
    resources = school.check_idle()
    out = Path(tempfile.mkdtemp(prefix='source-exam-', dir=product.ROOT))
    config = configuration() | {'num_ctx': 8192, 'num_predict': 4096, 'num_thread': 4, 'timeout_seconds': 180}
    original_brief = product.BRIEF
    cases = [dict(original_brief, **case, split='test') for case in CASES]
    manifest = {'schema': EXAM_VERSION, 'cases': cases, 'config': config,
                'source_fidelity_contract': product.SOURCE_FIDELITY_CONTRACT,
                'system_prompts': {arm: product.SYSTEM+'\n'+product.stage_rules('source', focused=focused)
                                   for arm, focused in [('combined', False), ('focused', True)]},
                'max_calls_per_arm': 3, 'evaluation_only': True, 'training_export_allowed': False}
    school.save(out/'exam.json', manifest)
    report = {'schema': 'product-source-exam-result.v1', 'status': 'running',
              'exam_sha256': school.checksum(out/'exam.json'), 'resources_before': resources,
              'cases': [], 'training_started': False, 'training_exported': False,
              'production_changed': False, 'visual_acceptance': False,
              'limitations': 'Three source-only briefs with identical physical dimensions. Not full products or proof of independence.'}
    implementation = out/'implementation'; implementation.mkdir()
    for name in ('product_source_exam.py', 'product_infographic_school.py', 'brand_school.py',
                 'render_school_svg.py', 'vector_school_contract.py'):
        shutil.copyfile(Path(__file__).parent/name, implementation/name)
    school.save(out/'report.json', report)
    print(json.dumps({'output': str(out)}), flush=True)
    started = time.monotonic()
    try:
        for index, brief in enumerate(cases):
            product.BRIEF = brief
            folder = out/brief['family']; folder.mkdir()
            style = brand.validated_call(folder, 'style', product.SYSTEM,
                json.dumps({'brief': brief})+'\nChoose five literal palette colors (ink, paper, accent, blue body_color, dark cap_color) and heading/body fonts.',
                product.Style.model_json_schema(), config, product.style_value)
            school.save(folder/'style.json', style)
            user = json.dumps({'brief': brief, 'style': style,
                'supplier_dimensions': {'height_cm': 24, 'diameter_cm': 7},
                'task': 'ACTIVE STAGE: SOURCE ONLY. Draw the synthetic reference bottle. '
                        'The measured silhouette height/width must match 24/7 within 10%, including cap and base. '
                        'Use a recognizable cylindrical bottle with shaped shoulders, screw cap and rounded base. '
                        'Print the exact product name legibly inside the body. You choose all actual geometry.'})
            result = {'family': brief['family'], 'arms': {}}
            report['cases'].append(result)
            arms = ('combined', 'focused') if index % 2 == 0 else ('focused', 'combined')
            for arm in arms:
                attempt_dir = folder/arm; attempt_dir.mkdir()
                outcome = {'measured_pass': False}
                result['arms'][arm] = outcome
                try:
                    svg = brand.validated_call(attempt_dir, 'source', manifest['system_prompts'][arm], user,
                        product.schema('source', style), config, product.checked_scene(attempt_dir, 'source', style))
                    (attempt_dir/'accepted.svg').write_text(svg)
                    outcome['measured_pass'] = True
                except ValueError as exc:
                    outcome['error'] = str(exc)
                outcome['model_calls'] = len(list(attempt_dir.glob('*-response.json')))
                school.save(out/'report.json', report)
                print(json.dumps({'family': brief['family'], 'arm': arm, **outcome}), flush=True)
        report.update(status='completed', scores={arm: sum(c['arms'][arm]['measured_pass'] for c in report['cases'])
                                                 for arm in ('combined', 'focused')})
    except Exception as exc:
        report.update(status='failed', error_type=type(exc).__name__, error=str(exc))
    finally:
        product.BRIEF = original_brief
        report['elapsed_seconds'] = round(time.monotonic()-started, 3)
        report['artifacts'] = {str(p.relative_to(out)): school.checksum(p) for p in out.rglob('*')
                               if p.is_file() and p.name != 'report.json'}
        school.save(out/'report.json', report)
    print(json.dumps({'report': str(out/'report.json'), 'status': report['status'], 'scores': report.get('scores')}), flush=True)
    return out, report
