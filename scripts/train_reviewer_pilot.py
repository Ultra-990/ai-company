"""Pinned second QLoRA experiment: exact reviewed outputs and reserved service probes.

No client artifacts are executed, no promotion, no feedback or training on exam
answers. Service outputs require independent structural and semantic assessment.
"""
import argparse
from contextlib import nullcontext
from hashlib import sha256
import json
from pathlib import Path
import signal
import sys
import tempfile
import time
import traceback

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import train_qwen_pilot as base
from scripts.prepare_training_data import load_batches
from scripts.qwen_evaluation_catalog import load_reviewer_suite,REVIEWER_CHECKSUM

PLAN=base.REPO/'config/qwen-sft-pilot-002.json'
PRIVATE=Path('/home/marcin/ai-company-workspaces/technical-review')


def verified_private_file(path):
    path=Path(path)
    if (not path.resolve().is_relative_to(PRIVATE.resolve())
            or any(p.is_symlink() for p in (path,*path.parents)) or not path.is_file()
            or path.stat().st_size>1024*1024):
        raise ValueError('Private reviewed file outside scope, changed type or too large')
    return path


def verify_review_record(row):
    report_path=verified_private_file(row['source']['reference'])
    report=json.loads(report_path.read_text());root=report_path.parent
    artifacts={name:verified_private_file(root/name) for name in
               ('request.json','response.json','article.md','sources.json')}
    request=json.loads(artifacts['request.json'].read_text())
    response=json.loads(artifacts['response.json'].read_text())
    if (report['status']!='structurally_valid' or report['authorship']['editorial_review']!='local_model'
            or report['synthetic_development_exercise'] is not True
            or sha256(response['content'].encode()).hexdigest()!=report['response_sha256']
            or response['model']!=report['model'] or response['digest']!=report['digest']
            or row['messages']!=request+[{'role':'assistant','content':response['content']}]
            or any(sha256(artifacts[name].read_bytes()).hexdigest()!=report[key] for name,key in
                   [('request.json','request_sha256'),('article.md','article_sha256'),('sources.json','sources_sha256')])):
        raise ValueError('Original model review provenance changed')
    if len(row['review']['evidence'])!=1:raise ValueError('One independently reviewed content assessment required')
    proof=row['review']['evidence'][0];path=verified_private_file(proof['reference'])
    assessment=json.loads(path.read_text())
    if (proof['kind']!='content_review' or sha256(path.read_bytes()).hexdigest()!=proof['sha256']
            or assessment['decision']!='approved_for_synthetic_training'
            or assessment['privacy_checked'] is not True or assessment['original_model_content_edited'] is not False
            or assessment['report_sha256']!=sha256(report_path.read_bytes()).hexdigest()
            or any(assessment[key]!=report[key] for key in
                   ('response_sha256','request_sha256','article_sha256','sources_sha256'))):
        raise ValueError('Independent acceptance evidence changed')


def load_protocol():
    original,_,_,roles=base.load_protocol()
    plan=json.loads(PLAN.read_text())
    training=original['training']|{'max_length':4096,'max_steps':18}
    reviewer={'sha256':REVIEWER_CHECKSUM,'case_count':3,'max_new_tokens':1700,
              'max_time_seconds_per_case':150,'max_context':4096,'do_sample':False}
    if (plan['schema']!='reviewer-sft-research.v1'
            or plan['parent_protocol_sha256']!=sha256(base.PLAN.read_bytes()).hexdigest()
            or any(plan[key]!=original[key] for key in
                   ('datasets','model','revision','evaluation','deadline_seconds','production_ready','automatic_promotion'))
            or plan['training']!=training or plan['reviewer_evaluation']!=reviewer):
        raise ValueError('Changed fixed research recipe; create another explicit protocol')
    private=verified_private_file(plan['reviewer_dataset']['path'])
    if sha256(private.read_bytes()).hexdigest()!=plan['reviewer_dataset']['sha256']:
        raise ValueError('Changed reviewed dataset')
    rows,gate=load_batches([base.REPO/x['path'] for x in original['datasets']]+[private])
    if len(rows)!=17 or plan['records']!=17 or gate['sha256']!=plan['combined_sha256']:
        raise ValueError('Dataset count/hash changed')
    if any(r['split']!='train' or r['review']['status']!='approved' or not r['source']['privacy_checked'] for r in rows):
        raise ValueError('Only approved training records permitted')
    for row in rows[-3:]:verify_review_record(row)
    exam=load_reviewer_suite()
    if len(exam['cases'])!=3:raise ValueError('Exam case count changed')
    return plan,rows,gate,roles,exam


