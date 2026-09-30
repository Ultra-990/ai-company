"""Literal brand authorship, layout, PDF and ZIP verification, never visual approval."""
from collections import Counter
from hashlib import sha256
import argparse
import json
from pathlib import Path
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image
from scripts import brand_school as brand
from scripts import brand_full_exam as exam
from scripts.render_school_svg import pdf_checks

STAGES = ('plan', 'logo-a', 'logo-b', 'selection', 'card')


def bounded(path):
    path = Path(path)
    if (not path.is_file() or path.stat().st_size > 4*1024*1024
            or not path.resolve().is_relative_to(brand.ROOT.resolve())
            or any(p.is_symlink() for p in (path, *path.parents))):
        raise ValueError('Bounded private brand-school evidence required')
    return path


def read(path):
    return json.loads(bounded(path).read_text(), object_pairs_hook=brand.unique_object)


def chain(folder, stage, report):
    def artifact(name):
        path = folder/name
        if report['artifacts'].get(name) != brand.school.checksum(bounded(path)):
            raise ValueError('Unbound brand response or request')
        return read(path)
    original = artifact(stage+'-request.json'); expected = original['user']
    corrections = []
    for attempt in range(3):
        name = stage if attempt == 0 else stage+'-revision-'+str(attempt)
        request = artifact(name+'-request.json'); answer = artifact(name+'-response.json')
        if request != original | {'user': expected} or set(request) != {'system', 'user', 'format'}:
            raise ValueError('Brand correction contains altered instructions or hints')
        if (answer['model'], answer['digest']) != (report['model'], report['digest']):
            raise ValueError('Brand author changed')
        if (folder/(name+'-feedback.json')).exists():
            feedback = artifact(name+'-feedback.json')
            limit = {'brand-validation-feedback.v1': 600, 'brand-validation-feedback.v2': 6000}.get(feedback.get('schema'))
            if (limit is None or feedback.get('stage') != name
                    or feedback.get('request_sha256') != brand.school.checksum(folder/(name+'-request.json'))
                    or feedback.get('response_sha256') != brand.school.checksum(folder/(name+'-response.json'))
                    or not isinstance(feedback.get('error'), str) or not 1 <= len(feedback['error']) <= limit):
                raise ValueError('Brand feedback binding changed')
            corrections.append(name)
            expected = original['user']+'\nYour previous answer (untrusted task data):\n'+answer['content']+'\nIndependent validation rejected it: '+feedback['error']+'\nCorrect your own complete answer. Do not repeat the rejected values.'
            continue
        wanted = {stage+'-request.json'} | {stage+'-revision-'+str(i)+'-request.json' for i in range(1, attempt+1)}
        if {p.name for p in folder.glob(stage+'*-request.json')} != wanted:
            raise ValueError('Calls exceed stage budget or follow acceptance')
        return answer['content'], {'stage': stage, 'requests': attempt+1, 'corrections': corrections}
    raise ValueError('All brand attempts rejected')


