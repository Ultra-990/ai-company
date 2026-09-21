"""Matched base/adapter exam on reserved images. Never exports answers for learning."""
import argparse
from contextlib import nullcontext
from hashlib import sha256
import json
import os
from pathlib import Path
import random
import signal
import subprocess
import sys
import tempfile
import time
import traceback

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.qwen_qlora_smoke import ROOT,MODEL,REVISION,configure,preflight,versions
from scripts.check_vision_training_inputs import SNAPSHOT,REPO
from scripts.train_vision_input_pilot import full_vision_names
from scripts.interior_school_contract import Inspection,SHAPES,curriculum_metadata,inspection_instruction

ADAPTER_RUN=ROOT/'vision-input-sft-uiau78tj'
ADAPTER=ADAPTER_RUN/'adapter-INPUT-RESEARCH-NOT-FOR-PRODUCTION'
ADAPTER_SHA='1ead1a8413150f3b7d172d0db2e0e654b7ac56926fffff702c7c1ab5e44b5f52'
CRITERIA={
 'grounded':'Descriptions and visible_details name only supported objects/positions/material appearances; no invented species, freshness, provenance or exact counts.',
 'defects':'Every proposed defect has a concrete visible basis; empty is acceptable. Normal lighting, blur or style alone is not a defect.',
 'complete':'Complete concise sentences: description <350 characters, alt 8-16 words and <130 characters; 3-5 details; brand_fit and uncertainty each <160 characters.',
 'uncertainty':'Specific useful visual limitations, consistent with claims in other fields; no unsupported certainty.',
 'brand_fit':'Concrete visible features explain the match or mismatch with warm classic cottage interiors.'}


def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2))


def load_exam(source):
    from scripts import interior_school as school
    parent,render=school.load_stage(source,'rendered')
    if curriculum_metadata(render)['data_split']!='test' or render.get('own_service_stopped') is not True:
        raise ValueError('Reserved completed images required')
    original=school.bounded_path(Path(render['source_report']))
    planned=json.loads(original.read_text())
    if (sha256(original.read_bytes()).hexdigest()!=render['source_sha256']
            or curriculum_metadata(planned)!=curriculum_metadata(render) or planned['plan']!=render['plan']):
        raise ValueError('Changed reserved plan chain')
    if [x['id'] for x in render['assets']]!=list(SHAPES):raise ValueError('Three reserved images required')
    cases=[]
    for item in render['assets']:
        image=school.bounded_path(parent/item['file'])
        if sha256(image.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Reserved image changed')
        cases.append({'id':item['id'],'image':str(image),'sha256':item['sha256']})
    weights=ADAPTER/'adapter_model.safetensors'
    if sha256(weights.read_bytes()).hexdigest()!=ADAPTER_SHA:raise ValueError('Adapter changed')
    training=json.loads((ADAPTER_RUN/'report.json').read_text())
    if training['status']!='completed_input_integration_only' or training['adapter_sha256']!=ADAPTER_SHA:
        raise ValueError('Completed pinned adapter required')
    train_bundle=Path(training['protocol']['bundle'])
    train_images={im['sha256'] for row in (json.loads(x) for x in (train_bundle/'records.jsonl').read_text().splitlines()) for im in row['images']}
    if train_images.intersection(c['sha256'] for c in cases):raise ValueError('Training image leaked into exam')
    return {'schema':'vision-transfer-protocol.v1','usage':'evaluation_only','family':render['family'],
        'render_report':str(source),'render_sha256':sha256(source.read_bytes()).hexdigest(),
        'model':MODEL,'revision':REVISION,'adapter_sha256':ADAPTER_SHA,
        'cases':cases,'system':inspection_instruction('grounded-concise-v1'),
        'user':'Inspect this generated interior candidate. Describe only what you can see; do not infer a real property or client.',
        'max_new_tokens':1100,'max_time_per_case':90,'context':4096,'do_sample':False,'criteria':CRITERIA,
        'training_started':False,'production_ready':False}


def evaluate(out,protocol,report,persist):
    configure();os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',UNSLOTH_COMPILE_LOCATION=str(out/'compiled'))
    from unsloth import FastModel
    import torch
    import transformers
    from transformers import conversion_mapping
    from peft import PeftModel
    from PIL import Image
    torch.set_num_threads(4);report['resources_before']=preflight();persist()
    if report['resources_before']['vram_free_bytes']<26*1024**3:raise RuntimeError('Insufficient free GPU memory')
    if transformers.__version__!='5.5.0':raise RuntimeError('Unverified loader version')
    with full_vision_names(conversion_mapping):
        base,processor=FastModel.from_pretrained(model_name=str(SNAPSHOT),max_seq_length=4096,
            load_in_4bit=True,full_finetuning=False,trust_remote_code=False,local_files_only=True,
            text_only=False,offload_embedding=False,dtype=torch.bfloat16)
    from bitsandbytes.nn import Linear4bit
    quant=[m for m in base.modules() if isinstance(m,Linear4bit)]
    if len(quant)!=352 or any(getattr(m.weight,'quant_state',None) is None for m in quant):raise RuntimeError('Incomplete quantization state')
    model=PeftModel.from_pretrained(base,str(ADAPTER),is_trainable=False)
    FastModel.for_inference(model)
    report['quantized_layers_verified']=len(quant)
    for phase in ('base','adapter'):
        for case in protocol['cases']:
            path=Path(case['image'])
            if sha256(path.read_bytes()).hexdigest()!=case['sha256']:raise ValueError('Exam image changed')
            with Image.open(path) as image: pixels=image.convert('RGB')
            messages=[{'role':'system','content':protocol['system']},{'role':'user','content':[
                {'type':'text','text':protocol['user']},{'type':'image'}]}]
            prompt=processor.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=False)
            inputs=processor(text=prompt,images=[pixels],return_tensors='pt',add_special_tokens=False,truncation=False)
            n=inputs['input_ids'].shape[1]
            if n+1100>4096:raise ValueError('Exam exceeds context')
            start=time.monotonic()
            with (model.disable_adapter() if phase=='base' else nullcontext()),torch.inference_mode():
                output=model.generate(**{k:v.to('cuda') for k,v in inputs.items()},max_new_tokens=1100,
                    max_time=90,do_sample=False,use_cache=True,pad_token_id=processor.tokenizer.pad_token_id)
            tokens=output[0,n:].tolist();raw=processor.tokenizer.decode(tokens,skip_special_tokens=True)
            structure=True
            try:Inspection.model_validate_json(raw)
            except ValueError:structure=False
            report['results'].append({'phase':phase,'case':case['id'],'image':str(path),'image_sha256':case['sha256'],
                'prompt_sha256':sha256(prompt.encode()).hexdigest(),'input_ids_sha256':sha256(inputs['input_ids'].numpy().tobytes()).hexdigest(),
                'content':raw,'response_sha256':sha256(raw.encode()).hexdigest(),'structure_valid':structure,
                'stop_token_seen':processor.tokenizer.convert_tokens_to_ids('<|im_end|>') in tokens,
                'seconds':round(time.monotonic()-start,3),'generated_tokens':len(tokens)})
            persist();print(json.dumps({'completed_samples':len(report['results'])}),flush=True)
            del output,inputs
    report['status']='completed_pending_blind_review'


