"""Supervised Qwen art brief -> fixed native ComfyUI graph -> local PNG assets.

Two explicit stages: --plan, then --render PLAN. No model-generated code/nodes.
"""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import build_opener, ProxyHandler, Request
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.local_ollama import configuration, OllamaProvider
from app.services.comfyui_provider import graph
from scripts.compare_local_models import check_idle, local_json
from scripts.start_comfyui import ROOT as COMFY_ROOT, REVISION, command, check_shared_mount, SHARED_MODELS
from scripts.check_comfyui_generation import MODELS, output_path
from scripts.prepare_training_data import unique_object

ROOT = Path('/home/marcin/ai-company-workspaces/qwen-training')
IDS = ['sculpture', 'architecture', 'material']
INSTRUCTION = '''You are art director for fictional FORMA studio website.
Return JSON {"assets":[{"id":"sculpture","prompt":"...","alt":"...","title":"..."},
{"id":"architecture",...},{"id":"material",...}]} in that order, exactly 3 items.
English image prompts 70–130 words; Polish alt descriptions <=180 characters;
Polish short titles <=60 characters. Describe images, never commands or code.
Shared art direction: contemporary editorial CGI/product photography, warm ivory,
graphite, brushed metal and restrained acid lime, physically plausible lighting,
bold architectural composition. Landscape 3:2, image fills frame, no lettering,
no logos, no watermark, no people, no fake client work, no UI screenshots.
sculpture: sculptural chrome ribbons with one lime accent on an ivory plinth.
architecture: monumental minimal pavilion, warm concrete, curved geometry and
soft daylight, a single lime intervention. material: macro composition of glass,
brushed aluminum and translucent lime resin. Distinct but cohesive, luxurious,
not generic sci-fi neon. Avoid clutter. These are speculative AI visuals, not
photographs of real products. Do not claim generation or review happened.'''
SCHEMA = {'type':'object','additionalProperties':False,'required':['assets'],
    'properties':{'assets':{'type':'array','minItems':3,'maxItems':3,'items':{
        'type':'object','additionalProperties':False,'required':['id','prompt','alt','title'],
        'properties':{k:{'type':'string'} for k in ('id','prompt','alt','title')}}}}}


def validate_plan(data):
    if not isinstance(data,dict) or set(data) != {'assets'} or not isinstance(data['assets'],list) or len(data['assets']) != 3:
        raise ValueError('Exactly three assets required')
    for entry, identifier in zip(data['assets'],IDS):
        if not isinstance(entry,dict) or set(entry) != {'id','prompt','alt','title'} or entry['id'] != identifier:
            raise ValueError('Fixed asset identifiers required')
        for key,limit in [('prompt',1500),('alt',180),('title',60)]:
            value = entry[key]
            if not isinstance(value,str) or not value.strip() or len(value)>limit or any(ord(c)<32 for c in value):
                raise ValueError('Invalid asset text')
    return data['assets']


def request(path, payload=None):
    req = Request('http://127.0.0.1:8189'+path, data=None if payload is None else json.dumps(payload).encode(),
                  headers={'Content-Type':'application/json'})
    with build_opener(ProxyHandler({})).open(req,timeout=5) as response:
        raw=response.read(4_000_001)
    if len(raw)>4_000_000: raise ValueError('Oversized response')
    return json.loads(raw)


