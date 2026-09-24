"""Export independently reviewed local brand scenes as multimodal training rows."""
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import vector_school as school
from scripts.prepare_training_data import unique_object

COLLECTOR = 'restaurant-brand-v1'
STAGES = ('logo-a', 'logo-b', 'selection', 'card')
ROOT = Path('/home/marcin/ai-company-workspaces/brand-school')


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(), object_pairs_hook=unique_object)


def collect(package, review_path):
    package = Path(package); review_path = Path(review_path)
    if package.name == 'report.json':
        package = package.parent
    report = read(package/'report.json'); review = read(review_path)
    if report.get('schema') != 'restaurant-brand-school.v1' or report.get('status') != 'pending_independent_visual_review':
        raise ValueError('Completed synthetic brand run required')
    if report.get('brief', {}).get('split') != 'train' or report.get('brief', {}).get('synthetic') is not True:
        raise ValueError('Only synthetic train brand run may enter learning')
    if (review.get('schema') != 'restaurant-brand-independent-review.v1'
            or review.get('report_sha256') != digest(package/'report.json')
            or review.get('reviewer') != 'assistant_direct_visual_review'
            or review.get('decision') != 'approved_for_synthetic_learning'
            or review.get('visual_acceptance') != {'accepted': True}):
        raise ValueError('Independent positive brand review required')
    config = report['config']; rows=[]; images={}
    for stage, image_name in (('logo-a','logo-a.png'), ('logo-b','logo-b.png'), ('card','business-card.png')):
        request_path = package/(stage+'-request.json'); response_path = package/(stage+'-response.json')
        if not request_path.is_file() or not response_path.is_file(): raise ValueError('Missing model conversation')
        request=read(request_path); response=read(response_path)
        if (response.get('model'), response.get('digest')) != (report.get('model'), report.get('digest')):
            raise ValueError('Pinned local author changed')
        image = package/'delivery'/image_name
        if not image.is_file(): raise ValueError('Missing rendered training image')
        image_sha=digest(image); image_file='images/'+image_sha+'.png'
        rows.append({'version':'company-vision-candidate.v1','id':'brand-'+stage+'-'+sha256(response['content'].encode()).hexdigest()[:16],
            'family':report['brief']['family'],'split':'train','task':'restaurant_brand_'+stage,
            'usage':'development_only','model':report['model'],'digest':report['digest'],
            'messages':[{'role':'system','content':request.get('system','')},
                        {'role':'user','content':[{'type':'text','text':request.get('user','')},{'type':'image','image_id':'image-0'}]},
                        {'role':'assistant','content':response['content']}],
            'images':[{'id':'image-0','file':image_file,'sha256':image_sha}],
            'generation_config':config,
            'review':{'status':'approved_for_synthetic_learning','reviewer':review['reviewer'],'notes':review['notes'],
                      'judgments':str(review_path),'judgments_sha256':digest(review_path)},
            'source':{'report':str(package/'report.json'),'report_sha256':digest(package/'report.json'),
                      'request':str(request_path),'request_sha256':digest(request_path),
                      'response':str(response_path),'response_sha256':digest(response_path),
                      'kind':'synthetic','client_data':False,'commercial_rights_assessed':False}})
        images[image_file]=image
    return rows, images


def export(package, review_path):
    rows, images = collect(package, review_path)
    out=Path(tempfile.mkdtemp(prefix='vision-candidates-', dir=ROOT))
    (out/'images').mkdir();
    for target, source in images.items():
        shutil.copyfile(source, out/target)
        if digest(out/target) != Path(target).stem: raise ValueError('Copied image changed')
    payload=''.join(json.dumps(row, ensure_ascii=False)+'\n' for row in rows); (out/'records.jsonl').write_text(payload)
    (out/'manifest.json').write_text(json.dumps({'schema':'vision-candidate-bundle.v1','collector':COLLECTOR,
        'records':len(rows),'records_sha256':sha256(payload.encode()).hexdigest(),'split':'train',
        'training_started':False,'ready_for_trainer':False,'production_ready':False,
        'requires':['multimodal processor and label-mask audit','broader reviewed data','independent validation/test families'],
        'limitation':'Synthetic reviewed brand conversations only; no parity or commercial approval.'},ensure_ascii=False,indent=2))
    return out


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(); parser.add_argument('package',type=Path); parser.add_argument('review',type=Path); parser.add_argument('--export',action='store_true'); args=parser.parse_args()
    print(json.dumps({'output':str(export(args.package,args.review))} if args.export else {'approved':len(collect(args.package,args.review)[0]),'training_started':False}))
