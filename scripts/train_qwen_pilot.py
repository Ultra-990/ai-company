"""Real, bounded QLoRA research on pinned reviewed records, with matched regression.

This separate research protocol cannot authorize production export/deployment.
It leaves the existing 200/25/50 gate and active Ollama model unchanged.
"""
import argparse
from contextlib import nullcontext
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import traceback

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.check_sft_tokenization import SNAPSHOT, encode_example
from scripts.prepare_training_data import load_batches
from scripts.qwen_evaluation_catalog import load_role_suite, ROLE_CHECKSUM
from scripts.qwen_qlora_smoke import ROOT, MODEL, REVISION, configure, preflight, versions
from scripts.role_evaluation_contract import check_response, messages_for, counts

REPO=Path(__file__).resolve().parents[1]
PLAN=REPO/'config/qwen-sft-pilot-001.json'


def save(path,value):
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    temporary.replace(path)


def load_protocol():
    plan=json.loads(PLAN.read_text())
    if (plan['schema']!='reviewed-sft-research.v1' or plan['model']!=MODEL
            or plan['revision']!=REVISION or plan['production_ready'] is not False
            or plan['automatic_promotion'] is not False):
        raise ValueError('Invalid research protocol')
    paths=[]
    for item in plan['datasets']:
        path=REPO/item['path']
        if not path.resolve().is_relative_to(REPO/'datasets/qwen') or path.is_symlink():
            raise ValueError('Dataset outside reviewed repository files')
        if sha256(path.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('Pinned dataset changed')
        paths.append(path)
    rows,gate=load_batches(paths)
    if len(rows)!=plan['records'] or gate['sha256']!=plan['combined_sha256']:
        raise ValueError('Research dataset mismatch')
    if any(row['split']!='train' or row['review']['status']!='approved'
           or row['source']['privacy_checked'] is not True for row in rows):
        raise ValueError('Only approved, privacy-reviewed train records permitted')
    for row in rows:
        for evidence in row['review']['evidence']:
            path=REPO/evidence['reference'].split('#')[0]
            if not path.resolve().is_relative_to(REPO/'datasets/qwen') or path.is_symlink():
                raise ValueError('Evidence outside reviewed repository files')
            if sha256(path.read_bytes()).hexdigest()!=evidence['sha256']:
                raise ValueError('Review evidence changed')
    suite=load_role_suite()
    if plan['evaluation']['role_suite_sha256']!=ROLE_CHECKSUM or len(suite['cases'])!=plan['evaluation']['case_count']:
        raise ValueError('Regression suite mismatch')
    t=plan['training']
    if (t!={'max_length':2048,'rank':8,'alpha':16,'batch_size':1,
            'gradient_accumulation_steps':2,'max_steps':14,'learning_rate':5e-5,'seed':3407}
            or plan['deadline_seconds']!=1800):
        raise ValueError('Create a new explicit protocol for changed training limits')
    return plan,rows,gate,suite


def compare(before,after,expected):
    b={case['id']:case for case in before};a={case['id']:case for case in after}
    complete=(len(before)==len(after)==len(b)==len(a)==expected and b.keys()==a.keys()
              and all(c['status'] in ('passed','wrong_decision','invalid_output') for c in before+after))
    return {'complete':complete,
            'before':counts(before,expected),'after':counts(after,expected),
            'improved_cases':[key for key in b if complete and b[key]['status']!='passed' and a[key]['status']=='passed'],
            'regressed_cases':[key for key in b if complete and b[key]['status']=='passed' and a[key]['status']!='passed'],
            'production_ready':False, 'expertise_proven':False}


def evaluate(model,tokenizer,suite,settings,disable_adapter,out,persist):
    import torch
    from unsloth import FastModel
    FastModel.for_inference(model)
    results=[]
    for case in suite['cases']:
        entry={'id':case['id'],'family':case['family'],'status':'infrastructure_error'}
        results.append(entry)
        save(out,results)
        prompt=tokenizer.apply_chat_template(messages_for(suite,case),tokenize=False,
                                             add_generation_prompt=True,enable_thinking=False)
        encoded=tokenizer(prompt,add_special_tokens=False,return_tensors='pt')
        if encoded['input_ids'].shape[1]+settings['max_new_tokens']>2048:
            raise ValueError('Regression exceeds fixed context')
        started=time.monotonic()
        with (model.disable_adapter() if disable_adapter else nullcontext()), torch.inference_mode():
            output=model.generate(**{k:v.to('cuda') for k,v in encoded.items()},
                max_new_tokens=settings['max_new_tokens'],do_sample=settings['do_sample'],
                max_time=settings['max_time_seconds_per_case'],use_cache=True,
                pad_token_id=tokenizer.pad_token_id,eos_token_id=tokenizer.eos_token_id)
        generated=output[0,encoded['input_ids'].shape[1]:].tolist()
        raw=tokenizer.decode(generated,skip_special_tokens=True)
        entry.update(content=raw,seconds=round(time.monotonic()-started,3),tokens=len(generated),
                     stop_token_seen=bool(generated and generated[-1]==tokenizer.eos_token_id))
        try:
            if not entry['stop_token_seen']:raise ValueError('Incomplete generation')
            parsed,passed=check_response(case,raw)
            entry['parsed']=parsed;entry['status']='passed' if passed else 'wrong_decision'
        except (ValueError,TypeError,KeyError):entry['status']='invalid_output'
        save(out,results);persist()
        print(json.dumps({'evaluation':out.stem,'case':case['id'],'status':entry['status']}),flush=True)
        del output,encoded
    return results


def verify_labels(trainer,encoded):
    """Check the trainer's actual dataset and collator, not just an offline audit."""
    if len(trainer.train_dataset)!=len(encoded):raise ValueError('Trainer changed record count')
    for index,row in enumerate(encoded):
        actual=trainer.train_dataset[index]
        if any(actual[key]!=row[key] for key in ('input_ids','attention_mask','labels')):
            raise ValueError('Trainer changed tokens or completion mask')
        batch=trainer.data_collator([actual])
        values=batch['labels'][0].tolist()
        if values[:len(row['labels'])]!=row['labels'] or any(v!=-100 for v in values[len(row['labels']):]):
            mismatch=next((i for i,(a,b) in enumerate(zip(values,row['labels'])) if a!=b),None)
            raise ValueError(f'Collator changed completion labels/padding: record={index}, '
                             f'expected_length={len(row["labels"])}, actual_length={len(values)}, '
                             f'first_mismatch={mismatch}, collator={type(trainer.data_collator).__name__}')
        if not any(v==-100 for v in row['labels']) or not any(v!=-100 for v in row['labels']):
            raise ValueError('Empty prompt/completion mask')


def run_training(output,report,plan,rows,suite,persist):
    # Resource policy lives in the application environment; do not import its
    # SQLAlchemy/application packages into the isolated ML environment.
    checked=subprocess.run([str(REPO/'.venv/bin/python'),'-c',
        'import json; from scripts.compare_local_models import check_idle; print(json.dumps(check_idle()))'],
        cwd=REPO,capture_output=True,text=True,timeout=20,check=False)
    if checked.returncode:raise RuntimeError('Shared-service preflight failed; no training started')
    report['idle_preflight']=json.loads(checked.stdout);persist()
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',
                      UNSLOTH_COMPILE_LOCATION=str(output/'compiled'))
    from unsloth import FastModel  # Must precede torch/transformers imports.
    import torch
    from datasets import Dataset
    from transformers import DataCollatorForSeq2Seq, TrainerCallback
    from trl import SFTTrainer,SFTConfig

    report['resources_before']=preflight();persist()
    if (report['resources_before']['vram_free_bytes']<26*1024**3
            or report['resources_before']['ram_available_bytes']<10*1024**3):
        raise RuntimeError('Insufficient free memory; no other workload will be stopped')
    torch.set_num_threads(4);torch.cuda.reset_peak_memory_stats()
    t=plan['training'];report['stage']='loading';persist()
    model,tokenizer=FastModel.from_pretrained(model_name=str(SNAPSHOT),max_seq_length=t['max_length'],
        load_in_4bit=True,full_finetuning=False,trust_remote_code=False,local_files_only=True,
        text_only=True,offload_embedding=False,dtype=torch.bfloat16)
    # text_only extracts Qwen3.8's decoder config, whose architectures is None.
    # This Unsloth version iterates it during generate(). Restore descriptive
    # metadata from the actually loaded class; never rewrite the base checkpoint.
    if model.config.architectures is None:
        model.config.architectures=[type(model).__name__]
        report['runtime_architecture_metadata']=model.config.architectures
    model=FastModel.get_peft_model(model,finetune_vision_layers=False,finetune_language_layers=True,
        finetune_attention_modules=True,finetune_mlp_modules=True,r=t['rank'],lora_alpha=t['alpha'],
        lora_dropout=0,bias='none',use_gradient_checkpointing='unsloth',random_state=t['seed'])
    trainable=[(n,p) for n,p in model.named_parameters() if p.requires_grad]
    if not trainable or any('lora_' not in n for n,p in trainable):
        raise RuntimeError('Only adapter parameters may train')
    report['trainable_parameters']=sum(p.numel() for n,p in trainable)
    probe_name,probe=next((n,p) for n,p in trainable if 'lora_B' in n)
    before=probe.detach().cpu().clone()
    encoded=[encode_example(tokenizer,row['messages'],t['max_length']) for row in rows]
    report['tokenization']=[{'id':row['id'],'tokens':len(e['input_ids']),
                            'supervised_tokens':sum(v!=-100 for v in e['labels'])} for row,e in zip(rows,encoded)]
    report['stage']='baseline';persist()
    report['baseline']=evaluate(model,tokenizer,suite,plan['evaluation'],True,output/'baseline.json',persist)
    report['stage']='training_setup';persist()
    FastModel.for_training(model)
    tokenizer.padding_side='right'
    collator=DataCollatorForSeq2Seq(tokenizer=tokenizer,padding=True,label_pad_token_id=-100,
                                   pad_to_multiple_of=8,return_tensors='pt')
    class Progress(TrainerCallback):
        def on_log(self,args,state,control,logs=None,**kwargs):
            report['training_log']=state.log_history;report['steps']=state.global_step;persist()
    trainer=SFTTrainer(model=model,processing_class=tokenizer,train_dataset=Dataset.from_list(encoded),
        data_collator=collator,callbacks=[Progress()],args=SFTConfig(
            output_dir=str(output/'checkpoints'),max_length=t['max_length'],
            dataset_kwargs={'skip_prepare_dataset':True},packing=False,
            per_device_train_batch_size=t['batch_size'],gradient_accumulation_steps=t['gradient_accumulation_steps'],
            max_steps=t['max_steps'],learning_rate=t['learning_rate'],warmup_steps=0,
            optim='adamw_8bit',logging_steps=1,save_strategy='no',report_to='none',
            seed=t['seed'],dataset_num_proc=1,bf16=True,dataloader_num_workers=0))
    # This Unsloth trainer constructor ends in for_inference(), switching its
    # shared tokenizer to left padding. Restore training mode before auditing
    # the actual collator; otherwise padding shifts the completion labels.
    FastModel.for_training(model)
    tokenizer.padding_side='right'
    verify_labels(trainer,encoded)
    report['trainer_completion_mask_verified']=True;report['stage']='training';persist()
    result=trainer.train()
    report.update(steps=trainer.state.global_step,metrics=result.metrics,
        finite_loss=math.isfinite(result.training_loss),
        adapter_parameter_changed=not torch.equal(before,probe.detach().cpu()),parameter_probe=probe_name,
        peak_vram_bytes=torch.cuda.max_memory_allocated())
    if not report['finite_loss'] or report['steps']!=t['max_steps'] or not report['adapter_parameter_changed']:
        raise RuntimeError('Training did not complete finite steps with changed adapter parameters')
    adapter=output/'adapter-RESEARCH-NOT-FOR-PRODUCTION'
    model.save_pretrained(adapter,safe_serialization=True);tokenizer.save_pretrained(adapter)
    if not (adapter/'adapter_model.safetensors').is_file():raise RuntimeError('Adapter weights missing')
    report['adapter_files_sha256']={p.name:sha256(p.read_bytes()).hexdigest() for p in adapter.iterdir() if p.is_file()}
    report['adapter_saved']=True;report['weights_trained']=True;report['stage']='after_training';persist()
    # Release optimizer state before generation, keeping the exact trained model.
    trainer.optimizer=None;trainer.lr_scheduler=None
    import gc
    gc.collect();torch.cuda.empty_cache()
    report['after']=evaluate(model,tokenizer,suite,plan['evaluation'],False,output/'after.json',persist)
    report['comparison']=compare(report['baseline'],report['after'],len(suite['cases']))
    report['stage']='complete'


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true')
    args=parser.parse_args();plan,rows,gate,suite=load_protocol()
    if not args.run:
        print(json.dumps({'records':len(rows),'regression_cases':len(suite['cases']),
            'production_dataset_ready':gate['export_ready'],'training_started':False,'protocol':plan},ensure_ascii=False));return 0
    configure()
    if any(p.is_symlink() for p in (ROOT,*ROOT.parents)) or ROOT.stat().st_dev!=Path('/home').stat().st_dev:
        raise ValueError('Linux non-symlink workspace required')
    output=Path(tempfile.mkdtemp(prefix='reviewed-sft-',dir=ROOT))
    report={'schema':'reviewed-sft-pilot.v1','status':'running','stage':'preflight',
            'protocol':plan,'protocol_sha256':sha256(PLAN.read_bytes()).hexdigest(),
            'versions':versions(),'dataset_gate':gate,'weights_trained':False,'adapter_saved':False,
            'production_ready':False,'production_routing_changed':False,
            'comparison_runtime':'Same pinned local HF bnb4 checkpoint; adapter disabled before, enabled after.',
            'limitations':plan['limitations'],'baseline':[],'after':[]}
    started=time.monotonic()
    def persist():
        report['elapsed_seconds']=round(time.monotonic()-started,3);save(output/'report.json',report)
    save(output/'protocol.json',plan);persist()
    print(json.dumps({'output':str(output)}),flush=True)
    def expired(*_):raise TimeoutError('Research deadline reached')
    signal.signal(signal.SIGALRM,expired);signal.alarm(plan['deadline_seconds'])
    try:
        run_training(output,report,plan,rows,suite,persist)
        report['status']='completed_research'
    except Exception as exc:
        report['status']='failed';report['error_type']=type(exc).__name__;report['error']=str(exc)[:1200]
        (output/'traceback.txt').write_text(traceback.format_exc(),encoding='utf-8')
        print(json.dumps({'error_type':type(exc).__name__,'error':str(exc)[:1200]}),flush=True)
    finally:
        signal.alarm(0);persist()
    print(json.dumps({'status':report['status'],'report':str(output/'report.json'),
                      'weights_trained':report['weights_trained'],'production_ready':False}),flush=True)
    return 0 if report['status']=='completed_research' else 1


if __name__=='__main__':raise SystemExit(main())
