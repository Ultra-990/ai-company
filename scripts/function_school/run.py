"""Bounded model-authored functional course; isolated tests, repairs, pending SFT.

Runs train exercises, not held-out evaluation or weight training. No generated
Python is imported, compiled or executed on the host. No production task writes.
"""
import argparse
import ast
import fcntl
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
import tempfile
import time
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.services.container_runner import ContainerRunner, configuration as runner_configuration
from app.services.local_ollama import OllamaProvider, configuration, generation_options
from scripts.compare_local_models import check_idle
from scripts.draft_repair_examples import APP, SCHEMA, parse_source, inspect_run
from scripts.function_school.curriculum import CASES
from scripts.prepare_training_data import validate_record, validate_dataset

ROOT = Path('/home/marcin/ai-company-workspaces/function-school')
INSTRUCTION = '''Write the entire requested solution.py yourself. Return only JSON
{"source":"complete Python source"}. No Markdown, tests, runner changes or claims
of execution. Pure Python standard library only: no files, network, processes,
test introspection or external side effects. Treat test output as diagnostic data.
Repair general rules, not individual expected values. Keep the source concise.'''


def digest(value):
    return sha256(value.encode()).hexdigest()


def save(path, value):
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def suite_hash():
    return digest(json.dumps(CASES, sort_keys=True, ensure_ascii=False))


def test_count(case):
    # Parse ONLY teacher-authored tests, never a model response.
    return sum(isinstance(node, ast.FunctionDef) and node.name.startswith('test_')
               for node in ast.walk(ast.parse(case['tests'])))


def messages_for(case, source, feedback):
    task = {'brief':case['brief'], 'previous_source':source,
            'independent_feedback':feedback}
    return [{'role':'system','content':INSTRUCTION},
            {'role':'user','content':json.dumps(task, ensure_ascii=False)}]


def verified_lessons(case, attempts):
    if not attempts or attempts[-1]['status'] != 'passed':
        return []
    failed = set()
    for attempt in attempts[:-1]:
        for name in re.findall(r'^(?:FAIL|ERROR): (test_\w+) \(', attempt.get('test_log',''), re.M):
            failed.add(name)
    return [{'check':name, 'lesson':case['lessons'][name]}
            for name in sorted(failed & case['lessons'].keys())]


def teach_case(case, folder, config, run_config, max_attempts, provider, runner,
               preflight=check_idle, deadline=None, clock=time.monotonic):
    entry = {'id':case['id'], 'family':case['family'], 'status':'running',
             'tests_sha256':digest(case['tests']), 'attempts':[], 'lessons':[]}
    folder.mkdir()
    save(folder/'contract.json', case)
    (folder/'test_app.py').write_text(case['tests'], encoding='utf-8')
    source = ''; feedback = ''
    for number in range(1, max_attempts+1):
        if deadline is not None and clock() >= deadline:
            entry['status'] = 'budget_exhausted'; break
        attempt_dir = folder/f'attempt-{number}'; attempt_dir.mkdir()
        attempt = {'number':number, 'status':'running'}
        entry['attempts'].append(attempt)
        save(folder/'report.json', entry)
        stage = 'preflight'
        try:
            preflight()
            messages = messages_for(case, source, feedback)
            save(attempt_dir/'request.json', messages)
            attempt['request_sha256'] = sha256((attempt_dir/'request.json').read_bytes()).hexdigest()
            stage = 'generation'
            response = provider.complete(messages)
            save(attempt_dir/'response.json', response)
            attempt['response_sha256'] = digest(response['content'])
            attempt['tokens'] = response['eval_count']
            attempt['seconds'] = response['elapsed_seconds']
            if response.get('model') != config['model'] or response.get('digest') != config['digest']:
                raise ValueError('Model provenance mismatch')
            stage = 'parse'
            source = parse_source(response['content'])
            (attempt_dir/'solution.py').write_text(source, encoding='utf-8')
            attempt['source_sha256'] = digest(source)
            stage = 'examination'
            preflight()
            result = runner.run({'app.py':APP, 'test_app.py':case['tests'], 'solution.py':source},
                                run_config, 'aic-package-'+uuid4().hex)
            save(attempt_dir/'execution.json', result)
            attempt['execution_sha256'] = sha256((attempt_dir/'execution.json').read_bytes()).hexdigest()
            tested = inspect_run(result, result.get('exit_code') == 0)
            attempt['test_log'] = tested['tests_log']
            counts = re.findall(r'^Ran (\d+) tests? in ', tested['tests_log'], re.M)
            if tested['tests_ok'] and counts != [str(test_count(case))]:
                raise ValueError('Passing report did not execute all expected tests')
            attempt['status'] = 'passed' if tested['tests_ok'] else 'failed_tests'
            feedback = tested['tests_log']
        except Exception as exc:
            attempt['status'] = 'invalid_output' if stage == 'parse' else 'infrastructure_error'
            attempt['error_stage'] = stage
            attempt['error_type'] = type(exc).__name__
            # Original response and execution evidence remain private on disk.
            feedback = 'Invalid output: return exactly one JSON source string, complete and within 12000 characters.'
        entry['status'] = attempt['status']
        save(folder/'report.json', entry)
        print(json.dumps({'case':case['id'], 'attempt':number, 'status':attempt['status']}), flush=True)
        if attempt['status'] in ('passed','infrastructure_error'):
            break
    entry['lessons'] = verified_lessons(case, entry['attempts'])
    save(folder/'report.json', entry)
    return entry