def blind(out,report):
    samples=[];mapping={}
    for case in SHAPES:
        entries=[e for e in report['results'] if e['case']==case]
        if len(entries)!=2 or len({e['input_ids_sha256'] for e in entries})!=1:raise ValueError('Unmatched inputs')
        random.SystemRandom().shuffle(entries)
        for entry in entries:
            id=f'sample-{len(samples)+1:02d}'
            samples.append({'sample':id,'case':case,'image':entry['image'],'content':entry['content'],
                            'structure_valid':entry['structure_valid'],'stop_token_seen':entry['stop_token_seen']})
            mapping[id]={'phase':entry['phase'],'case':case,'response_sha256':entry['response_sha256']}
    save(out/'blind-packet.json',{'criteria':CRITERIA,'samples':samples})
    save(out/'mapping-OPEN-AFTER-SCORING.json',{'mapping':mapping,
        'packet_sha256':sha256((out/'blind-packet.json').read_bytes()).hexdigest(),
        'report_sha256':sha256((out/'report.json').read_bytes()).hexdigest()})


def finalize(out):
    report=json.loads((out/'report.json').read_text());packet=json.loads((out/'blind-packet.json').read_text())
    mapping=json.loads((out/'mapping-OPEN-AFTER-SCORING.json').read_text());judgments=json.loads((out/'judgments.json').read_text())
    if (report['status']!='completed_pending_blind_review' or packet['criteria']!=CRITERIA
            or mapping['packet_sha256']!=sha256((out/'blind-packet.json').read_bytes()).hexdigest()
            or mapping['report_sha256']!=sha256((out/'report.json').read_bytes()).hexdigest()
            or set(judgments)!=set(mapping['mapping'])):raise ValueError('Changed exam or incomplete judgments')
    expected={(e['phase'],e['case']):e for e in report['results']};seen=set();samples=[]
    if set(expected)!={(p,c) for p in ('base','adapter') for c in SHAPES}:raise ValueError('Incomplete matched exam')
    for sample in packet['samples']:
        origin=mapping['mapping'][sample['sample']];key=(origin['phase'],origin['case'])
        if (key in seen or key not in expected or sample['case']!=key[1]
                or sample['content']!=expected[key]['content']
                or sample['image']!=expected[key]['image']
                or origin['response_sha256']!=sha256(sample['content'].encode()).hexdigest()
                or sample['structure_valid']!=expected[key]['structure_valid']
                or sample['stop_token_seen']!=expected[key]['stop_token_seen']):raise ValueError('Blind evidence differs from source')
        if sha256(Path(sample['image']).read_bytes()).hexdigest()!=expected[key]['image_sha256']:
            raise ValueError('Exam image changed after generation')
        seen.add(key);j=judgments[sample['sample']]
        if (set(j)!={'scores','notes'} or set(j['scores'])!=set(CRITERIA)
                or any(type(v) is not bool for v in j['scores'].values()) or not isinstance(j['notes'],str)
                or len(j['notes'])<10):raise ValueError('Explicit independent criteria and notes required')
        samples.append(origin|j|{'sample':sample['sample'],'points':sum(j['scores'].values()),
            'passed':all(j['scores'].values()) and sample['structure_valid'] and sample['stop_token_seen']})
    if seen!=set(expected):raise ValueError('Missing judgments')
    result={'schema':'vision-transfer-assessment.v1','samples':samples,
        'judgments_sha256':sha256((out/'judgments.json').read_bytes()).hexdigest(),
        'totals':{p:{'points':sum(x['points'] for x in samples if x['phase']==p),
                     'passed':sum(x['passed'] for x in samples if x['phase']==p)} for p in ('base','adapter')},
        'training_exported':False,'production_ready':False,'parity_proven':False,
        'limitations':'Three samples from one held-out synthetic room family; teacher-scored with phase labels hidden, not a statistical quality equivalence test.'}
    save(out/'comparison.json',result);return result


