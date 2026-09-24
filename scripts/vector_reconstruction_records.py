"""Export reviewed local-model full-vector references as multimodal train rows.

The source SVG and pixels must come from a local model reference run. This
collector adds only the reconstruction conversation envelope; it never edits
the artwork or accepts a candidate reconstruction.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import vector_school as school
from scripts.vector_school_contract import RULES, RECREATE_BRIEF, parse_response

COLLECTOR = 'vector-reconstruction-v1'


def read(path):
    return json.loads(school.checked(path).read_text())


def collect(report_path, review_path):
    report = read(report_path); review = read(review_path)
    if (report.get('schema') not in {'vector-school.v1', 'vector-structured-source.v1'}
            or report.get('role') != 'source' or report.get('status') != 'reference_ready'
            or report.get('data_split') != 'train'):
        raise ValueError('Completed train source reference required')
    if (review.get('schema') != 'vector-reference-review.v1'
            or review.get('source_sha256') != school.checksum(school.checked(report_path))
            or review.get('reviewer') != 'assistant_direct_visual_review'
            or review.get('decision') != 'usable_synthetic_training_reference'
            or not isinstance(review.get('notes'), str) or not review['notes'].strip()):
        raise ValueError('Independent positive source review required')
    school.authenticate(report_path, report)
    source_svg = school.checked(Path(report_path).parent/'artwork.svg').read_text()
    if parse_response(json.loads((Path(report_path).parent/'response.json').read_text())['content']) != source_svg:
        raise ValueError('Source artwork is not the exact local-model response')
    image = school.checked(Path(report_path).parent/'preview.png')
    image_sha = school.checksum(image)
    target = json.dumps({'svg': source_svg}, ensure_ascii=False, separators=(',', ':'))
    row = {
        'version': 'company-vision-candidate.v1',
        'id': 'vector-reconstruction-' + sha256((school.checksum(report_path)+image_sha).encode()).hexdigest()[:24],
        'family': report['family'], 'split': 'train', 'task': 'full_vector_reconstruction',
        'usage': 'development_only', 'model': report['model'], 'digest': report['digest'],
        'messages': [
            {'role': 'system', 'content': RULES},
            {'role': 'user', 'content': [{'type': 'text', 'text': RECREATE_BRIEF},
                                          {'type': 'image', 'image_id': 'image-0'}]},
            {'role': 'assistant', 'content': target}],
        'images': [{'id': 'image-0', 'file': 'images/'+image_sha+'.png', 'sha256': image_sha}],
        'generation_config': {'model': report['model'], 'digest': report['digest'], 'num_ctx': 8192,
                              'task_contract': 'full_vector_reconstruction.v1'},
        'review': {'status': 'approved_for_synthetic_learning', 'reviewer': review['reviewer'],
                   'notes': review['notes'], 'judgments': str(review_path),
                   'judgments_sha256': school.checksum(school.checked(review_path))},
        'source': {'report': str(report_path), 'report_sha256': school.checksum(school.checked(report_path)),
                   'review': str(review_path), 'review_sha256': school.checksum(school.checked(review_path)),
                   'kind': 'synthetic', 'client_data': False, 'commercial_rights_assessed': False}
    }
    return [row], {'images/'+image_sha+'.png': image}


def export(pairs):
    if not 1 <= len(pairs) <= 16: raise ValueError('Bounded reconstruction batch required')
    rows=[]; images={}
    for report, review in pairs:
        accepted, assets = collect(report, review); rows.extend(accepted); images.update(assets)
    if len({r['id'] for r in rows}) != len(rows): raise ValueError('Duplicate reconstruction candidate')
    out=Path(tempfile.mkdtemp(prefix='vision-candidates-', dir=Path('/home/marcin/ai-company-workspaces/vector-school')))
    (out/'images').mkdir()
    for target, source in images.items():
        shutil.copyfile(source, out/target)
        if school.checksum(out/target) != Path(target).stem: raise ValueError('Image changed during export')
    payload=''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in rows); (out/'records.jsonl').write_text(payload)
    school.save(out/'manifest.json', {'schema':'vision-candidate-bundle.v1','collector':COLLECTOR,
        'records':len(rows),'records_sha256':sha256(payload.encode()).hexdigest(),'split':'train',
        'training_started':False,'ready_for_trainer':False,'production_ready':False,
        'requires':['multimodal processor and label-mask audit','broader reviewed data','independent validation/test families'],
        'limitation':'Local-model authored synthetic references for full reconstruction; no held-out gain or commercial approval.'})
    return out


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('pairs',nargs='+',type=Path);parser.add_argument('--export',action='store_true');args=parser.parse_args()
    if len(args.pairs)%2: parser.error('Pass report/review pairs')
    pairs=list(zip(args.pairs[::2],args.pairs[1::2]))
    if args.export: print(json.dumps({'output':str(export(pairs)),'training_started':False}))
    else: print(json.dumps({'approved':sum(len(collect(a,b)[0]) for a,b in pairs),'training_started':False}))
