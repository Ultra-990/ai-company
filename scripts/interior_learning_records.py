"""Preserve teacher-approved image conversations; never train or flatten images to text."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import interior_school as school
from scripts.interior_school_contract import Inspection,SHAPES
from scripts.prepare_training_data import unique_object

VERSION='company-vision-candidate.v1'


def digest(path):return sha256(school.bounded_path(path).read_bytes()).hexdigest()


def read(path):return json.loads(school.bounded_path(path).read_text(),object_pairs_hook=unique_object)


def collect(report_path,judgments_path):
    parent,report=school.load_stage(report_path,'packaged_pending_independent_review')
    if report.get('synthetic') is not True or report.get('published') is not False:
        raise ValueError('Only unpublished synthetic school runs')
    judgments=read(judgments_path)
    if (judgments.get('schema')!='interior-teacher-judgments.v1'
            or judgments.get('report_sha256')!=digest(report_path)
            or judgments.get('reviewer')!='assistant_direct_visual_review'
            or judgments.get('synthetic_privacy_checked') is not True
            or judgments.get('split')!='train'):
        raise ValueError('Independent synthetic training review required')
    if [x['id'] for x in judgments['assets']]!=list(SHAPES):raise ValueError('Review all three assets')
    if [x['id'] for x in report['inspections']]!=list(SHAPES):raise ValueError('Incomplete observations')
    rendered_path=Path(report['source_report'])
    rendered_parent,rendered=school.load_stage(rendered_path,'rendered')
    if report['source_sha256']!=digest(rendered_path):raise ValueError('Changed render report')
    if [x['id'] for x in rendered['assets']]!=list(SHAPES):raise ValueError('Incomplete images')
    rows=[];images={}
    for item,decision,asset in zip(report['inspections'],judgments['assets'],rendered['assets']):
        request_path=parent/(item['id']+'-request.json');response_path=parent/(item['id']+'-response.json')
        request=read(request_path);response=read(response_path);raw=response['content']
        if (decision['request_sha256']!=digest(request_path) or decision['response_sha256']!=digest(response_path)
                or sha256(raw.encode()).hexdigest()!=item['response_sha256']
                or response['model']!=report['model'] or response['digest']!=report['digest']
                or request['config']['model']!=report['model'] or request['config']['digest']!=report['digest']
                or Inspection.model_validate(json.loads(raw,object_pairs_hook=unique_object)).model_dump()!=item['observation']):
            raise ValueError('Changed reviewed model conversation')
        image_path=rendered_parent/asset['file'];image_sha=digest(image_path)
        if (image_sha!=asset['sha256'] or image_sha!=item['image_sha256']
                or image_sha!=request['image_sha256'] or image_sha!=decision['image_sha256']
                or Path(request['image_source'])!=image_path or Path(item['image_source'])!=image_path):
            raise ValueError('Changed observed image')
        if type(decision['approved']) is not bool or not isinstance(decision['notes'],str) or not decision['notes'].strip():
            raise ValueError('Explicit teacher decision with reasons required')
        if not decision['approved']:continue
        image_file='images/'+image_sha+'.png'
        rows.append({'version':VERSION,'id':item['id']+'-'+item['response_sha256'][:16],
            'family':'interior-render-'+report['source_sha256'][:16],'split':'train',
            'usage':'development_only','model':report['model'],'digest':report['digest'],
            'messages':[{'role':'system','content':request['system']},
                        {'role':'user','content':[{'type':'text','text':request['user']},
                                                 {'type':'image','image_id':'image-0'}]},
                        {'role':'assistant','content':raw}],
            'images':[{'id':'image-0','file':image_file,'sha256':image_sha}],
            'generation_config':request['config'],
            'review':{'status':'approved_for_synthetic_learning','reviewer':judgments['reviewer'],'notes':decision['notes'],
                      'judgments':str(judgments_path),'judgments_sha256':digest(judgments_path)},
            'source':{'report':str(report_path),'report_sha256':digest(report_path),
                      'request':str(request_path),'request_sha256':digest(request_path),
                      'response':str(response_path),'response_sha256':digest(response_path),
                      'render_report':str(rendered_path),'render_sha256':digest(rendered_path),
                      'kind':'synthetic','client_data':False,'commercial_rights_assessed':False}})
        images[image_file]=image_path
    return rows,images


def export(report_path,judgments_path):
    rows,images=collect(report_path,judgments_path)
    if not rows:raise ValueError('No approved observations')
    out=Path(tempfile.mkdtemp(prefix='vision-candidates-',dir=school.ROOT))
    (out/'images').mkdir()
    for target,source in images.items():shutil.copyfile(source,out/target)
    for row in rows:
        for image in row['images']:
            if digest(out/image['file'])!=image['sha256']:raise ValueError('Image copy changed')
    payload=''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows)
    (out/'records.jsonl').write_text(payload)
    school.save(out/'manifest.json',{'schema':'vision-candidate-bundle.v1','records':len(rows),
        'records_sha256':sha256(payload.encode()).hexdigest(),'split':'train',
        'training_started':False,'ready_for_trainer':False,'production_ready':False,
        'requires':['multimodal processor and label-mask audit','broader reviewed data','independent validation/test families'],
        'limitation':'Approved synthetic conversations with actual PNGs; not text-only SFT, a trained model, or commercial delivery approval.'})
    return out


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path);parser.add_argument('judgments',type=Path)
    parser.add_argument('--export',action='store_true');args=parser.parse_args()
    if args.export:print(json.dumps({'output':str(export(args.report,args.judgments))}))
    else:
        rows,_=collect(args.report,args.judgments)
        print(json.dumps({'approved':len(rows),'training_started':False,'exported':False}))


if __name__=='__main__':main()