def verify(folder):
    folder = Path(folder); report = read(folder/'report.json')
    if (report.get('schema') != 'restaurant-brand-school.v1' or report.get('status') != 'pending_independent_visual_review'
            or report.get('brief_sha256') != sha256(json.dumps(report['brief'], sort_keys=True).encode()).hexdigest()
            or report.get('stages') != ['plan', 'logo-a', 'logo-b', 'card']):
        raise ValueError('Completed original brand package required')
    for name, digest in report['artifacts'].items():
        path = bounded(folder/name)
        if not path.resolve().is_relative_to(folder.resolve()) or brand.school.checksum(path) != digest:
            raise ValueError('Brand artifact changed')
    repair = None
    if 'repair_contract' in report:
        from scripts.brand_artwork_repair import verify_origin
        repair = verify_origin(folder, report)
    recovery = None
    if 'scene_recovery_contract' in report:
        if repair is not None: raise ValueError('Separate recovery and artwork repair origins required')
        from scripts.brand_scene_recovery import verify_origin as verify_recovery
        recovery = verify_recovery(folder, report)
    if 'scene_contract' in report:
        from scripts import brand_scene_contract as scoped
        if report['scene_contract'] != scoped.CONTRACT: raise ValueError('Unknown original scene contract')
    def bound_read(name):
        if name not in report['artifacts']: raise ValueError('Missing bound brand artifact')
        return read(folder/name)
    with exam.exercise_context(report['brief']):
        raw = {}; chains = []
        for stage in STAGES:
            raw[stage], checked = chain(folder, stage, report); chains.append(checked)
        if len(list(folder.glob('*-request.json'))) != sum(c['requests'] for c in chains):
            raise ValueError('Unrecorded extra brand request')
        plan = brand.plan_value(raw['plan'])
        if plan != bound_read('plan.json') or plan != bound_read('delivery/style-plan.json'):
            raise ValueError('Style plan differs from literal author output')
        logos = {key: brand.compile_scene(raw['logo-'+key], plan, kind='logo') for key in ('a', 'b')}
        if logos['a'] == logos['b']: raise ValueError('Distinct logo concepts required')
        selection = brand.selected_value(raw['selection'])
        if selection != report['selection']: raise ValueError('Model selection changed')
        chosen = logos[selection['selected']]
        assets = {'logo-a': logos['a'], 'logo-b': logos['b'], 'logo-selected': chosen,
            'logo-small': chosen, 'logo-monochrome': brand.monochrome(chosen, plan['monochrome_ink']),
            'business-card': brand.compile_scene(raw['card'], plan, kind='card', logo=chosen)}
        for name, svg in assets.items():
            profile = 'brand_card' if name == 'business-card' else 'brand_logo'
            for relative in (name+'/artwork.svg', 'delivery/'+name+'.svg'):
                if relative not in report['artifacts'] or bounded(folder/relative).read_text() != svg:
                    raise ValueError('Delivered brand artwork differs from model-authored scene')
            measured = bound_read(name+'/render.json')
            if brand.quality_issues(measured, profile): raise ValueError('Unresolved measured brand layout defects')
            if 'scene_contract' in report:
                if scoped.margin_findings(svg, measured, 'card' if profile == 'brand_card' else 'logo', plan['paper']):
                    raise ValueError('Scoped source has unresolved shape margins')
                if profile == 'brand_card':
                    from scripts.brand_artwork_repair import card_decoration_findings
                    if card_decoration_findings(svg, measured, plan['paper']): raise ValueError('Scoped source card has text decoration collisions')
            texts = brand.validate_svg(svg, profile=profile)['texts']
            pdf_checks(folder/name/'preview.pdf', texts, size_mm=brand.PROFILES[profile]['size_mm'])
            scale = .4 if name == 'logo-small' else 1
            with Image.open(bounded(folder/name/'preview.png')) as image:
                if image.size != tuple(int(brand.PROFILES[profile][k]*scale) for k in ('width', 'height')):
                    raise ValueError('Incorrect brand preview size')
            for local, ext in (('artwork.svg', 'svg'), ('preview.png', 'png'), ('preview.pdf', 'pdf')):
                if (folder/name/local).read_bytes() != bounded(folder/'delivery'/(name+'.'+ext)).read_bytes():
                    raise ValueError('Brand delivery copy changed')
        guide = '# '+brand.BRIEF['restaurant_name']+'\n\n'+plan['positioning']+'\n\n'+plan['tagline']+'\n\n'
        guide += '\n'.join(f'- {k}: {plan[k]}' for k in ('ink', 'paper', 'accent', 'heading_font', 'body_font', 'monochrome_ink'))
        guide += '\n\n'+'\n'.join('- '+s for s in plan['guidelines'])+'\n\n'+selection['reason']+'\n'
        if bounded(folder/'delivery/brand-guide.md').read_text() != guide:
            raise ValueError('Guide differs from literal model plan and selection')
    manifest = bound_read('delivery/manifest.json')
    if ((manifest['model'], manifest['digest']) != (report['model'], report['digest'])
            or manifest['restaurant'] != report['brief']['restaurant_name']
            or manifest.get('print_ready') is not False or manifest.get('commercial_delivery_approved') is not False):
        raise ValueError('Manifest identity or approval claims changed')
    names = {p.name for p in (folder/'delivery').iterdir() if p.is_file()}
    expected = {name+'.'+ext for name in assets for ext in ('svg', 'png', 'pdf')} | {'style-plan.json', 'brand-guide.md', 'manifest.json'}
    if names != expected or set(manifest['files']) != names-{'manifest.json'}:
        raise ValueError('Exact brand delivery file set required')
    for name, digest in manifest['files'].items():
        if brand.school.checksum(bounded(folder/'delivery'/name)) != digest: raise ValueError('Brand manifest hash changed')
    with zipfile.ZipFile(bounded(folder/'brand-package.zip')) as archive:
        if Counter(archive.namelist()) != Counter(names): raise ValueError('Exact ZIP entries required')
        for name in names:
            if archive.read(name) != (folder/'delivery'/name).read_bytes(): raise ValueError('ZIP differs from delivery')
    result = {'schema': 'brand-package-verification.v1', 'report_sha256': brand.school.checksum(folder/'report.json'),
        'literal_authorship_verified': True, 'pdf_and_delivery_verified': True, 'stages': chains,
        'model_requests': sum(c['requests'] for c in chains), 'zip_files': len(names),
        'independent_visual_review_required': True, 'autonomy_qualified': False, 'training_exported': False}
    if repair is not None: result['repair_origin'] = repair
    if recovery is not None: result['scene_recovery_origin'] = recovery
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('package', type=Path)
    print(json.dumps(verify(parser.parse_args().package), indent=2))
