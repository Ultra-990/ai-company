"""Local Qwen concepts -> three native Comfy images -> local vision metadata.

Separate bounded stages, preserved authorship, no live DB or client publication.
"""
import argparse
import csv
from hashlib import sha256
import http.client
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.local_ollama import configuration,OllamaProvider
from app.services import local_vision
from scripts import build_studio_media as media
from scripts.check_technical_reviewer import save
from scripts.prepare_training_data import unique_object
from scripts.interior_school_contract import BRIEF,Plan,Inspection,SHAPES,check_plan,inspection_instruction,VISION_PROFILES

ROOT=Path('/home/marcin/ai-company-workspaces/interior-school')


def bounded_path(path):
    if any(p.is_symlink() for p in (path,*path.parents)) or not path.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError('Private non-symlink school file required')
    if not path.is_file() or path.stat().st_size>4*1024*1024:raise ValueError('Bounded file required')
    return path


def load_stage(path,status):
    path=bounded_path(path);report=json.loads(path.read_text(),object_pairs_hook=unique_object)
    if report.get('schema')!='interior-school.v1' or report.get('status')!=status:
        raise ValueError('Wrong or incomplete source stage')
    return path.parent,report


def plan(out,report):
    config=configuration()|{'format':Plan.model_json_schema(),'num_predict':2600,'num_ctx':8192,'num_thread':4,'timeout_seconds':180}
    messages=[{'role':'system','content':BRIEF},{'role':'user','content':'Prepare the complete three-image editorial teaching package.'}]
    save(out/'request.json',messages)
    result=OllamaProvider(config).complete(messages);save(out/'response.json',result)
    parsed=check_plan(Plan.model_validate(json.loads(result['content'],object_pairs_hook=unique_object)))
    report.update(status='planned',model=result['model'],digest=result['digest'],plan=parsed.model_dump(),
                  response_sha256=sha256(result['content'].encode()).hexdigest(),request_sha256=sha256((out/'request.json').read_bytes()).hexdigest())


