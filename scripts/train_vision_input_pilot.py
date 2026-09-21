"""Three opt-in multimodal adapter updates; no quality claim, routing or promotion."""
import argparse
from contextlib import contextmanager
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
from scripts.qwen_qlora_smoke import ROOT,MODEL,REVISION,configure,preflight,versions
from scripts.check_vision_training_inputs import SNAPSHOT,REPO,VisionResponseCollator,feature

PLAN=REPO/'config/vision-sft-input-pilot-001.json'
SETTINGS={'max_length':4096,'max_steps':3,'rank':4,'alpha':8,'learning_rate':1e-5,
          'seed':3407,'batch_size':1,'vision_layers_frozen':True,'optimizer':'torch_adamw'}


@contextmanager
def full_vision_names(registry):
    """5.5.0 wrongly applies its text-extraction rename inside the full VLM.

    Disable only that observed rule while loading this full, pinned checkpoint.
    This process-local registry is restored even if loading fails; no files edited.
    """
    previous=registry.get_checkpoint_conversion_mapping('qwen3_5_text')
    if (len(previous)!=1 or previous[0].source_patterns!=['^model.language_model']
            or previous[0].target_patterns!=['model']):raise ValueError('Unrecognized text-extraction rule')
    registry.register_checkpoint_conversion_mapping('qwen3_5_text',[],overwrite=True)
    try:yield
    finally:registry.register_checkpoint_conversion_mapping('qwen3_5_text',previous,overwrite=True)


def load_protocol():
    plan=json.loads(PLAN.read_text())
    if (plan['schema']!='vision-input-training-research.v1' or plan['model']!=MODEL
            or plan['revision']!=REVISION or plan['training']!=SETTINGS or plan['records']!=1
            or plan['deadline_seconds']!=900 or plan['production_ready'] is not False
            or plan['automatic_promotion'] is not False or plan['held_out_quality_measured'] is not False):
        raise ValueError('New limits require a new explicit research protocol')
    return plan


def train(out,plan,rows,report,persist):
    configure()
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',UNSLOTH_COMPILE_LOCATION=str(out/'compiled'))
    from unsloth import FastModel
    import torch
    torch.set_num_threads(4)
    report['resources_before']=preflight();persist()
    if report['resources_before']['vram_free_bytes']<26*1024**3 or report['resources_before']['ram_available_bytes']<10*1024**3:
        raise RuntimeError('Insufficient memory; no other processes will be changed')
    torch.cuda.reset_peak_memory_stats()
    report['stage']='loading_multimodal_model';persist()
    import transformers
    from transformers import conversion_mapping
    if transformers.__version__!='5.5.0':raise RuntimeError('Loader compatibility is audited only on Transformers 5.5.0')
    with full_vision_names(conversion_mapping):
        model,processor=FastModel.from_pretrained(model_name=str(SNAPSHOT),max_seq_length=4096,
            load_in_4bit=True,full_finetuning=False,trust_remote_code=False,local_files_only=True,
            text_only=False,offload_embedding=False,dtype=torch.bfloat16)
    from bitsandbytes.nn import Linear4bit
    quantized=[(name,m) for name,m in model.named_modules() if isinstance(m,Linear4bit)]
    if not quantized or any(getattr(m.weight,'quant_state',None) is None for _,m in quantized):
        raise RuntimeError('Missing quantization state; refuse training before forward')
    if any(p.is_meta for p in model.parameters()):raise RuntimeError('Unloaded model parameter')
    report.update(loader_profile='full_vlm_preserve_names_transformers_5_5_0',
                  quantized_layers_verified=len(quantized),conversion_registry_restored=True)
    if not hasattr(processor,'image_processor'):raise RuntimeError('Vision processor missing')
    model=FastModel.get_peft_model(model,finetune_vision_layers=False,finetune_language_layers=True,
        finetune_attention_modules=True,finetune_mlp_modules=True,r=4,lora_alpha=8,lora_dropout=0,bias='none',
        use_gradient_checkpointing='unsloth',random_state=3407)
    parameters=[(n,p) for n,p in model.named_parameters() if p.requires_grad]
    if not parameters or any('lora_' not in n or 'visual' in n or 'vision_tower' in n for n,p in parameters):
        raise RuntimeError('Only language adapter parameters may train')
    probe_name,probe=next((n,p) for n,p in parameters if 'lora_B' in n)
    before=probe.detach().cpu().clone()
    report.update(trainable_parameters=sum(p.numel() for n,p in parameters),parameter_probe=probe_name)
    FastModel.for_training(model)
    processor.tokenizer.padding_side='right'
    collator=VisionResponseCollator(processor,4096)
    batch=collator([feature(rows[0],Path(plan['bundle']))])
    labels=batch['labels'];ids=batch['input_ids'];n=int((labels[0]==-100).sum())
    if not torch.all(labels[0,:n]==-100) or not torch.equal(labels[:,n:],ids[:,n:]):raise RuntimeError('Actual training labels differ')
    report['training_input']={'tokens':ids.shape[1],'supervised_tokens':int((labels!=-100).sum()),
        'masked_tokens':n,'image_grid_thw':batch['image_grid_thw'].tolist(),
        'pixel_values_shape':list(batch['pixel_values'].shape),'completion_mask_verified':True,
        'input_ids_sha256':sha256(ids.numpy().tobytes()).hexdigest(),
        'labels_sha256':sha256(labels.numpy().tobytes()).hexdigest()}
    # Count actual calls to the model's visual module: a pixel tensor in a manifest is insufficient.
    visual=next((m for name,m in model.named_modules() if name.endswith('.visual')),None)
    if visual is None:raise RuntimeError('Could not locate visual module for instrumentation')
    calls=[]
    hook=visual.register_forward_pre_hook(lambda module,args:calls.append(len(args)))
    batch={k:v.to('cuda') for k,v in batch.items()}
    optimizer=torch.optim.AdamW([p for n,p in parameters],lr=1e-5)
    report.update(stage='training',steps=0,losses=[]);persist()
    try:
        for step in range(3):
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type='cuda',dtype=torch.bfloat16):
                output=model(**batch);loss=output.loss
            value=float(loss.detach())
            if not math.isfinite(value):raise RuntimeError('Non-finite loss')
            loss.backward()
            norm=float(torch.nn.utils.clip_grad_norm_([p for _,p in parameters],1.0))
            if not math.isfinite(norm):raise RuntimeError('Non-finite gradient')
            optimizer.step()
            report['losses'].append(value);report['steps']=step+1
            report['visual_forward_calls']=len(calls);persist()
            print(json.dumps({'step':step+1,'loss':value,'visual_forward_calls':len(calls)}),flush=True)
            del output,loss
    finally:hook.remove()
    changed=not torch.equal(before,probe.detach().cpu())
    if not changed or len(calls)<3:raise RuntimeError('Missing adapter updates or actual image forwards')
    report.update(adapter_parameter_changed=changed,weights_trained=True,peak_vram_bytes=torch.cuda.max_memory_allocated())
    adapter=out/'adapter-INPUT-RESEARCH-NOT-FOR-PRODUCTION'
    model.save_pretrained(adapter,safe_serialization=True);processor.save_pretrained(adapter)
    weights=adapter/'adapter_model.safetensors'
    if not weights.is_file():raise RuntimeError('Adapter weights missing')
    report.update(adapter_saved=True,adapter_sha256=sha256(weights.read_bytes()).hexdigest(),
        stage='complete',status='completed_input_integration_only')


