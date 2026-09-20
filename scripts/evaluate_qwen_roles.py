"""Opt-in decision baseline by role. No training, app database or agent actions.

This checks categorical decisions and targets only. Explanations require a
separate review; a passed case is not proof of job delivery or safe autonomy.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.local_ollama import (OllamaProvider, ModelFailure, configuration,
                                    ensure_idle, generation_options)
from scripts.qwen_evaluation_catalog import load_role_suite,ROLE_CHECKSUM

ROOT=Path('/home/marcin/ai-company-workspaces/qwen-training')
from scripts.role_evaluation_contract import (DECISIONS, SCHEMA, ASSESSED, messages_for, check_response, counts)


def evaluate_case(suite,case,provider):
    messages=messages_for(suite,case)
    entry={'id':case['id'],'family':case['family'],'role':case['role'],
           'messages':messages,'expected':case['expected'],'status':'infrastructure_error',
           'reason_reviewed':False}
    try:
        ensure_idle()
        result=provider.complete(messages)
        entry['result']=result
    except ModelFailure as exc:
        entry['error_code']=exc.code
        if exc.code in {'truncated_output','empty_output','output_limit','invalid_text'}:
            entry['status']='invalid_output'
        return entry
    except (ValueError,TimeoutError,OSError) as exc:
        entry['error_type']=type(exc).__name__
        return entry
    try:
        entry['response'],passed=check_response(case,result['content'])
        entry['status']='passed' if passed else 'wrong_decision'
    except (ValueError,TypeError,KeyError):entry['status']='invalid_output'
    return entry


def summarize(suite,entries):
    roles=sorted({case['role'] for case in suite['cases']})
    return {'overall':counts(entries,len(suite['cases'])),
            'roles':{role:counts([e for e in entries if e['role']==role],
                                 sum(c['role']==role for c in suite['cases'])) for role in roles},
            'production_assignment_allowed':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true')
    args=parser.parse_args()
    suite=load_role_suite()
    if not args.run:
        print(json.dumps({'suite_sha256':ROLE_CHECKSUM,'cases':len(suite['cases']),
                          'model_invoked':False,'training_started':False}))
        return 0
    if any(p.is_symlink() for p in [*ROOT.parents,ROOT]):raise ValueError('Symlink in workspace path')
    ROOT.mkdir(parents=True,exist_ok=True)
    if ROOT.stat().st_dev!=Path('/home').stat().st_dev:raise ValueError('Linux /home required')
    output=Path(tempfile.mkdtemp(prefix='role-evaluation-',dir=ROOT))
    config=configuration()|{'num_predict':600,'timeout_seconds':90,'format':SCHEMA}
    report={'schema':'role-evaluation-report.v1','suite_sha256':ROLE_CHECKSUM,
            'suite':suite,'model':config['model'],'digest':config['digest'],
            'runtime':'ollama','adapter':None,'sampling':generation_options(config),
            'timeout_seconds':90,'format':SCHEMA,'think':False,'keep_alive':0,
            'cases':[],'attempts_per_case':1,'training_started':False,
            'training_examples_exported':0,'limitations':__doc__}
    print(json.dumps({'report':str(output/'report.json')}),flush=True)
    started=time.monotonic()
    for case in suite['cases']:
        if time.monotonic()-started>600:break
        entry=evaluate_case(suite,case,OllamaProvider(config))
        report['cases'].append(entry)
        report['summary']=summarize(suite,report['cases'])
        report['elapsed_seconds']=round(time.monotonic()-started,3)
        (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'case':case['id'],'status':entry['status']}),flush=True)
        if entry['status']=='infrastructure_error':break
    return 0 if report['summary']['overall']['decision_pass_rate']==1 else 1


if __name__=='__main__':raise SystemExit(main())