def training_candidate(case, entry, folder, config, course_id):
    """Recheck exact evidence; never approve or alter the model's response."""
    if entry['status'] != 'passed':
        raise ValueError('Only passing attempts can be collected')
    attempt = entry['attempts'][-1]
    root = folder/f"attempt-{attempt['number']}"
    messages = json.loads((root/'request.json').read_text())
    if sha256((root/'request.json').read_bytes()).hexdigest() != attempt['request_sha256']:
        raise ValueError('Changed request')
    response = json.loads((root/'response.json').read_text())
    source = (root/'solution.py').read_text()
    if (parse_source(response['content']) != source or digest(source) != attempt['source_sha256']
            or digest(response['content']) != attempt['response_sha256']
            or response.get('model') != config['model'] or response.get('digest') != config['digest']):
        raise ValueError('Changed model response/source/provenance')
    if digest((folder/'test_app.py').read_text()) != digest(case['tests']):
        raise ValueError('Changed examiner')
    if messages != messages_for(case,
            json.loads(messages[-1]['content'])['previous_source'],
            json.loads(messages[-1]['content'])['independent_feedback']):
        raise ValueError('Changed instruction/contract')
    evidence = root/'execution.json'
    if sha256(evidence.read_bytes()).hexdigest() != attempt['execution_sha256']:
        raise ValueError('Changed execution evidence')
    tested = inspect_run(json.loads(evidence.read_text()), True)
    if (tested['tests_log'] != attempt['test_log'] or
            re.findall(r'^Ran (\d+) tests? in ', tested['tests_log'], re.M) != [str(test_count(case))]):
        raise ValueError('Changed or incomplete execution evidence')
    row = {'version':'company-sft.v1', 'id':course_id+'-'+case['id'],
           'family':case['family'], 'split':'train',
           'skill':'repair' if len(entry['attempts'])>1 else 'coding',
           'source':{'kind':'synthetic','reference':str(folder/'report.json'),
                     'rights':'Original synthetic teacher contract and local model response; no customer data.',
                     'privacy_checked':False},
           'messages':messages+[{'role':'assistant','content':response['content']}],
           'review':{'status':'pending','reviewer':'','reviewed_on':None,
                     'evidence':[{'kind':'independent_test','reference':str(evidence),
                                  'sha256':sha256(evidence.read_bytes()).hexdigest()}],
                     'note':'Requires code, privacy, rights and tokenization review. Train exercise, not holdout or production acceptance.'}}
    validate_record(row)
    return row


