"""CPU-only audit of real image pixels and completion labels, without model weights."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.qwen_qlora_smoke import ROOT,MODEL,REVISION

SNAPSHOT=ROOT/'hf-cache/hub/models--unsloth--Qwen3.8-27B-unsloth-bnb-4bit/snapshots'/REVISION
REPO=Path(__file__).resolve().parents[1]
BUNDLE_ROOTS=(ROOT.parent/'interior-school',ROOT.parent/'vector-school',ROOT.parent/'product-infographic-school')


def bundle_file(bundle, name, max_bytes=4*1024*1024):
    path=bundle/name
    if (not any(bundle.resolve().is_relative_to(root.resolve()) for root in BUNDLE_ROOTS)
            or not path.resolve().is_relative_to(bundle.resolve())
            or any(p.is_symlink() for p in (path,*path.parents))
            or not path.is_file() or path.stat().st_size>max_bytes):
        raise ValueError('Bounded private candidate file required')
    return path


def candidate_image(bundle, image):
    digest=image['sha256']
    if (not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest)
            or image['file']!='images/'+digest+'.png'):
        raise ValueError('Content-addressed bundle image required')
    path=bundle_file(bundle,image['file'])
    if sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Candidate image changed')
    return path


def completion_labels(ids,prefix,image_id,expected_images,eos,max_length):
    if len(ids)>max_length:raise ValueError('Context overflow; no truncation allowed')
    n=len(prefix)
    if not 0<n<len(ids) or ids[:n]!=prefix:raise ValueError('Prompt token boundary changed')
    if expected_images<=0 or ids.count(image_id)!=expected_images or image_id in ids[n:]:
        raise ValueError('Image token/grid mismatch')
    if eos not in ids[n:]:raise ValueError('Missing assistant end of turn')
    return [-100]*n+ids[n:]


class VisionResponseCollator:
    """One complete image conversation; no truncation or supervision of prompts."""
    def __init__(self,processor,max_length=4096):
        if type(max_length) is not int or not 256<=max_length<=8192:raise ValueError('Context limit')
        self.processor=processor;self.max_length=max_length

    def __call__(self,features):
        import torch
        if len(features)!=1:raise ValueError('Only batch size one is audited')
        messages=features[0]['messages'];images=features[0]['images']
        if [m['role'] for m in messages]!=['system','user','assistant'] or len(images)!=1:
            raise ValueError('One reviewed image conversation required')
        tokenizer=self.processor.tokenizer
        texts=[messages[0]['content'],messages[1]['content'][0]['text'],messages[2]['content']]
        if any(special in text for special in tokenizer.all_special_tokens for text in texts):
            raise ValueError('Control token in conversation text')
        prefix=self.processor.apply_chat_template(messages[:-1],tokenize=False,add_generation_prompt=True,enable_thinking=False)
        full=self.processor.apply_chat_template(messages,tokenize=False,add_generation_prompt=False,enable_thinking=False)
        if not full.startswith(prefix) or full[len(prefix):]!=messages[-1]['content'].strip()+'<|im_end|>\n':
            raise ValueError('Assistant template content changed')
        kwargs={'images':images,'add_special_tokens':False,'truncation':False,'return_tensors':'pt'}
        batch=self.processor(text=full,**kwargs)
        prompt=self.processor(text=prefix,**kwargs)
        ids=batch['input_ids'];prefix_ids=prompt['input_ids'];n=prefix_ids.shape[1]
        if 'pixel_values' not in batch or 'image_grid_thw' not in batch:raise ValueError('Image tensors missing')
        if not torch.equal(batch['pixel_values'],prompt['pixel_values']):raise ValueError('Image processing differs across prefix')
        if not torch.isfinite(batch['pixel_values']).all() or batch['pixel_values'].numel()==0:raise ValueError('Invalid pixels')
        image_id=tokenizer.convert_tokens_to_ids('<|image_pad|>')
        merge=self.processor.image_processor.merge_size
        expected=int(batch['image_grid_thw'].prod(dim=1).sum())//(merge*merge)
        eos=tokenizer.convert_tokens_to_ids('<|im_end|>')
        labels=completion_labels(ids[0].tolist(),prefix_ids[0].tolist(),image_id,expected,eos,self.max_length)
        batch['labels']=torch.tensor([labels],dtype=ids.dtype,device=ids.device)
        return batch


def verify_bundle(bundle):
    from scripts.prepare_training_data import unique_object
    manifest=json.loads(bundle_file(bundle,'manifest.json').read_text(),object_pairs_hook=unique_object)
    collector=manifest.get('collector','interior-v1')
    if collector=='interior-v1':
        from scripts import interior_learning_records as records
    elif collector=='vector-attribute-v1':
        from scripts import vector_learning_records as records
    elif collector=='product-visual-revision-v1':
        from scripts import product_visual_revision as records
    else:raise ValueError('Unknown approved-conversation collector')
    payload=bundle_file(bundle,'records.jsonl').read_bytes()
    if (manifest.get('schema')!='vision-candidate-bundle.v1'
            or sha256(payload).hexdigest()!=manifest['records_sha256'] or manifest['split']!='train'):
        raise ValueError('Changed candidate manifest')
    rows=[json.loads(line,object_pairs_hook=unique_object) for line in payload.decode().splitlines()]
    if not 1<=len(rows)<=16 or len(rows)!=manifest['records']:raise ValueError('Bounded candidate batch required')
    if len({r['id'] for r in rows})!=len(rows):raise ValueError('Duplicate candidate')
    for row in rows:
        if row.get('version')!='company-vision-candidate.v1' or row.get('split')!='train':
            raise ValueError('Training candidate schema and split required')
        expected,_=records.collect(Path(row['source']['report']),Path(row['review']['judgments']))
        if row not in expected:raise ValueError('Candidate differs from approved conversation')
        for image in row['images']:
            candidate_image(bundle,image)
    return rows


def feature(row,bundle):
    from PIL import Image
    if len(row['images'])!=1:raise ValueError('One image required')
    image=row['images'][0]
    path=candidate_image(bundle,image)
    with Image.open(path) as original:
        if original.format!='PNG' or original.width*original.height>1024*1024:raise ValueError('Bounded PNG')
        pixels=original.convert('RGB')
    messages=json.loads(json.dumps(row['messages']))
    if messages[1]['content'][1]!={'type':'image','image_id':image['id']}:raise ValueError('Wrong image reference')
    messages[1]['content'][1]={'type':'image'}
    return {'messages':messages,'images':[pixels]}


def worker(out,input_sha):
    os.environ.update(CUDA_VISIBLE_DEVICES='',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',
        HF_HUB_DISABLE_TELEMETRY='1',HF_HUB_DISABLE_IMPLICIT_TOKEN='1',TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='4')
    raw=(out/'input.json').read_bytes()
    if sha256(raw).hexdigest()!=input_sha:raise ValueError('Changed verified input')
    data=json.loads(raw);bundle=Path(data['bundle'])
    from transformers import AutoProcessor
    import torch
    torch.set_num_threads(4)
    processor=AutoProcessor.from_pretrained(str(SNAPSHOT),local_files_only=True,trust_remote_code=False)
    collator=VisionResponseCollator(processor);entries=[]
    for row in data['rows']:
        batch=collator([feature(row,bundle)]);labels=batch['labels'];ids=batch['input_ids']
        n=int((labels[0]==-100).sum())
        if not torch.all(labels[0,:n]==-100) or not torch.equal(labels[:,n:],ids[:,n:]):raise ValueError('Non-prefix label mask')
        # Negative control: removing the supplied image must never become text-only training.
        missing=feature(row,bundle);missing['images']=[]
        try:collator([missing])
        except ValueError:pass
        else:raise ValueError('Missing image accepted')
        entries.append({'id':row['id'],'tokens':ids.shape[1],'masked_tokens':n,'supervised_tokens':ids.shape[1]-n,
            'pixel_values_shape':list(batch['pixel_values'].shape),'pixel_values_dtype':str(batch['pixel_values'].dtype),
            'image_grid_thw':batch['image_grid_thw'].tolist(),'image_tokens':int((ids==processor.tokenizer.convert_tokens_to_ids('<|image_pad|>')).sum()),
            'missing_image_rejected':True,'exact_response_suffix':True})
    if torch.cuda.is_initialized():raise ValueError('CPU audit initialized CUDA')
    from scripts.qwen_qlora_smoke import versions
    result={'schema':'vision-input-audit.v1','status':'passed','model':MODEL,'revision':REVISION,'versions':versions(),
        'input_sha256':input_sha,'records':entries,'max_length':4096,'batch_size':1,'truncation':False,
        'processor_class':type(processor).__name__,'processor_config_sha256':sha256((SNAPSHOT/'processor_config.json').read_bytes()).hexdigest(),
        'template_sha256':sha256(processor.chat_template.encode()).hexdigest(),
        'weights_loaded':False,'training_started':False,'cuda_initialized':False,'ready_for_training':False,
        'limitation':'CPU processor and collator audit only; trainer integration, gradients, broader data and independent evaluation remain.'}
    (out/'report.json').write_text(json.dumps(result,indent=2));print(json.dumps({'report':str(out/'report.json'),'status':'passed'}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle',type=Path);parser.add_argument('--run',action='store_true')
    parser.add_argument('--worker-sha',help=argparse.SUPPRESS);args=parser.parse_args()
    if args.worker_sha:
        if Path(sys.prefix).resolve()!=(ROOT/'venv').resolve():raise ValueError('Isolated ML environment required')
        worker(args.bundle,args.worker_sha);return 0
    rows=verify_bundle(args.bundle)
    if not args.run:print(json.dumps({'verified_records':len(rows),'processor_loaded':False,'training_started':False}));return 0
    from scripts import interior_school as school
    out=Path(tempfile.mkdtemp(prefix='vision-input-audit-',dir=school.ROOT))
    payload=json.dumps({'bundle':str(args.bundle),'rows':rows});(out/'input.json').write_text(payload)
    env=os.environ.copy()
    for key in ('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','DBUS_SESSION_BUS_ADDRESS'):env.pop(key,None)
    cmd=[str(ROOT/'venv/bin/python'),str(Path(__file__).resolve()),str(out),'--worker-sha',sha256(payload.encode()).hexdigest()]
    try:
        result=subprocess.run(cmd,cwd=REPO,env=env,capture_output=True,text=True,timeout=120)
        (out/'worker.log').write_text(result.stdout+'\n'+result.stderr)
        if result.returncode:raise RuntimeError('CPU processor audit failed; inspect private worker.log')
    except Exception as exc:
        school.save(out/'failure.json',{'status':'failed','error_type':type(exc).__name__,'training_started':False})
        print(json.dumps({'output':str(out),'status':'failed'}));return 1
    print(json.dumps({'report':str(out/'report.json'),'status':'passed'}));return 0


if __name__=='__main__':raise SystemExit(main())
