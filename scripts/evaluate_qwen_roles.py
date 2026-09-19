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
from scripts.prepare_training_data import unique_object

ROOT=Path('/home/marcin/ai-company-workspaces/qwen-training')
DECISIONS=('SUPPORTED','CLARIFY','UNSUPPORTED','ASSIGN_TASK','NO_READY_TASK',
           'ESCALATE','REJECT_RESULT','RETEST','WAIT_FOR_EVIDENCE','WAIT_OWNER',
           'BLOCK_DELIVERY','PREPARE_HANDOFF')
SCHEMA={'type':'object','additionalProperties':False,'required':['decision','target_ids','reason'],
        'properties':{'decision':{'type':'string','enum':list(DECISIONS)},
                      'target_ids':{'type':'array','maxItems':3,'items':{'type':'string','maxLength':30}},
                      'reason':{'type':'string','minLength':10,'maxLength':600}}}
ASSESSED={'passed','wrong_decision','invalid_output'}


def messages_for(suite,case):
    # Never serialize case.expected into the request to the model.
    return [{'role':'system','content':suite['instruction']},
            {'role':'user','content':case['brief']}]


def check_response(case,content):
    if not isinstance(content,str) or len(content)>4000:raise ValueError('Response size')
    data=json.loads(content,object_pairs_hook=unique_object)
    if not isinstance(data,dict) or set(data)!={'decision','target_ids','reason'}:raise ValueError('Fields')
    if data['decision'] not in DECISIONS:raise ValueError('Decision')
    ids=data['target_ids']
    if (not isinstance(ids,list) or len(ids)>3 or not all(isinstance(i,str) and 0<len(i)<=30 for i in ids)
            or len(set(ids))!=len(ids)):raise ValueError('Targets')
    reason=data['reason']
    if not isinstance(reason,str) or not 10<=len(reason.strip())<=600 or '\x00' in reason:raise ValueError('Reason')
    return data, data['decision']==case['expected']['decision'] and sorted(ids)==sorted(case['expected']['target_ids'])


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


def counts(entries,expected):
    assessed=sum(e['status'] in ASSESSED for e in entries)
    passed=sum(e['status']=='passed' for e in entries)
    complete=len(entries)==expected and assessed==expected
    return {'expected':expected,'attempted':len(entries),'assessed':assessed,'passed':passed,
            'complete':complete,'decision_pass_rate':passed/expected if complete else None}


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
