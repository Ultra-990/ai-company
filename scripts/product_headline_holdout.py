"""Frozen synthetic copy-review holdout; no product generation or training.

Gold verdicts stay outside every model request. Four bounded calls, no retries
or feedback. A passing classification score still needs independent inspection
of the reasons and does not qualify full product delivery.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import product_headline_probe as probe

product = probe.product
CONTRACT = 'product-headline-holdout.v1'
# Evaluator-written synthetic tests, never lessons or customer deliverables.
# Each tuple is (headline, exhaustive facts, gold verdict).
CASES = (
    ('larch', (
        ('Hydration Until Sundown', ['Capacity: 700 ml', 'Includes: 1 bottle'], 'unsupported'),
        ('Size at a Glance', ['Height: 24 cm', 'Diameter: 7.2 cm'], 'supported'),
        ('Built to Last for Years', ['Body: stainless steel', 'Lid: polypropylene'], 'unsupported'),
        ('Wash by Hand', ['Hand wash only', 'Air dry before storage'], 'supported'),
    )),
    ('fern', (
        ('One Bottle, One Litre', ['Capacity: 1000 ml', 'Includes: 1 bottle'], 'supported'),
        ('Fits Every Car Cup Holder', ['Height: 28 cm', 'Diameter: 8 cm'], 'unsupported'),
        ('A Plastic-Free Choice', ['Body: glass', 'Lid: polypropylene'], 'unsupported'),
        ('Ready for the Dishwasher', ['Dishwasher safe', 'Top rack only'], 'supported'),
    )),
    ('heath', (
        ('Five Hundred Millilitres', ['Capacity: 500 ml', 'Includes: 1 bottle'], 'supported'),
        ('Pocket-Sized for Everyone', ['Height: 26 cm', 'Diameter: 9 cm'], 'unsupported'),
        ('Body and Lid Materials', ['Body: aluminium', 'Lid: polypropylene'], 'supported'),
        ('Sterilise with Boiling Water', ['Hand wash only', 'Do not use boiling water'], 'unsupported'),
    )),
    ('aspen', (
        ('Keeps Water Cold All Day', ['Capacity: 900 ml', 'Includes: 1 bottle'], 'unsupported'),
        ('Measured from Top to Base', ['Height: 30 cm', 'Diameter: 8 cm'], 'supported'),
        ('Recycled Steel Body', ['Body: 90% recycled stainless steel', 'Lid: polypropylene'], 'supported'),
        ('A Lifetime Without Odours', ['Hand wash only', 'Air dry before storage'], 'unsupported'),
    )),
)


def definition(case):
    name, rows = case
    return {'id': name, 'input': {'product_name': name.upper(), 'unknown': ['All properties not explicitly supplied'],
        'panels': [{'panel': panel, 'headline': row[0], 'supplier_facts': row[1]}
                   for panel, row in zip(product.DEFAULT_PANELS, rows)]},
        'gold': {panel: row[2] for panel, row in zip(product.DEFAULT_PANELS, rows)}}


def run():
    config = product.configuration() | {'sampling_profile': 'bounded-default.v1', 'think': False,
        'num_ctx': 8192, 'num_predict': 2048, 'num_thread': 4, 'timeout_seconds': 90}
    resources = product.school.check_idle()
    out = Path(tempfile.mkdtemp(prefix='headline-holdout-', dir=product.ROOT))
    code = out/'implementation'; code.mkdir()
    for name in ('product_headline_holdout.py', 'product_headline_probe.py', 'brand_school.py'):
        shutil.copyfile(Path(__file__).parent/name, code/name)
    shutil.copyfile(Path(__file__).resolve().parents[1]/'app/services/local_ollama.py', code/'local_ollama.py')
    manifest = {'schema': CONTRACT, 'cases': [definition(c) for c in CASES], 'config': config,
        'system': probe.SYSTEM, 'format': probe.schema(), 'max_model_calls': 4,
        'expected_verdict_supplied_to_model': False, 'training_exported': False}
    product.school.save(out/'manifest.json', manifest)
    report = {'schema': CONTRACT, 'status': 'running', 'cases': [], 'resources_before': resources,
        'manifest_sha256': product.school.checksum(out/'manifest.json'), 'training_exported': False,
        'production_changed': False, 'whole_package_accepted': False}
    started = time.monotonic()
    print(json.dumps({'output': str(out)}), flush=True)
    def save():
        report['elapsed_seconds'] = round(time.monotonic()-started, 3)
        report['artifacts'] = {str(p.relative_to(out)): product.school.checksum(p)
            for p in out.rglob('*') if p.is_file() and p.name != 'report.json'}
        product.school.save(out/'report.json', report)
    save()
    try:
        for case in manifest['cases']:
            entry = {'id': case['id']}; report['cases'].append(entry)
            try:
                raw = product.brand.call(out, case['id'], probe.SYSTEM,
                    json.dumps(case['input']), probe.schema(), config)
                review = probe.validate(raw, case['input'])
                product.school.save(out/(case['id']+'-review.json'), review)
                entry['status'] = 'complete'
            except Exception as exc:
                entry.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:600])
            save()
            print(json.dumps(entry), flush=True)
        report['status'] = 'completed'
    finally:
        save()
    return out, report


def assess(out):
    out = Path(out)
    report = probe.revision.read(out/'report.json'); manifest = probe.revision.read(out/'manifest.json')
    checksum = product.school.checksum
    if (report['schema'] != CONTRACT or report['status'] != 'completed'
            or manifest['schema'] != CONTRACT or manifest['cases'] != [definition(c) for c in CASES]
            or manifest['system'] != probe.SYSTEM or manifest['format'] != probe.schema()
            or report['manifest_sha256'] != checksum(out/'manifest.json')
            or manifest['max_model_calls'] != 4
            or manifest['expected_verdict_supplied_to_model'] is not False
            or manifest['training_exported'] is not False
            or any(report[key] is not False for key in ('training_exported', 'production_changed', 'whole_package_accepted'))
            or [row['id'] for row in report['cases']] != [row['id'] for row in manifest['cases']]):
        raise ValueError('Frozen completed holdout required')
    for name, digest in report['artifacts'].items():
        path = probe.revision.bounded(out/name)
        if not path.resolve().is_relative_to(out.resolve()) or checksum(path) != digest:
            raise ValueError('Holdout artifact changed')
    requests = {p.name for p in out.glob('*-request.json')}
    if requests != {case['id']+'-request.json' for case in manifest['cases']}:
        raise ValueError('Exactly one recorded request per frozen case required')
    findings = []
    for case, entry in zip(manifest['cases'], report['cases']):
        name = case['id']
        required = [name+'-request.json']
        if entry['status'] == 'complete': required += [name+'-response.json', name+'-review.json']
        if any(filename not in report['artifacts'] for filename in required):
            raise ValueError('Unbound evaluation artifact')
        request = probe.revision.read(out/(name+'-request.json'))
        if request != {'system': manifest['system'], 'user': json.dumps(case['input']), 'format': manifest['format']}:
            raise ValueError('Request contains hints or differs from frozen input')
        reviews = {}
        if entry['status'] == 'complete':
            response = probe.revision.read(out/(name+'-response.json'))
            if (response['model'], response['digest']) != (manifest['config']['model'], manifest['config']['digest']):
                raise ValueError('Pinned reviewer changed')
            value = probe.validate(response['content'], case['input'])
            if value != probe.revision.read(out/(name+'-review.json')):
                raise ValueError('Review differs from literal model response')
            reviews = {row['panel']: row for row in value['reviews']}
        for panel, expected in case['gold'].items():
            actual = reviews.get(panel, {}).get('verdict', 'missing')
            findings.append({'case': name, 'panel': panel, 'expected': expected, 'actual': actual,
                'exact_match': actual == expected, 'unsafe_approval': expected == 'unsupported' and actual == 'supported',
                'reason': reviews.get(panel, {}).get('reason')})
    return {'schema': CONTRACT, 'report_sha256': checksum(out/'report.json'), 'findings': findings,
        'exact_matches': sum(row['exact_match'] for row in findings), 'total': len(findings),
        'unsafe_approvals': sum(row['unsafe_approval'] for row in findings),
        'independent_reason_review_required': True, 'autonomy_qualified': False, 'training_exported': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--run', action='store_true'); group.add_argument('--assess', type=Path)
    args = parser.parse_args()
    if args.run:
        out, _ = run(); print(json.dumps({'report': str(out/'report.json')}))
    elif args.assess: print(json.dumps(assess(args.assess), indent=2))
    else: print(json.dumps({'cases': [definition(c) for c in CASES], 'model_called': False}))