def worker(out,checksum):
    raw=(out/'protocol.json').read_bytes()
    if sha256(raw).hexdigest()!=checksum:raise ValueError('Protocol changed')
    protocol=json.loads(raw)
    if sha256((ADAPTER/'adapter_model.safetensors').read_bytes()).hexdigest()!=ADAPTER_SHA:raise ValueError('Adapter changed')
    report={'schema':'vision-transfer.v1','status':'running','protocol':protocol,'protocol_sha256':checksum,
            'results':[],'versions':versions(),'training_started':False,'production_ready':False}
    start=time.monotonic()
    def persist():report['elapsed_seconds']=round(time.monotonic()-start,3);save(out/'report.json',report)
    def expired(*_):raise TimeoutError('Exam deadline')
    signal.signal(signal.SIGALRM,expired);signal.alarm(900);persist()
    try:evaluate(out,protocol,report,persist)
    except Exception as exc:
        report.update(status='failed',error_type=type(exc).__name__);(out/'traceback.txt').write_text(traceback.format_exc())
    finally:signal.alarm(0);persist()
    if report['status']=='completed_pending_blind_review':blind(out,report)
    return int(report['status']=='failed')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path)
    parser.add_argument('--run',action='store_true');parser.add_argument('--finalize',action='store_true')
    parser.add_argument('--worker-sha',help=argparse.SUPPRESS);args=parser.parse_args()
    if args.finalize:print(json.dumps(finalize(args.source)['totals']));return 0
    if args.worker_sha:return worker(args.source,args.worker_sha)
    protocol=load_exam(args.source)
    if not args.run:print(json.dumps({'reserved_cases':3,'generation_started':False}));return 0
    from scripts.compare_local_models import check_idle
    resources=check_idle();out=Path(tempfile.mkdtemp(prefix='vision-transfer-',dir=ROOT))
    save(out/'protocol.json',protocol);save(out/'preflight.json',resources)
    print(json.dumps({'output':str(out)}),flush=True)
    env=os.environ.copy()
    for key in ('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','DBUS_SESSION_BUS_ADDRESS'):env.pop(key,None)
    cmd=[str(ROOT/'venv/bin/python'),str(Path(__file__).resolve()),str(out),'--worker-sha',sha256((out/'protocol.json').read_bytes()).hexdigest()]
    with (out/'worker.log').open('w') as log:result=subprocess.run(cmd,cwd=REPO,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=930)
    print(json.dumps({'status':json.loads((out/'report.json').read_text())['status'],'output':str(out)}))
    return result.returncode


if __name__=='__main__':raise SystemExit(main())
