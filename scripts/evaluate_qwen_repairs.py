"""Opt-in frozen repair evaluation, one attempt per case, no training export.

Code runs only in the isolated guest. All failures are retained; infrastructure
failures make the assessment incomplete, not a model quality score.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
import time
from uuid import uuid4

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.container_runner import ContainerRunner, configuration as runner_configuration
from app.services.local_ollama import configuration, ensure_idle, OllamaProvider, generation_options
from scripts.draft_repair_examples import APP, SCHEMA, INSTRUCTION, parse_source, inspect_run, messages_for
from scripts.qwen_evaluation_catalog import load_suite, CHECKSUM

ROOT = Path('/home/marcin/ai-company-workspaces/qwen-training')


def summary(cases, expected):
    completed = sum(c.get('status') in ('passed','failed_tests','invalid_output') for c in cases)
    passed = sum(c.get('status')=='passed' for c in cases)
    return {'expected':expected,'attempted':len(cases),'assessed':completed,'passed':passed,
            'complete':len(cases)==expected and completed==expected,
            'pass_rate':passed/expected if completed==expected else None}


def evaluate_case(case, provider, runner, run_config):
    entry = {'id':case['id'],'family':case['family'],'status':'infrastructure_error',
             'source_before_sha256':sha256(case['broken'].encode()).hexdigest(),
             'tests_sha256':sha256(case['tests'].encode()).hexdigest()}
    stage = 'baseline'
    try:
        files = {'app.py':APP,'test_app.py':case['tests'],'solution.py':case['broken']}
        entry['before'] = runner.run(files,run_config,'aic-package-'+uuid4().hex)
        before = inspect_run(entry['before'],False)
        if 'FAIL:' not in before['tests_log']:
            raise ValueError('Baseline lacks a failing assertion')
        entry['messages'] = messages_for(case,before['tests_log'])
        stage = 'model'
        ensure_idle()
        entry['result'] = provider.complete(entry['messages'])
        stage = 'parse'
        source = parse_source(entry['result']['content'])
        entry['source_after_sha256'] = sha256(source.encode()).hexdigest()
        stage = 'test'
        entry['after'] = runner.run(files|{'solution.py':source},run_config,'aic-package-'+uuid4().hex)
        # Exit=1 with healthy harness/isolation and real assertions is a model
        # failure; timeouts/OOM/cleanup trouble remain incomplete infrastructure.
        after = inspect_run(entry['after'],entry['after'].get('exit_code')==0)
        entry['status'] = 'passed' if after['tests_ok'] else 'failed_tests'
    except Exception as exc:
        entry['error_stage'] = stage
        entry['error_type'] = type(exc).__name__
        if stage == 'parse': entry['status'] = 'invalid_output'
    return entry


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true')
    args=parser.parse_args()
    suite=load_suite()
    if not args.run:
        print(json.dumps({'suite_sha256':CHECKSUM,'cases':len(suite['cases']),
                          'model_invoked':False,'training_started':False}))
        return 0
    for parent in [*ROOT.parents,ROOT]:
        if parent.is_symlink(): raise ValueError('Symlink in evaluation path')
    ROOT.mkdir(parents=True,exist_ok=True)
    if ROOT.stat().st_dev != Path('/home').stat().st_dev:
        raise ValueError('Linux /home filesystem required')
    output=Path(tempfile.mkdtemp(prefix='repair-evaluation-',dir=ROOT))
    config=configuration()|{'num_predict':1200,'timeout_seconds':90,'format':SCHEMA}
    run_config=runner_configuration()
    report={'schema':'repair-evaluation-report.v1','suite_sha256':CHECKSUM,
            'suite':suite,'model':config['model'],'digest':config['digest'],
            'sampling':generation_options(config),'timeout_seconds':config['timeout_seconds'],
            'think':False,'keep_alive':0,'attempts_per_case':1,
            'instruction':INSTRUCTION,'format':SCHEMA,
            'health_stub_sha256':sha256(APP.encode()).hexdigest(),
            'cases':[],'training_started':False,'training_examples_exported':0,
            'limitations':'Public synthetic evaluation only; not a private final holdout, customer release or security proof.'}
    print(json.dumps({'report':str(output/'report.json')}),flush=True)
    started=time.monotonic()
    for case in suite['cases']:
        if time.monotonic()-started>600: break
        entry=evaluate_case(case,OllamaProvider(config),ContainerRunner(),run_config)
        report['cases'].append(entry)
        report['summary']=summary(report['cases'],len(suite['cases']))
        report['elapsed_seconds']=round(time.monotonic()-started,3)
        (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'case':case['id'],'status':entry['status']}),flush=True)
        if entry['status']=='infrastructure_error': break
    print(json.dumps(report['summary']),flush=True)
    return 0 if report['summary']['complete'] and report['summary']['passed']==len(suite['cases']) else 1


if __name__=='__main__':
    raise SystemExit(main())