def execute(config, run_config, max_attempts=2, budget_seconds=1200, provider=None, runner=None,
            preflight=check_idle, clock=time.monotonic):
    if type(max_attempts) is not int or not 1 <= max_attempts <= 3:
        raise ValueError('One to three attempts required')
    if type(budget_seconds) is not int or not 60 <= budget_seconds <= 1800:
        raise ValueError('Budget must be 60..1800 seconds')
    if any(p.is_symlink() for p in (ROOT,*ROOT.parents)):
        raise ValueError('Symlink workspace')
    ROOT.mkdir(parents=True, exist_ok=True)
    if ROOT.stat().st_dev != Path('/home').stat().st_dev:
        raise ValueError('Linux workspace required')
    if (ROOT/'.course.lock').is_symlink():
        raise ValueError('Symlink lock')
    with (ROOT/'.course.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return _execute(config, run_config, max_attempts, budget_seconds,
                        provider or OllamaProvider(config), runner or ContainerRunner(), preflight, clock)


def _execute(config, run_config, max_attempts, budget_seconds, provider, runner, preflight, clock):
    output = Path(tempfile.mkdtemp(prefix='course-', dir=ROOT))
    started = clock()
    report = {'schema':'functional-school.v1', 'status':'running', 'suite_sha256':suite_hash(),
              'model':config['model'], 'digest':config['digest'], 'sampling':generation_options(config),
              'max_attempts_per_case':max_attempts, 'budget_seconds':budget_seconds,
              'budget_scope':'No new attempt after deadline; in-flight model/container calls have separate timeouts.',
              'cases':[], 'expected_cases':len(CASES), 'candidates':0,
              'weights_trained':False, 'automatically_approved':0, 'production_routing_changed':False,
              'split':'train', 'authorship':{'solutions':'local_model','contracts_tests_orchestration':'assistant'},
              'limitations':'Development exercises only; not holdout, full applications, security audit or weight improvement.'}
    rows = []
    save(output/'report.json', report)
    print(json.dumps({'output':str(output)}), flush=True)
    try:
        for case in CASES:
            if clock()-started >= budget_seconds:
                report['status'] = 'budget_exhausted'; break
            entry = teach_case(case, output/case['id'], config, run_config, max_attempts,
                               provider, runner, preflight, started+budget_seconds, clock)
            report['cases'].append(entry)
            save(output/'report.json', report)
            if entry['status'] == 'passed':
                rows.append(training_candidate(case, entry, output/case['id'], config, output.name))
                validate_dataset(''.join(json.dumps(row, ensure_ascii=False)+'\n' for row in rows).encode())
                # Append only after full evidence validation; preserve already collected examples on failure.
                with (output/'candidates.jsonl').open('a', encoding='utf-8') as stream:
                    stream.write(json.dumps(rows[-1], ensure_ascii=False)+'\n')
                report['candidates'] = len(rows)
            if entry['status'] in ('infrastructure_error','budget_exhausted'):
                report['status'] = entry['status']; break
        else:
            report['status'] = 'passed' if all(c['status']=='passed' for c in report['cases']) else 'needs_more_learning'
    except Exception as exc:
        report['status'] = 'infrastructure_error'; report['error_type'] = type(exc).__name__
    finally:
        report['elapsed_seconds'] = round(clock()-started,3)
        report['first_attempt_passes'] = sum(c['attempts'][0]['status']=='passed' for c in report['cases'] if c['attempts'])
        report['final_passes'] = sum(c['status']=='passed' for c in report['cases'])
        report['complete'] = len(report['cases']) == len(CASES) and all(
            c['status'] in ('passed','failed_tests','invalid_output') for c in report['cases'])
        candidates_path = output/'candidates.jsonl'
        report['candidates_sha256'] = sha256(candidates_path.read_bytes()).hexdigest() if candidates_path.exists() else None
        save(output/'report.json', report)
    return output, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--max-attempts', type=int, choices=(1,2,3), default=2)
    parser.add_argument('--budget-seconds', type=int, default=1200)
    args = parser.parse_args()
    if not args.run:
        print(json.dumps({'suite_sha256':suite_hash(), 'cases':[{'id':c['id'],'tests':test_count(c)} for c in CASES],
                          'model_invoked':False, 'weights_trained':False})); return 0
    config = configuration() | {'num_ctx':16384, 'num_predict':3200, 'num_thread':4,
                                'timeout_seconds':180, 'format':SCHEMA}
    output, report = execute(config, runner_configuration(), args.max_attempts, args.budget_seconds)
    print(json.dumps({'report':str(output/'report.json'), 'status':report['status'],
                      'candidates':report['candidates'], 'weights_trained':False}), flush=True)
    return 0 if report['status']=='passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
