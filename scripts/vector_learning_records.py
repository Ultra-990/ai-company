"""Export independently reviewed local SVG tool conversations with their real pixels."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import vector_school as school
from scripts import vector_patch_school as patch
from scripts.prepare_training_data import unique_object

COLLECTOR = 'vector-attribute-v1'


def read(path):
    return json.loads(school.checked(path).read_text(), object_pairs_hook=unique_object)


def collect(report_path, judgments_path):
    experience = patch.experience(report_path, judgments_path)
    if experience['split'] != 'train':
        raise ValueError('Only predeclared train families may enter the training candidates')
    image = experience['images'][0]
    image_file = 'images/' + image['sha256'] + '.png'
    row = {key: experience[key] for key in
           ('id', 'family', 'split', 'task', 'model', 'digest', 'messages', 'generation_config')}
    row.update(version='company-vision-candidate.v1', usage='development_only',
               images=[{'id': image['id'], 'file': image_file, 'sha256': image['sha256']}],
               review={'status': 'approved_for_synthetic_learning',
                       'reviewer': 'assistant_direct_visual_review',
                       'notes': experience['review']['notes'],
                       'judgments': str(judgments_path),
                       'judgments_sha256': school.checksum(school.checked(judgments_path))},
               source={'report': str(report_path), 'report_sha256': school.checksum(school.checked(report_path)),
                       'kind': 'synthetic', 'client_data': False, 'commercial_rights_assessed': False})
    return [row], {image_file: school.checked(Path(image['path']))}


def export(experience_paths):
    if not 1 <= len(experience_paths) <= 16:
        raise ValueError('Bounded integration batch of one to sixteen experiences required')
    rows, images = [], {}
    for path in experience_paths:
        archived = read(path)
        report = Path(archived['source']['report']); review = Path(archived['review']['path'])
        if archived != patch.experience(report, review):
            raise ValueError('Archived experience differs from the reviewed local model conversation')
        accepted, assets = collect(report, review)
        rows.extend(accepted); images.update(assets)
    if len({row['id'] for row in rows}) != len(rows):
        raise ValueError('Duplicate training candidate')
    out = Path(tempfile.mkdtemp(prefix='vision-candidates-', dir=school.ROOT))
    (out/'images').mkdir()
    for target, source in images.items():
        shutil.copyfile(source, out/target)
        if school.checksum(out/target) != Path(target).stem:
            raise ValueError('Image changed during export')
    payload = ''.join(json.dumps(row, ensure_ascii=False)+'\n' for row in rows)
    (out/'records.jsonl').write_text(payload)
    school.save(out/'manifest.json', {
        'schema': 'vision-candidate-bundle.v1', 'collector': COLLECTOR,
        'records': len(rows), 'records_sha256': sha256(payload.encode()).hexdigest(), 'split': 'train',
        'training_started': False, 'ready_for_trainer': False, 'production_ready': False,
        'requires': ['multimodal processor and label-mask audit', 'broader reviewed data',
                     'independent validation/test families'],
        'limitation': 'Reviewed local-model tool responses with reference PNGs. Integration candidates only; '
                      'no weight update, held-out gain or commercial delivery approval.'})
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiences', nargs='+', type=Path)
    parser.add_argument('--export', action='store_true')
    args = parser.parse_args()
    if args.export:
        print(json.dumps({'output': str(export(args.experiences)), 'training_started': False}))
    else:
        for path in args.experiences:
            entry = read(path)
            rows, _ = collect(Path(entry['source']['report']), Path(entry['review']['path']))
            print(json.dumps({'experience': str(path), 'approved': len(rows), 'training_started': False}))