def service_evaluator(exam,settings):
    def evaluate(model,tokenizer,disable_adapter,output,report,persist):
        import torch
        from unsloth import FastModel
        FastModel.for_inference(model)
        phase='reviewer_baseline' if disable_adapter else 'reviewer_after'
        results=[];report[phase]=results
        for case in exam['cases']:
            prompt=tokenizer.apply_chat_template(case['messages'],tokenize=False,
                add_generation_prompt=True,enable_thinking=False)
            encoded=tokenizer(prompt,add_special_tokens=False,return_tensors='pt')
            length=encoded['input_ids'].shape[1]
            if length+settings['max_new_tokens']>settings['max_context']:
                raise ValueError('Service probe exceeds fixed context; never truncate')
            started=time.monotonic()
            with (model.disable_adapter() if disable_adapter else nullcontext()),torch.inference_mode():
                answer=model.generate(**{k:v.to('cuda') for k,v in encoded.items()},
                    max_new_tokens=settings['max_new_tokens'],do_sample=False,
                    max_time=settings['max_time_seconds_per_case'],use_cache=True,
                    pad_token_id=tokenizer.pad_token_id,eos_token_id=tokenizer.eos_token_id)
            generated=answer[0,length:].tolist();raw=tokenizer.decode(generated,skip_special_tokens=True)
            entry={'id':case['id'],'family':case['family'],'content':raw,
                   'prompt_sha256':sha256(prompt.encode()).hexdigest(),
                   'response_sha256':sha256(raw.encode()).hexdigest(),'prompt_tokens':length,
                   'tokens':len(generated),'seconds':round(time.monotonic()-started,3),
                   'stop_token_seen':bool(generated and generated[-1]==tokenizer.eos_token_id),
                   'structural_review':'pending','semantic_review':'pending','accepted':False}
            results.append(entry);base.save(output/(phase+'.json'),results);persist()
            print(json.dumps({'phase':phase,'case':case['id'],'tokens':len(generated),
                              'complete_generation':entry['stop_token_seen']}),flush=True)
            del encoded,answer
    return evaluate


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true')
    args=parser.parse_args();plan,rows,gate,roles,exam=load_protocol()
    if not args.run:
        print(json.dumps({'training_started':False,'records':len(rows),'service_probes':len(exam['cases']),
                          'max_length':plan['training']['max_length'],'production_ready':False}));return 0
    base.configure()
    if (any(p.is_symlink() for p in (base.ROOT,*base.ROOT.parents))
            or base.ROOT.stat().st_dev!=Path('/home').stat().st_dev):
        raise ValueError('Linux non-symlink workspace required')
    out=Path(tempfile.mkdtemp(prefix='reviewer-sft-',dir=base.ROOT))
    report={'schema':'reviewer-sft-pilot.v1','status':'running','stage':'preflight','protocol':plan,
            'protocol_sha256':sha256(PLAN.read_bytes()).hexdigest(),'versions':base.versions(),
            'dataset_gate':gate,'weights_trained':False,'adapter_saved':False,'production_ready':False,
            'production_routing_changed':False,'baseline':[],'after':[],
            'comparison_runtime':'Same pinned HF bnb4 base, fresh adapter disabled before/enabled after; identical greedy prompts and budgets.'}
    base.save(out/'protocol.json',plan);base.save(out/'exam-snapshot.json',exam)
    (out/'reviewed-records.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
    for path in (Path(__file__),Path(base.__file__)):(out/path.name).write_bytes(path.read_bytes())
    started=time.monotonic()
    def persist():
        report['elapsed_seconds']=round(time.monotonic()-started,3);base.save(out/'report.json',report)
    persist();print(json.dumps({'output':str(out)}),flush=True)
    def expired(*_):raise TimeoutError('Fixed research deadline')
    signal.signal(signal.SIGALRM,expired);signal.alarm(plan['deadline_seconds'])
    try:
        base.run_training(out,report,plan,rows,roles,persist,service_evaluator(exam,plan['reviewer_evaluation']))
        report['status']='completed_research_pending_semantic_review'
    except Exception as exc:
        report['status']='failed';report['error_type']=type(exc).__name__;report['error']=str(exc)[:1000]
        (out/'traceback.txt').write_text(traceback.format_exc());print(json.dumps({'error':report['error']}),flush=True)
    finally:signal.alarm(0);persist()
    print(json.dumps({'report':str(out/'report.json'),'status':report['status'],
                      'weights_trained':report['weights_trained']}),flush=True)
    return 0 if report['status']=='completed_research_pending_semantic_review' else 1


if __name__=='__main__':raise SystemExit(main())