def worker(out,input_sha):
    raw=(out/'input.json').read_bytes()
    if sha256(raw).hexdigest()!=input_sha:raise ValueError('Changed verified inputs')
    payload=json.loads(raw);plan=load_protocol()
    if plan!=payload['protocol']:raise ValueError('Protocol changed after preflight')
    report={'schema':'vision-input-training.v1','status':'running','stage':'preflight',
        'protocol':plan,'protocol_sha256':sha256(PLAN.read_bytes()).hexdigest(),'input_sha256':input_sha,
        'resources_checked':payload['resources'],'versions':versions(),
        'weights_trained':False,'adapter_saved':False,'production_ready':False,'automatic_promotion':False,
        'held_out_quality_measured':False,'limitation':'Three steps on one approved training image; validates plumbing, not generalization or service readiness.'}
    started=time.monotonic()
    def persist():
        report['elapsed_seconds']=round(time.monotonic()-started,3)
        temporary=out/'report.tmp';temporary.write_text(json.dumps(report,indent=2));temporary.replace(out/'report.json')
    def expired(*_):raise TimeoutError('Bounded vision training deadline')
    signal.signal(signal.SIGALRM,expired);signal.alarm(900)
    persist()
    try:train(out,plan,payload['rows'],report,persist)
    except Exception as exc:
        report.update(status='failed',error_type=type(exc).__name__)
        (out/'traceback.txt').write_text(traceback.format_exc())
    finally:signal.alarm(0);persist()
    print(json.dumps({'report':str(out/'report.json'),'status':report['status']}),flush=True)
    return 1 if report['status']=='failed' else 0


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true')
    parser.add_argument('--worker',type=Path,help=argparse.SUPPRESS);parser.add_argument('--input-sha',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.worker:return worker(args.worker,args.input_sha)
    from scripts.check_vision_training_inputs import verify_bundle
    plan=load_protocol();bundle=Path(plan['bundle']);rows=verify_bundle(bundle)
    if len(rows)!=1 or sha256((bundle/'records.jsonl').read_bytes()).hexdigest()!=plan['records_sha256']:
        raise ValueError('Pinned reviewed record changed')
    if not args.run:print(json.dumps({'records':1,'training_started':False,'protocol':plan}));return 0
    from scripts.compare_local_models import check_idle
    resources=check_idle()
    out=Path(tempfile.mkdtemp(prefix='vision-input-sft-',dir=ROOT))
    payload=json.dumps({'protocol':plan,'rows':rows,'resources':resources});(out/'input.json').write_text(payload)
    env=os.environ.copy()
    for key in ('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','DBUS_SESSION_BUS_ADDRESS'):env.pop(key,None)
    cmd=[str(ROOT/'venv/bin/python'),str(Path(__file__).resolve()),'--worker',str(out),'--input-sha',sha256(payload.encode()).hexdigest()]
    print(json.dumps({'output':str(out)}),flush=True)
    with (out/'worker.log').open('w') as log:
        result=subprocess.run(cmd,cwd=REPO,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=930)
    report=json.loads((out/'report.json').read_text());print(json.dumps({'report':str(out/'report.json'),'status':report['status']}))
    return result.returncode


if __name__=='__main__':raise SystemExit(main())
