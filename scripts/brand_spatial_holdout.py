"""Frozen language-only claim extraction test; no geometry or labels in prompts."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
from scripts import brand_spatial_review as spatial

CONTRACT = 'brand-spatial-claim-holdout.v1'
CASES = (
    ('vertical', {'a': 'The wordmark sits under the leaf emblem.', 'b': 'A small bowl is positioned below the restaurant name.'}, {'a': ['above'], 'b': ['below']}),
    ('horizontal', {'a': 'The text is placed to the right of the mark.', 'b': 'A narrow flame stands to the right of the name.'}, {'a': ['left'], 'b': ['right']}),
    ('integration', {'a': 'The restaurant name is surrounded by a ring.', 'b': 'The leaf is integrated into the first letter of the wordmark.'}, {'a': ['surrounds'], 'b': ['overlaps']}),
    ('absence', {'a': 'The mark and name are arranged next to one another horizontally.', 'b': 'A friendly plant motif evokes freshness.'}, {'a': ['side_by_side'], 'b': ['unspecified']}),
    ('compound', {'a': 'The symbol is positioned above and to the left of the wordmark.', 'b': 'The mark sits beneath a wordmark and the wordmark is above the mark.'}, {'a': ['above', 'left'], 'b': ['below']}),
    ('internal', {'a': 'A wave cradles a flame; the wordmark is below this symbol.', 'b': 'A bowl carries steam, with the name in a line underneath.'}, {'a': ['above'], 'b': ['above']}),
    ('intersection', {'a': 'An arc runs through the wordmark.', 'b': 'The name is inside a circular border.'}, {'a': ['overlaps'], 'b': ['surrounds']}),
    ('reversed', {'a': 'The name sits to the left of the circular icon.', 'b': 'A circle above the letters contains a leaf shape.'}, {'a': ['right'], 'b': ['above']}),
)


def run(*, subjects=False):
    suite = sys.modules[__name__]; reviewer = spatial
    if subjects:
        from scripts import brand_spatial_subject_holdout as suite
        reviewer = suite.REVIEWER
    cases = suite.CASES
    b = spatial.base.legacy.brand; resources = b.school.check_idle()
    out = Path(tempfile.mkdtemp(prefix='spatial-holdout-', dir=b.ROOT))
    config = b.configuration() | {'sampling_profile': 'bounded-default.v1', 'think': False,
        'num_ctx': 8192, 'num_predict': 1800, 'num_thread': 4, 'timeout_seconds': 90}
    b.school.save(out/'exam.json', {'schema': suite.CONTRACT, 'cases': cases, 'config': config, 'geometry_and_labels_withheld': True})
    code = out/'implementation'; code.mkdir()
    for name in ('brand_spatial_holdout.py', 'brand_spatial_review.py', 'brand_plan_review.py', 'brand_guide_revision.py', 'brand_school.py'):
        shutil.copyfile(Path(__file__).parent/name, code/name)
    if subjects:
        for name in ('brand_spatial_subject_review.py', 'brand_spatial_subject_holdout.py'):
            shutil.copyfile(Path(__file__).parent/name, code/name)
    shutil.copyfile(Path(__file__).parents[1]/'app/services/local_ollama.py', code/'local_ollama.py')
    report = {'schema': suite.CONTRACT, 'status': 'running', 'config': config, 'resources_before': resources,
        'exam_sha256': b.school.checksum(out/'exam.json'), 'results': [], 'training_exported': False,
        'autonomy_qualified': False, 'production_changed': False}
    started = time.monotonic(); print(json.dumps({'output': str(out)}), flush=True)
    try:
        for name, texts, expected in cases:
            raw = b.call(out, name, reviewer.CLAIM_SYSTEM, json.dumps(texts), reviewer.CLAIM_SCHEMA, config)
            claims = reviewer.claims_value(raw, texts)
            actual = {r['id']: {c['relation'] for c in r['claims']} for r in claims['concepts']}
            report['results'].append({'id': name, 'claims': claims,
                'correct': sum(actual[key] == set(expected[key]) for key in texts)})
        report.update(status='completed', correct=sum(r['correct'] for r in report['results']), total=16)
    except Exception as exc:
        report.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:400])
    finally:
        report['elapsed_seconds'] = round(time.monotonic()-started, 3)
        report['artifacts'] = {str(p.relative_to(out)): b.school.checksum(p) for p in out.rglob('*') if p.is_file()}
        b.school.save(out/'report.json', report)
    print(json.dumps({'report': str(out/'report.json'), 'status': report['status'], 'correct': report.get('correct'), 'total': 16}), flush=True)
    return out, report


def verify(out):
    out = Path(out); b = spatial.base.legacy.brand; read = spatial.base.legacy.evidence.read
    report = read(out/'report.json'); exam = read(out/'exam.json')
    suite = sys.modules[__name__]; reviewer = spatial
    if report.get('schema') != CONTRACT:
        from scripts import brand_spatial_subject_holdout as suite
        reviewer = suite.REVIEWER
    cases = suite.CASES
    if (report.get('schema') != suite.CONTRACT or report.get('status') != 'completed'
            or exam != {'schema': suite.CONTRACT, 'cases': json.loads(json.dumps(cases)), 'config': report['config'], 'geometry_and_labels_withheld': True}
            or b.school.checksum(out/'exam.json') != report['exam_sha256'] or len(report['results']) != 8
            or any(report.get(k) is not False for k in ('training_exported', 'autonomy_qualified', 'production_changed'))):
        raise ValueError('Complete frozen language-only spatial holdout required')
    for name, digest in report['artifacts'].items():
        p = spatial.base.legacy.evidence.bounded(out/name)
        if not p.resolve().is_relative_to(out.resolve()) or b.school.checksum(p) != digest: raise ValueError('Spatial holdout artifact changed')
    if {p.name for p in out.glob('*-request.json')} != {c[0]+'-request.json' for c in cases}: raise ValueError('Exactly eight bounded requests required')
    correct = 0
    for (name, texts, expected), row in zip(cases, report['results']):
        request = read(out/(name+'-request.json')); response = read(out/(name+'-response.json'))
        if request != {'system': reviewer.CLAIM_SYSTEM, 'user': json.dumps(texts), 'format': reviewer.CLAIM_SCHEMA}:
            raise ValueError('Actual geometry, labels or extra hints entered the extraction prompt')
        if (response['model'], response['digest']) != (report['config']['model'], report['config']['digest']): raise ValueError('Extractor changed')
        claims = reviewer.claims_value(response['content'], texts)
        actual = {r['id']: {c['relation'] for c in r['claims']} for r in claims['concepts']}
        score = sum(actual[key] == set(expected[key]) for key in texts)
        if row != {'id': name, 'claims': claims, 'correct': score}: raise ValueError('Claim extraction or score changed')
        correct += score
    if report['correct'] != correct or report['total'] != 16: raise ValueError('Spatial holdout total changed')
    return {'schema': suite.CONTRACT, 'report_sha256': b.school.checksum(out/'report.json'), 'correct': correct, 'total': 16,
        'geometry_and_labels_withheld': True, 'independent_quote_review_required': True, 'autonomy_qualified': False}
