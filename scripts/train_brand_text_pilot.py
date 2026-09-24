"""Text-only QLoRA pilot for restaurant brand scene JSON responses."""
from contextlib import nullcontext
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import train_qwen_pilot as pilot
from scripts.qwen_qlora_smoke import ROOT, configure, versions


EXAM = Path('/home/marcin/ai-company-workspaces/brand-school-holdout/identity-ova6f6j7/exam.json')
STATE = Path('/home/marcin/ai-company-workspaces/learning-autopilot/brand-group-state.json')


def rows_from_group():
    state=json.loads(STATE.read_text())
    rows=[]
    for entry in state['entries'].values():
        bundle=Path(entry['bundle'])
        for line in (bundle/'records.jsonl').read_text().splitlines():
            row=json.loads(line)
            messages=[]
            for message in row['messages']:
                if message['role']=='user' and isinstance(message['content'],list):
                    content='\n'.join(item['text'] for item in message['content'] if item.get('type')=='text')
                else: content=message['content']
                messages.append({'role':message['role'],'content':content})
            row['messages']=messages; rows.append(row)
    return rows


def brand_service_eval(model, tokenizer, disable_adapter, output, report, persist):
    import torch
    data=json.loads(EXAM.read_text()); results=[]
    for case in data['cases']:
        request=dict(case['request']); prompt=tokenizer.apply_chat_template(
            [{'role':'system','content':request['system']},{'role':'user','content':request['user']}],
            tokenize=False,add_generation_prompt=True,enable_thinking=False)
        encoded=tokenizer(prompt,add_special_tokens=False,return_tensors='pt')
        if encoded['input_ids'].shape[1]+900>4096: raise ValueError('Brand text holdout context overflow')
        with (model.disable_adapter() if disable_adapter else nullcontext()), torch.inference_mode():
            generated=model.generate(**{k:v.to('cuda') for k,v in encoded.items()},max_new_tokens=900,
                do_sample=False,use_cache=True,pad_token_id=tokenizer.pad_token_id,eos_token_id=tokenizer.eos_token_id)
        raw=tokenizer.decode(generated[0,encoded['input_ids'].shape[1]:].tolist(),skip_special_tokens=True)
        item={'id':case['id'],'kind':case['kind'],'content':raw,'stop_token_seen':True}
        results.append(item); persist(); del generated,encoded
    key='brand_after' if not disable_adapter else 'brand_baseline'; report[key]=results; persist()


def run():
    rows=rows_from_group(); exam=json.loads(EXAM.read_text());
    plan={'training':{'max_length':4096,'rank':8,'alpha':16,'batch_size':1,'gradient_accumulation_steps':2,
                      'max_steps':20,'learning_rate':5e-5,'seed':3407},
          'evaluation':{'max_new_tokens':64,'max_time_seconds_per_case':1,'do_sample':False,'max_length':4096},
          'limitations':['Private text-only brand pilot; no production promotion.']}
    out=Path(tempfile.mkdtemp(prefix='brand-text-sft-',dir=ROOT)); report={'schema':'brand-text-sft-pilot.v1','status':'running',
      'records':len(rows),'weights_trained':False,'production_ready':False,'automatic_promotion':False,'holdout':str(EXAM)}
    started=time.monotonic()
    def persist():
        report['elapsed_seconds']=round(time.monotonic()-started,3);(out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    persist(); configure()
    try:
        pilot.run_training(out,report,plan,rows,{'cases':[]},persist,service_evaluator=brand_service_eval)
        report['status']='completed_research'
    except Exception as exc:
        report.update(status='failed',error_type=type(exc).__name__,error=str(exc)[:800])
    persist(); print(json.dumps({'report':str(out/'report.json'),'status':report['status']})); return report


if __name__=='__main__': raise SystemExit(0 if run()['status']=='completed_research' else 1)
