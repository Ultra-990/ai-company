"""Frozen contrastive v13 extraction exam; expectations never enter prompts."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import time

from app.services.local_ollama import configuration, OllamaProvider
from scripts import brand_explicit_lines_review as protocol
from scripts import brand_school as brand

CONTRACT = 'brand-line-claim-exam.v1'
PROFILES = {'bounded': 'bounded-default.v1', 'deliberate': 'qwen-deliberate-trial.v1'}
BUDGET = {'num_ctx': 8192, 'num_predict': 900, 'num_thread': 4, 'timeout_seconds': 90}
CASES = (
    ('stacked-wordmark', 'A centered stacked wordmark in Georgia accompanies a restrained seed motif.', 'multiple'),
    ('two-line-name', 'A two-line name in Georgia accompanies a restrained branch motif.', 'multiple'),
    ('name-set-two-lines', 'The wordmark is set on two lines beside a quiet circular motif.', 'multiple'),
    ('single-line-wordmark', 'A single-line wordmark in Georgia sits beside a restrained leaf motif.', 'single'),
    ('name-on-one-line', 'The name is set on one line above a quiet water motif.', 'single'),
    ('symbol-stacked', 'A small seed symbol is stacked above the wordmark in a centered composition.', 'unspecified'),
    ('symbol-below', 'A restrained branch symbol sits below the name in the compact logo.', 'unspecified'),
    ('negated-two-line', 'This is not a two-line wordmark; a small leaf sits beside the centered name.', 'uncertain'),
    ('negated-single-line', 'The centered name is not single-line and sits above a small seed motif.', 'uncertain'),
    ('no-count', 'A Georgia wordmark accompanies a restrained reed and water motif.', 'unspecified'),
)


def manifest(config):
    return {'schema': CONTRACT, 'model': config['model'], 'digest': config['digest'],
            'profiles': PROFILES, 'budget': BUDGET,
            'cases': [{'id': key, 'text': text, 'expected': expected} for key, text, expected in CASES],
            'expected_values_are_prompt_data': False, 'training_export_allowed': False}


def pairs():
    return [CASES[index:index+2] for index in range(0, len(CASES), 2)]


def request(pair):
    texts = {'a': pair[0][1], 'b': pair[1][1]}; payload = protocol.catalogue(texts)
    return payload, {'system': protocol.CLAIM_SYSTEM, 'user': json.dumps(payload),
                     'format': protocol.claim_schema(payload)}


def run():
    config = configuration(); resources = brand.school.check_idle()
    out = Path(tempfile.mkdtemp(prefix='line-claim-exam-', dir=brand.ROOT))
    frozen = manifest(config); brand.school.save(out/'exam.json', frozen)
    code = out/'implementation'; code.mkdir()
    for module in ('brand_line_claim_exam.py', 'brand_explicit_lines_review.py', 'brand_compact_review.py',
                   'brand_literal_review.py', 'brand_guide_revision.py'):
        shutil.copyfile(Path(__file__).parent/module, code/module)
    report = {'schema': CONTRACT, 'status': 'running', 'resources_before': resources,
              'exam_sha256': brand.school.checksum(out/'exam.json'), 'arms': {}, 'call_preflights': [],
              'training_exported': False, 'production_changed': False, 'autonomy_qualified': False}
    started = time.monotonic()
    for arm, profile in PROFILES.items():
        records = []
        provider = OllamaProvider(config | BUDGET | {'sampling_profile': profile, 'think': arm == 'deliberate'})
        for index, pair in enumerate(pairs()):
            payload, call = request(pair); prefix = arm+'-'+str(index)
            brand.school.save(out/(prefix+'-request.json'), call)
            # Recheck immediately before every local inference. A later call
            # must not rely on resources observed before an earlier call.
            report['call_preflights'].append({'stage': prefix, 'resources': brand.school.check_idle()})
            response = provider.complete([{'role': 'system', 'content': call['system']},
                                          {'role': 'user', 'content': call['user']}])
            brand.school.save(out/(prefix+'-response.json'), response)
            checked = protocol.claims_value(response['content'], payload)
            observed = {row['id']: row['wordmark_lines']['relation'] for row in checked['concepts']}
            records.extend({'id': case[0], 'observed': observed[key], 'passed': observed[key] == case[2]}
                           for key, case in zip(('a', 'b'), pair))
        report['arms'][arm] = {'profile': profile, 'cases': records,
                               'score': sum(row['passed'] for row in records)}
    report.update(status='completed', elapsed_seconds=round(time.monotonic()-started, 3))
    report['artifacts'] = {str(path.relative_to(out)): brand.school.checksum(path)
                           for path in out.rglob('*') if path.is_file()}
    brand.school.save(out/'report.json', report); return out, report


def verify(out):
    out = Path(out); report = json.loads((out/'report.json').read_text())
    frozen = json.loads((out/'exam.json').read_text())
    if (report.get('schema') != CONTRACT or report.get('status') != 'completed'
            or frozen != manifest(frozen) or report.get('exam_sha256') != brand.school.checksum(out/'exam.json')
            or any(report.get(key) is not False for key in ('training_exported', 'production_changed', 'autonomy_qualified'))):
        raise ValueError('Complete frozen line-claim exam required')
    implementation = {'brand_line_claim_exam.py', 'brand_explicit_lines_review.py',
                      'brand_compact_review.py', 'brand_literal_review.py', 'brand_guide_revision.py'}
    calls = {arm+'-'+str(index)+suffix for arm in PROFILES for index in range(len(pairs()))
             for suffix in ('-request.json', '-response.json')}
    expected_artifacts = {'exam.json'} | calls | {'implementation/'+name for name in implementation}
    actual_artifacts = {str(path.relative_to(out)) for path in out.rglob('*')
                        if path.is_file() and path.name != 'report.json'}
    if set(report.get('artifacts', {})) != expected_artifacts or actual_artifacts != expected_artifacts:
        raise ValueError('Exact fully bound exam artifact set required')
    for name, digest in report['artifacts'].items():
        if brand.school.checksum(out/name) != digest: raise ValueError('Exam artifact changed')
    for name in implementation:
        if (out/'implementation'/name).read_bytes() != (Path(__file__).parent/name).read_bytes():
            raise ValueError('Required implementation snapshot changed')
    expected = {key: relation for key, _, relation in CASES}
    if ([row.get('stage') for row in report.get('call_preflights', [])]
            != [arm+'-'+str(index) for arm in PROFILES for index in range(len(pairs()))]
            or any(not isinstance(row.get('resources'), dict) for row in report['call_preflights'])):
        raise ValueError('Resource preflight required immediately before every model call')
    for arm, profile in PROFILES.items():
        records = []
        if report['arms'][arm]['profile'] != profile: raise ValueError('Pinned profile changed')
        for index, pair in enumerate(pairs()):
            payload, call = request(pair); prefix = arm+'-'+str(index)
            if json.loads((out/(prefix+'-request.json')).read_text()) != call:
                raise ValueError('Prompt includes changed data')
            response = json.loads((out/(prefix+'-response.json')).read_text())
            if (response['model'], response['digest']) != (frozen['model'], frozen['digest']):
                raise ValueError('Pinned local extractor changed')
            checked = protocol.claims_value(response['content'], payload)
            observed = {row['id']: row['wordmark_lines']['relation'] for row in checked['concepts']}
            records.extend({'id': case[0], 'observed': observed[key], 'passed': observed[key] == expected[case[0]]}
                           for key, case in zip(('a', 'b'), pair))
        if report['arms'][arm] != {'profile': profile, 'cases': records,
                                   'score': sum(row['passed'] for row in records)}:
            raise ValueError('Line-claim score changed')
    return {'schema': CONTRACT, 'report_sha256': brand.school.checksum(out/'report.json'),
            'scores': {arm: report['arms'][arm]['score'] for arm in PROFILES},
            'cases_per_arm': len(CASES), 'independent_review_required': True,
            'autonomy_qualified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--run', action='store_true'); action.add_argument('--verify', type=Path)
    args = parser.parse_args()
    if args.verify: print(json.dumps(verify(args.verify), indent=2))
    else:
        path, result = run(); print(json.dumps({'output': str(path), 'status': result['status']}))