def external_idle():
    """Never stop other services. Caller may stop only its owned 8189 process."""
    from app.services.local_ollama import ensure_idle
    ensure_idle()
    if subprocess.check_output(['docker','ps','--format','{{.ID}}'],text=True,timeout=5).strip():
        raise RuntimeError('New container workload')
    try: queue=local_json(8188,'/queue')
    except ConnectionRefusedError: return
    if queue.get('queue_running') != [] or queue.get('queue_pending') != []:
        raise RuntimeError('User ComfyUI work started')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--plan',action='store_true')
    mode.add_argument('--render',type=Path)
    parser.add_argument('--run',action='store_true')
    args=parser.parse_args(argv)
    if not args.run:
        print('No inference. Add --run for the selected bounded local stage.');return 0
    resources=check_idle()
    if any(p.is_symlink() for p in [ROOT,*ROOT.parents]) or ROOT.stat().st_dev != Path('/home').stat().st_dev:
        raise ValueError('Linux workspace required')
    out=Path(tempfile.mkdtemp(prefix='studio-media-',dir=ROOT))
    report={'schema':'studio-media.v1','status':'incomplete','resources_before':resources,
            'published':False,'training_started':False,'assets':[]}
    def save(): (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    save();print(json.dumps({'report':str(out/'report.json')}),flush=True)
    if args.plan:
        config=configuration() | {'format':SCHEMA,'num_predict':1600,'num_thread':6,'timeout_seconds':120}
        report.update(model=config['model'],digest=config['digest'],instruction=INSTRUCTION)
        try:
            result=OllamaProvider(config).complete([{'role':'system','content':INSTRUCTION},
                {'role':'user','content':'Prepare the three cohesive FORMA asset briefs.'}])
            report['generation']=result;save()
            report['assets']=validate_plan(json.loads(result['content'],object_pairs_hook=unique_object))
            report.update(status='planned',visual_review='pending',rendered=False)
        except Exception as exc:
            report.update(status='failed',error_type=type(exc).__name__);save();raise
        finally: save()
        return 0
    path=args.render.resolve()
    if not path.is_relative_to(ROOT) or not path.is_file() or path.stat().st_size>100_000:
        raise ValueError('Bounded local plan required')
    raw=path.read_bytes();plan=json.loads(raw,object_pairs_hook=unique_object)
    if plan.get('schema') != 'studio-media.v1' or plan.get('status') != 'planned' or plan.get('rendered') is not False:
        raise ValueError('Expected unrendered art plan')
    assets=validate_plan({'assets':plan['assets']})
    if not check_shared_mount():
        report.update(status='blocked',error_code='shared_weights_not_mounted',rendered=False)
        save()
        print('Windows model directory unavailable. No models downloaded and no ComfyUI started.',flush=True)
        return 2
    for name in MODELS:
        if not (SHARED_MODELS/name).is_file(): raise ValueError('Missing existing model')
    revision=subprocess.check_output(['git','-C',str(COMFY_ROOT/'ComfyUI'),'rev-parse','HEAD'],text=True).strip()
    if revision != REVISION: raise ValueError('ComfyUI revision changed')
    with socket.socket() as probe: probe.bind(('127.0.0.1',8189))
    report.update(plan_sha256=sha256(raw).hexdigest(),model=plan['model'],digest=plan['digest'],
                  comfy_revision=revision,model_files=list(MODELS),visual_review='pending')
    cmd=command();cmd[cmd.index('--port')+1]='8189'
    cmd+=['--base-directory',str(out/'data'),'--output-directory',str(out/'output')]
    env=os.environ.copy();env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',
        HF_HUB_DISABLE_TELEMETRY='1',DO_NOT_TRACK='1',OMP_NUM_THREADS='8')
    with (out/'server.log').open('w') as log:
        proc=subprocess.Popen(cmd,cwd=COMFY_ROOT/'ComfyUI',env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+60
            while time.monotonic()<deadline:
                if proc.poll() is not None: raise RuntimeError('Owned ComfyUI exited')
                try: report['system_stats']=request('/system_stats');break
                except OSError: time.sleep(.5)
            else: raise TimeoutError('Startup')
            for i,asset in enumerate(assets):
                # Once Comfy owns GPU memory, inspect foreign workload separately.
                external_idle()
                workflow=graph(asset['prompt'],20260919+i,asset['id'])
                entry=asset | {'workflow':workflow,'status':'pending'}
                report['assets'].append(entry);save()
                submitted=time.monotonic()
                job=request('/prompt',{'prompt':workflow,'client_id':str(uuid4())})
                if job.get('node_errors'): raise ValueError('Invalid fixed graph')
                entry['prompt_id']=job['prompt_id'];save()
                deadline=time.monotonic()+300
                last_check=0
                while time.monotonic()<deadline:
                    if time.monotonic()-last_check>=5:
                        external_idle();last_check=time.monotonic()
                    history=request('/history/'+job['prompt_id']).get(job['prompt_id'])
                    if history: break
                    if proc.poll() is not None: raise RuntimeError('Owned ComfyUI stopped')
                    time.sleep(1)
                else: raise TimeoutError('Image generation')
                entry['history']=history
                if history['status'].get('status_str') != 'success' or not history['status'].get('completed'):
                    raise ValueError('Image execution failed')
                outputs=history['outputs']['10']['images']
                if len(outputs)!=1: raise ValueError('One image per asset')
                image=output_path(out/'output',outputs[0])
                from PIL import Image, ImageStat
                with Image.open(image) as img:
                    img.load()
                    if img.size != (768,512) or img.format != 'PNG' or max(ImageStat.Stat(img.convert('RGB')).stddev)<1:
                        raise ValueError('Invalid image')
                entry.update(status='rendered',file=str(image.relative_to(out)),sha256=sha256(image.read_bytes()).hexdigest(),
                             seconds=round(time.monotonic()-submitted,3));save()
                print(json.dumps({'asset':asset['id'],'seconds':entry['seconds']}),flush=True)
            report.update(status='rendered',rendered=True)
        except Exception as exc:
            report.update(status='failed',error_type=type(exc).__name__)
        finally:
            proc.terminate()
            try:proc.wait(timeout=15)
            except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
            report['own_service_stopped']=proc.poll() is not None;save()
    return 0 if report['status']=='rendered' else 1


if __name__=='__main__':raise SystemExit(main())
