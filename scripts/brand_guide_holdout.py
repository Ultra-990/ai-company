"""Frozen unseen guide-review metadata fixtures; no artwork generation or training."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time

from scripts import brand_guide_revision as guide

CONTRACT = 'brand-guide-review-holdout.v1'
# Evaluator-authored factual metadata fixtures, not client deliverables.
# Expected flags are never sent to the model.
CASES = (
    ('north-pantry', [
        'Use the dark ink for text and the green accent for small decorative details.',
        'The delivered wordmark uses Arial Light at weight 300.',
        'Leave clear space at least one capital-letter height around the full logo.',
        'Print the supplied dark monochrome logo directly on black paper.'], [False, True, False, True]),
    ('harvest-room', [
        'Use Arial Bold for the wordmark and Georgia Regular for the supporting card text.',
        'Retain the supplied green accent and light paper colors in the identity.',
        'Below 18 mm, use the separately delivered symbol-only small variant.',
        'The supplied logo remains legible at every size on every background.'], [False, False, True, True]),
    ('morning-table', [
        'The supplied logo wordmark uses Georgia Regular.',
        'Keep clear space equal to the wordmark capital height around the logo.',
        'The full logo has been tested and remains readable at a minimum width of 9 mm.',
        'Use the supplied dark monochrome ink on a light background.'], [True, False, True, False]),
    ('field-kitchen', [
        'Use the separate wordmark-only SVG in the delivery when space is narrow.',
        'The 240-pixel preview guarantees legibility at any print size.',
        'Keep the logo proportions unchanged when placing it on a light field.',
        'Preserve the supplied Arial wordmark and Georgia supporting typography.'], [True, True, False, False]),
)


def data(case):
    identity, rules, _ = case
    return {'restaurant': identity, 'fixture_kind': 'synthetic evaluator-authored metadata, not an actual delivered project',
        'plan': {'ink': '#203040', 'paper': '#FAFAF5', 'accent': '#6A9030', 'monochrome_ink': '#203040',
                 'heading_font': 'Arial', 'body_font': 'Georgia', 'guidelines': deepcopy(rules)},
        'actual_asset_texts': {'logo-selected': [{'text': identity, 'font_family': 'Arial', 'font_weight': '700', 'font_size': '48'}],
            'business-card': [{'text': 'Contact', 'font_family': 'Georgia', 'font_weight': '400', 'font_size': '28'}]},
        'small_preview_pixels': [240, 144], 'small_svg_identical_to_selected': True,
        'verified_minimum_print_width_mm': None, 'printer_specifications_supplied': False,
        'delivered_files': [n+'.'+e for n in ('logo-a', 'logo-b', 'logo-selected', 'logo-small', 'logo-monochrome', 'business-card')
                            for e in ('svg', 'png', 'pdf')]+['style-plan.json', 'brand-guide.md', 'manifest.json']}


def run(*, expanded=False):
    suite = sys.modules[__name__]
    reviewer = guide
    if expanded:
        from scripts import brand_plan_holdout as suite
        reviewer = suite.REVIEWER
    cases = suite.CASES
    total = sum(len(c[2]) for c in cases)
    b = guide.brand; resources = b.school.check_idle()
    out = Path(tempfile.mkdtemp(prefix='guide-holdout-', dir=b.ROOT))
    config = b.configuration() | {'sampling_profile': 'bounded-default.v1', 'think': False,
        'num_ctx': 8192, 'num_predict': 1800, 'num_thread': 4, 'timeout_seconds': 90}
    manifest = {'schema': suite.CONTRACT, 'cases': cases, 'config': config, 'expected_flags_withheld': True}
    if expanded: manifest['inputs'] = [suite.data(c) for c in cases]
    b.school.save(out/'exam.json', manifest)
    code = out/'implementation'; code.mkdir()
    for name in ('brand_guide_holdout.py', 'brand_guide_revision.py', 'brand_school.py'):
        shutil.copyfile(Path(__file__).parent/name, code/name)
    if expanded:
        for name in ('brand_plan_review.py', 'brand_plan_holdout.py'):
            shutil.copyfile(Path(__file__).parent/name, code/name)
    report = {'schema': suite.CONTRACT, 'status': 'running', 'config': config, 'resources_before': resources,
        'exam_sha256': b.school.checksum(out/'exam.json'), 'results': [], 'training_exported': False,
        'autonomy_qualified': False, 'production_changed': False}
    started = time.monotonic(); print(json.dumps({'output': str(out)}), flush=True)
    try:
        for index, case in enumerate(cases):
            payload = manifest['inputs'][index] if expanded else suite.data(case)
            raw = b.call(out, case[0], reviewer.REVIEW_SYSTEM, json.dumps(payload), reviewer.REVIEW_SCHEMA, config)
            review = reviewer.review_value(raw)
            flags = {r['index']: r['verdict'] != 'supported' for r in review['reviews']}
            report['results'].append({'id': case[0], 'review': review,
                'correct': sum(flags[i] == expected for i, expected in enumerate(case[2]))})
        report.update(status='completed', correct=sum(r['correct'] for r in report['results']), total=total)
    except Exception as exc:
        report.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:400])
    finally:
        report['elapsed_seconds'] = round(time.monotonic()-started, 3)
        report['artifacts'] = {str(p.relative_to(out)): b.school.checksum(p) for p in out.rglob('*') if p.is_file()}
        b.school.save(out/'report.json', report)
    print(json.dumps({'report': str(out/'report.json'), 'status': report['status'], 'correct': report.get('correct'), 'total': total}), flush=True)
    return out, report


def verify(out):
    out = Path(out); read = guide.evidence.read; checksum = guide.brand.school.checksum
    report = read(out/'report.json'); exam = read(out/'exam.json')
    suite = sys.modules[__name__]; reviewer = guide
    if report.get('schema') != CONTRACT:
        from scripts import brand_plan_holdout as suite
        reviewer = suite.REVIEWER
    cases = suite.CASES; total = sum(len(c[2]) for c in cases)
    expected_exam = {'schema': suite.CONTRACT, 'cases': json.loads(json.dumps(cases)), 'config': report['config'], 'expected_flags_withheld': True}
    if suite.CONTRACT != CONTRACT: expected_exam['inputs'] = [suite.data(c) for c in cases]
    if (report.get('schema') != suite.CONTRACT or report.get('status') != 'completed'
            or exam != expected_exam
            or checksum(out/'exam.json') != report['exam_sha256'] or len(report['results']) != 4
            or any(report.get(k) is not False for k in ('training_exported', 'autonomy_qualified', 'production_changed'))):
        raise ValueError('Unchanged complete guide review holdout required')
    for name, digest in report['artifacts'].items():
        path = guide.evidence.bounded(out/name)
        if not path.resolve().is_relative_to(out.resolve()) or checksum(path) != digest: raise ValueError('Holdout artifact changed')
    if {p.name for p in out.glob('*-request.json')} != {c[0]+'-request.json' for c in cases}: raise ValueError('Four requests required')
    correct = 0
    for case, row in zip(cases, report['results']):
        request = read(out/(case[0]+'-request.json')); response = read(out/(case[0]+'-response.json'))
        if request != {'system': reviewer.REVIEW_SYSTEM, 'user': json.dumps(suite.data(case)), 'format': reviewer.REVIEW_SCHEMA}:
            raise ValueError('Expected labels or extra hints entered request')
        if (response['model'], response['digest']) != (report['config']['model'], report['config']['digest']): raise ValueError('Reviewer model changed')
        review = reviewer.review_value(response['content'])
        flags = {r['index']: r['verdict'] != 'supported' for r in review['reviews']}
        score = sum(flags[i] == expected for i, expected in enumerate(case[2]))
        if row != {'id': case[0], 'review': review, 'correct': score}: raise ValueError('Review score changed')
        correct += score
    if report['correct'] != correct or report['total'] != total: raise ValueError('Holdout total changed')
    return {'schema': suite.CONTRACT, 'report_sha256': checksum(out/'report.json'), 'correct': correct, 'total': total,
        'expected_flags_withheld': True, 'independent_reason_review_required': True, 'autonomy_qualified': False}
