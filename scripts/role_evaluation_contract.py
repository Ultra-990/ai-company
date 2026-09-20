"""Pure frozen-role output contract; usable without application dependencies."""
import json
from scripts.prepare_training_data import unique_object

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


def counts(entries,expected):
    assessed=sum(e['status'] in ASSESSED for e in entries)
    passed=sum(e['status']=='passed' for e in entries)
    complete=len(entries)==expected and assessed==expected
    return {'expected':expected,'attempted':len(entries),'assessed':assessed,'passed':passed,
            'complete':complete,'decision_pass_rate':passed/expected if complete else None}
