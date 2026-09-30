"""Frozen contrastive v13 extraction exam; expectations never enter prompts."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import time

from app.services.local_ollama import configuration
from scripts import brand_explicit_lines_review as protocol
from scripts import brand_school as brand
from scripts.local_retained_batch import RetainedBatch

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
    failure = None
    for arm, profile in PROFILES.items():
        records = []; batch = RetainedBatch(config | BUDGET | {'sampling_profile': profile, 'think': arm == 'deliberate'}, 5)
        try:
            for index, pair in enumerate(pairs()):
                payload, call = request(pair); prefix = arm+'-'+str(index)
                count = len(batch.calls)
                try:
                    content = batch.call(out, prefix, call['system'], call['user'], call['format'], final=index == len(pairs())-1)
                finally:
                    if len(batch.calls) > count:
                        report['call_preflights'].append({'stage': prefix, 'resources': batch.calls[-1]['resources_before']})
                checked = protocol.claims_value(content, payload)
                observed = {row['id']: row['wordmark_lines']['relation'] for row in checked['concepts']}
                records.extend({'id': case[0], 'observed': observed[key], 'passed': observed[key] == case[2]}
                               for key, case in zip(('a', 'b'), pair))
        except Exception as error:
            failure = error
            report['failed_stage'] = arm+'-'+str(len(batch.calls)-1)
            brand.school.save(out/(report['failed_stage']+'-failure.json'), {
                'schema': 'brand-line-claim-failure.v1', 'stage': report['failed_stage'],
                'error_type': type(error).__name__, 'error': str(error),
                'response_saved': (out/(report['failed_stage']+'-response.json')).is_file()})
        finally:
            try: retained = batch.close()
            except Exception as close_error:
                if failure is None:
                    failure = close_error; report['failed_stage'] = arm+'-retention'
                    brand.school.save(out/(report['failed_stage']+'-failure.json'), {
                        'schema': 'brand-line-claim-failure.v1', 'stage': report['failed_stage'],
                        'error_type': type(close_error).__name__, 'error': str(close_error), 'response_saved': False})
                retained = {'schema': 'local-retained-batch.v1', 'calls': batch.calls, 'idle_after': False}
            brand.school.save(out/(arm+'-retained-batch.json'), retained)
        report['arms'][arm] = {'profile': profile, 'cases': records,
                               'score': sum(row['passed'] for row in records)}
        if failure is not None: break
    report.update(status='failed' if failure else 'completed', elapsed_seconds=round(time.monotonic()-started, 3))
    if failure is not None: report.update(error_type=type(failure).__name__, error=str(failure)[:400])
    report['artifacts'] = {str(path.relative_to(out)): brand.school.checksum(path)
                           for path in out.rglob('*') if path.is_file()}
    brand.school.save(out/'report.json', report); return out, report


def verify(out):
    out = Path(out); report = json.loads((out/'report.json').read_text())
    frozen = json.loads((out/'exam.json').read_text())
    if (report.get('schema') != CONTRACT or report.get('status') not in ('completed', 'failed')
            or frozen != manifest(frozen) or report.get('exam_sha256') != brand.school.checksum(out/'exam.json')
            or any(report.get(key) is not False for key in ('training_exported', 'production_changed', 'autonomy_qualified'))):
        raise ValueError('Complete frozen line-claim exam required')
    implementation = {'brand_line_claim_exam.py', 'brand_explicit_lines_review.py',
                      'brand_compact_review.py', 'brand_literal_review.py', 'brand_guide_revision.py'}
    stages = [row.get('stage') for row in report.get('call_preflights', [])]
    ordered = [arm+'-'+str(index) for arm in PROFILES for index in range(len(pairs()))]
    if stages != ordered[:len(stages)] or not stages:
        raise ValueError('Ordered resource preflight required for every attempted call')
    expected_artifacts = {'exam.json'} | {'implementation/'+name for name in implementation}
    expected_artifacts |= {stage+'-request.json' for stage in stages}
    expected_artifacts |= {stage+'-response.json' for stage in stages if (out/(stage+'-response.json')).is_file()}
    started_arms = list(dict.fromkeys(stage.split('-', 1)[0] for stage in stages))
    expected_artifacts |= {arm+'-retained-batch.json' for arm in started_arms}
    if report['status'] == 'failed': expected_artifacts.add(report.get('failed_stage', '')+'-failure.json')
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
    if any(not isinstance(row.get('resources'), dict) for row in report['call_preflights']):
        raise ValueError('Resource preflight required immediately before every model call')
    failure_replayed = False
    for arm, profile in PROFILES.items():
        arm_stages = [stage for stage in stages if stage.startswith(arm+'-')]
        if not arm_stages:
            if arm in report['arms']: raise ValueError('Unattempted arm has results')
            continue
        records = []
        if report['arms'][arm]['profile'] != profile: raise ValueError('Pinned profile changed')
        retained = json.loads((out/(arm+'-retained-batch.json')).read_text())
        if (retained.get('schema') != 'local-retained-batch.v1' or retained.get('idle_after') is not True
                or [row.get('stage') for row in retained.get('calls', [])] != arm_stages):
            raise ValueError('Terminal naturally released retained batch required')
        for index, pair in enumerate(pairs()[:len(arm_stages)]):
            payload, call = request(pair); prefix = arm+'-'+str(index)
            if json.loads((out/(prefix+'-request.json')).read_text()) != call:
                raise ValueError('Prompt includes changed data')
            response_path = out/(prefix+'-response.json')
            if not response_path.is_file():
                if report['status'] != 'failed' or prefix != report.get('failed_stage'):
                    raise ValueError('Missing nonterminal response')
                failure_replayed = True; break
            response = json.loads(response_path.read_text())
            try:
                if (response['model'], response['digest']) != (frozen['model'], frozen['digest']):
                    raise ValueError('Pinned local extractor changed')
                checked = protocol.claims_value(response['content'], payload)
            except Exception as error:
                if (report['status'] != 'failed' or prefix != report.get('failed_stage')
                        or (type(error).__name__, str(error)[:400]) != (report.get('error_type'), report.get('error'))):
                    raise ValueError('Recorded terminal failure does not replay') from error
                failure_replayed = True; break
            observed = {row['id']: row['wordmark_lines']['relation'] for row in checked['concepts']}
            records.extend({'id': case[0], 'observed': observed[key], 'passed': observed[key] == expected[case[0]]}
                           for key, case in zip(('a', 'b'), pair))
        if report['arms'][arm] != {'profile': profile, 'cases': records,
                                   'score': sum(row['passed'] for row in records)}:
            raise ValueError('Line-claim score changed')
    if report['status'] == 'failed':
        failure_record = json.loads((out/(report['failed_stage']+'-failure.json')).read_text())
        if (failure_record.get('schema') != 'brand-line-claim-failure.v1'
                or failure_record.get('stage') != report['failed_stage']
                or (failure_record.get('error_type'), failure_record.get('error')[:400]) != (report.get('error_type'), report.get('error'))
                or not failure_replayed):
            raise ValueError('Bound terminal failure record required')
    return {'schema': CONTRACT, 'report_sha256': brand.school.checksum(out/'report.json'),
            'status': report['status'], 'scores': {arm: value['score'] for arm, value in report['arms'].items()},
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