def render(source,out,report,persist):
    parent,previous=load_stage(source,'planned')
    response=json.loads(bounded_path(parent/'response.json').read_text())
    if (sha256(response['content'].encode()).hexdigest()!=previous['response_sha256']
            or response['model']!=previous['model'] or response['digest']!=previous['digest']
            or sha256(bounded_path(parent/'request.json').read_bytes()).hexdigest()!=previous['request_sha256']):
        raise ValueError('Changed original model plan')
    parsed=check_plan(Plan.model_validate(json.loads(response['content'],object_pairs_hook=unique_object)))
    if parsed.model_dump()!=previous['plan']:raise ValueError('Plan no longer matches model output')
    if not media.check_shared_mount():raise ValueError('Existing read-only weights unavailable')
    revision=subprocess.check_output(['git','-C',str(media.COMFY_ROOT/'ComfyUI'),'rev-parse','HEAD'],text=True).strip()
    if revision!=media.REVISION:raise ValueError('Comfy revision changed')
    for name in media.MODELS:
        if not (media.SHARED_MODELS/name).is_file():raise ValueError('Required existing weights unavailable')
    with socket.socket() as probe:probe.bind(('127.0.0.1',8189))
    report.update(plan=parsed.model_dump(),source_report=str(source),source_sha256=sha256(source.read_bytes()).hexdigest(),
                  comfy_revision=revision,model_files=list(media.MODELS),model_hash_authenticity_verified=False,assets=[])
    cmd=media.command();cmd[cmd.index('--port')+1]='8189'
    cmd+=['--base-directory',str(out/'data'),'--output-directory',str(out/'output')]
    env=os.environ.copy();env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',DO_NOT_TRACK='1',OMP_NUM_THREADS='4')
    for key in ('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','DBUS_SESSION_BUS_ADDRESS'):env.pop(key,None)
    with (out/'server.log').open('w') as log:
        proc=subprocess.Popen(cmd,cwd=media.COMFY_ROOT/'ComfyUI',env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+60
            while time.monotonic()<deadline:
                if proc.poll() is not None:raise RuntimeError('Own Comfy process exited')
                try:report['system_stats']=media.request('/system_stats');break
                except OSError:time.sleep(.5)
            else:raise TimeoutError('Comfy startup')
            for i,asset in enumerate(parsed.assets):
                media.external_idle()
                width,height=SHAPES[asset.id]
                graph=media.graph(asset.prompt,20260920+i,asset.id)
                graph['6']['inputs'].update(width=width,height=height)
                job_id=str(uuid4())
                entry={'id':asset.id,'workflow':graph,'prompt_id':job_id,'status':'submitting'}
                report['assets'].append(entry);persist()
                queued=media.request('/prompt',{'prompt_id':job_id,'client_id':job_id,'prompt':graph})
                if queued.get('prompt_id')!=job_id or queued.get('node_errors'):raise ValueError('Submission not confirmed; no retry')
                started=time.monotonic();last_check=0
                while time.monotonic()-started<300:
                    if time.monotonic()-last_check>=5:media.external_idle();last_check=time.monotonic()
                    history=media.request('/history/'+job_id).get(job_id)
                    if history:break
                    if proc.poll() is not None:raise RuntimeError('Own Comfy process exited')
                    time.sleep(1)
                else:raise TimeoutError('Generation; no automatic retry')
                entry['history']=history
                if history['status'].get('status_str')!='success' or history['status'].get('completed') is not True:
                    raise ValueError('Image job failed')
                images=history['outputs']['10']['images']
                if len(images)!=1:raise ValueError('One output per candidate required')
                image=media.output_path(out/'output',images[0])
                from PIL import Image,ImageStat
                with Image.open(image) as im:
                    im.load()
                    if im.format!='PNG' or im.size!=(width,height) or max(ImageStat.Stat(im.convert('RGB')).stddev)<1:
                        raise ValueError('Invalid generated image')
                library=out/'library';library.mkdir(exist_ok=True)
                target=library/asset.filename;shutil.copyfile(image,target)
                entry.update(status='rendered',file=str(target.relative_to(out)),sha256=sha256(target.read_bytes()).hexdigest(),
                             width=width,height=height,seconds=round(time.monotonic()-started,3));persist()
                print(json.dumps({'image':asset.id,'path':str(target)}),flush=True)
            report['status']='rendered'
        finally:
            proc.terminate()
            try:proc.wait(timeout=15)
            except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
            report['own_service_stopped']=proc.poll() is not None;persist()


def csv_cell(value):
    value=str(value)
    return "'"+value if value.startswith(('=','+','-','@','\t','\r')) else value


def load_feedback(path,source):
    """Teacher comments bound to exact previous model observations and images."""
    feedback=json.loads(bounded_path(path).read_text(),object_pairs_hook=unique_object)
    if set(feedback)!={'source_report','source_sha256','comments'}:raise ValueError('Feedback contract')
    previous_path=Path(feedback['source_report'])
    parent,previous=load_stage(previous_path,'packaged_pending_independent_review')
    if (sha256(previous_path.read_bytes()).hexdigest()!=feedback['source_sha256']
            or Path(previous['source_report'])!=source
            or previous['source_sha256']!=sha256(bounded_path(source).read_bytes()).hexdigest()):
        raise ValueError('Changed feedback source')
    if [x['id'] for x in previous['inspections']]!=list(SHAPES):raise ValueError('Feedback observation count')
    for item in previous['inspections']:
        raw=json.loads(bounded_path(parent/(item['id']+'-response.json')).read_text())
        if (sha256(raw['content'].encode()).hexdigest()!=item['response_sha256']
                or raw['model']!=previous['model'] or raw['digest']!=previous['digest']
                or json.loads(raw['content'])!=item['observation']):raise ValueError('Changed reviewed response')
    comments=feedback['comments']
    if (not isinstance(comments,dict) or set(comments)!=set(SHAPES)
            or any(not isinstance(x,str) or not 1<=len(x)<=2000 for x in comments.values())):
        raise ValueError('Feedback comments required for all images')
    return feedback


def inspect(source,out,report,persist,feedback_path=None,vision_profile='legacy'):
    instruction=inspection_instruction(vision_profile)
    report['vision_profile']=vision_profile
    parent,previous=load_stage(source,'rendered')
    feedback=load_feedback(feedback_path,source) if feedback_path else None
    if feedback:
        save(out/'feedback.json',feedback)
        report.update(feedback_sha256=sha256((out/'feedback.json').read_bytes()).hexdigest(),
                      revision_mode='fresh_image_with_teacher_feedback',previous_inspection=feedback['source_report'])
    if previous.get('own_service_stopped') is not True:raise ValueError('Comfy ownership not released')
    original=bounded_path(Path(previous['source_report']))
    if (sha256(original.read_bytes()).hexdigest()!=previous['source_sha256']
            or json.loads(original.read_text())['plan']!=previous['plan']):
        raise ValueError('Changed source plan chain')
    config=configuration()|{'format':Inspection.model_json_schema(),'num_predict':1800,'num_ctx':8192,'num_thread':4,'timeout_seconds':180}
    conn=http.client.HTTPConnection('127.0.0.1',11434,timeout=5)
    try:
        conn.request('POST','/api/show',json.dumps({'model':config['model']}),{'Content-Type':'application/json'})
        response=conn.getresponse();raw=response.read(1024*1024+1)
        if response.status!=200 or len(raw)>1024*1024 or 'vision' not in json.loads(raw).get('capabilities',[]):
            raise ValueError('Pinned local model does not advertise vision')
    finally:conn.close()
    report.update(source_report=str(source),source_sha256=sha256(source.read_bytes()).hexdigest(),
                  model=config['model'],digest=config['digest'],inspections=[],plan=previous['plan'])
    plan=check_plan(Plan.model_validate(previous['plan']))
    if [x['id'] for x in previous['assets']]!=list(SHAPES):raise ValueError('Expected three rendered images')
    rows=[]
    for asset,entry in zip(plan.assets,previous['assets']):
        media.check_idle()
        path=bounded_path(parent/entry['file']);image=path.read_bytes()
        if sha256(image).hexdigest()!=entry['sha256']:raise ValueError('Changed image')
        user='Inspect this generated interior candidate. Describe only what you can see; do not infer a real property or client.'
        if feedback:
            user+='\nTeacher feedback on your previous inspection:\n'+feedback['comments'][asset.id]
            user+='\nReinspect the image and write all fields afresh. Keep complete sentences comfortably below each character limit. Do not copy the feedback into the deliverable.'
        save(out/(asset.id+'-request.json'),{'system':instruction,'user':user,'image_sha256':entry['sha256'],
                                          'image_source':str(path),'config':config})
        result=local_vision.complete(config,instruction,user,image)
        save(out/(asset.id+'-response.json'),result)
        observation=Inspection.model_validate(json.loads(result['content'],object_pairs_hook=unique_object))
        item={'id':asset.id,'image_sha256':entry['sha256'],'image_source':str(path),
              'response_sha256':sha256(result['content'].encode()).hexdigest(),'observation':observation.model_dump()}
        report['inspections'].append(item);persist()
        library=out/'library';library.mkdir(exist_ok=True);shutil.copyfile(path,library/asset.filename)
        rows.append([asset.id,asset.filename,asset.title,observation.description,observation.alt_text,
                     entry['width'],entry['height'],entry['sha256'],'AI-generated synthetic training image',
                     observation.recommendation,'independent_review_pending','not_published'])
        print(json.dumps({'inspected':asset.id,'candidate_status':observation.recommendation}),flush=True)
    with (out/'image-tracker.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.writer(stream);writer.writerow(['id','filename','planned_concept_title','description','alt_text','width','height','sha256','origin','model_recommendation','review','publication'])
        writer.writerows([[csv_cell(value) for value in row] for row in rows])
    # Mechanical packaging: every editorial sentence below is exact model text.
    package=['# '+plan.article_title,'',plan.writer_brief,'','## Outline','']+['- '+x for x in plan.outline]
    package+=['','## Publishing checks','']+['- '+x for x in plan.publishing_checks]
    package+=['','## Observed image candidates','']
    for asset,item in zip(plan.assets,report['inspections']):
        ob=item['observation'];package+=['### Planned concept: '+asset.title,'',f'![{ob["alt_text"]}](library/{asset.filename})','',ob['description'],'',ob['brand_fit'],'',ob['uncertainty'],'']
    (out/'writer-package.md').write_text('\n'.join(package),encoding='utf-8')
    save(out/'new-url-package.json',{'article_title':plan.article_title,'proposed_slug':plan.proposed_slug,
        'meta_description':plan.meta_description,'publication_status':'draft_pending_independent_review',
        'live_url':None,'assets':[{'id':asset.id,'file':'library/'+asset.filename,
            'alt_text':item['observation']['alt_text'],'image_sha256':item['image_sha256']}
            for asset,item in zip(plan.assets,report['inspections'])],
        'publishing_checks':plan.publishing_checks})
    report['status']='packaged_pending_independent_review'


def main():
    parser=argparse.ArgumentParser(description=__doc__);mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--plan',action='store_true');mode.add_argument('--render',type=Path);mode.add_argument('--inspect',type=Path)
    parser.add_argument('--feedback',type=Path,help='Teacher feedback bound to an earlier inspection; only with --inspect')
    parser.add_argument('--vision-profile',choices=VISION_PROFILES,default='legacy')
    parser.add_argument('--run',action='store_true');args=parser.parse_args()
    if args.feedback and not args.inspect:parser.error('--feedback requires --inspect')
    if args.vision_profile!='legacy' and not args.inspect:parser.error('--vision-profile requires --inspect')
    if not args.run:print(json.dumps({'model_invoked':False,'training_started':False}));return 0
    resources=media.check_idle()
    if any(p.is_symlink() for p in (ROOT,*ROOT.parents)):raise ValueError('Symlink workspace')
    ROOT.mkdir(exist_ok=True)
    if ROOT.stat().st_dev!=Path('/home').stat().st_dev:raise ValueError('Linux workspace required')
    stage='plan' if args.plan else 'render' if args.render else 'inspect'
    out=Path(tempfile.mkdtemp(prefix=stage+'-',dir=ROOT));started=time.monotonic()
    report={'schema':'interior-school.v1','status':'running','stage':stage,'resources_before':resources,
            'synthetic':True,'published':False,'independently_accepted':False,'weights_trained':False,
            'training_exported':False,'midjourney_tested':False,
            'authorship':{'creative_concepts_and_editorial_text':'local_qwen','images':'local_z_image_turbo','brief_and_independent_review':'assistant'}}
    def persist():report['elapsed_seconds']=round(time.monotonic()-started,3);save(out/'report.json',report)
    persist();print(json.dumps({'output':str(out)}),flush=True)
    try:
        if args.plan:plan(out,report)
        elif args.render:render(args.render,out,report,persist)
        else:inspect(args.inspect,out,report,persist,args.feedback,args.vision_profile)
    except Exception as exc:
        report.update(status='failed',error_type=type(exc).__name__)
        import traceback
        (out/'traceback.txt').write_text(traceback.format_exc())
    finally:persist()
    print(json.dumps({'report':str(out/'report.json'),'status':report['status']}),flush=True)
    return 1 if report['status']=='failed' else 0


if __name__=='__main__':raise SystemExit(main())
