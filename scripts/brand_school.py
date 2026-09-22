"""Local-model restaurant identity trial; teacher code only validates and exports.

All wording, palettes, geometry and placement values come from captured model
responses. Logo reuse and monochrome conversion are literal declared tool actions.
No brand asset is repaired by the compiler or admitted to training automatically.
"""
import argparse
import asyncio
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pydantic import BaseModel, ConfigDict, Field
from typing import Annotated, Literal
from app.services.local_ollama import configuration, OllamaProvider
from scripts import vector_structured_source as scene
from scripts import vector_school as school
from scripts.vector_school_contract import PROFILES, ATTRS, NS, validate_svg, layout_issues
from scripts.render_school_svg import render
from scripts.prepare_training_data import unique_object

ROOT = Path('/home/marcin/ai-company-workspaces/brand-school')
BRIEF = {'restaurant_name': 'Juniper Table', 'family': 'juniper-table-identity-001', 'split': 'train',
         'concept': 'Fictional neighborhood restaurant serving seasonal plant-forward dinners. Warm, quietly confident and welcoming; avoid luxury crests and generic fork/knife clip art.',
         'audience': 'Adults meeting friends for relaxed, thoughtful dinners.',
         'contacts': ['Reservations by email', 'hello@junipertable.example', 'junipertable.example'],
         'synthetic': True, 'printer_specifications_supplied': False}


class Plan(BaseModel):
    model_config = ConfigDict(extra='forbid')
    positioning: str = Field(min_length=20, max_length=350)
    tagline: str = Field(min_length=5, max_length=32)
    ink: str = Field(min_length=7, max_length=7, description='Literal #RRGGBB hexadecimal color, not a name.')
    paper: str = Field(min_length=7, max_length=7, description='Literal #RRGGBB hexadecimal color, not a name.')
    accent: str = Field(min_length=7, max_length=7, description='Literal #RRGGBB hexadecimal color, not a name.')
    heading_font: Literal['Arial', 'Georgia']
    body_font: Literal['Arial', 'Georgia']
    monochrome_ink: str = Field(min_length=7, max_length=7, description='Literal #RRGGBB hexadecimal color, not a name.')
    concept_a: str = Field(min_length=20, max_length=300)
    concept_b: str = Field(min_length=20, max_length=300)
    guidelines: list[Annotated[str, Field(min_length=20, max_length=350)]] = Field(min_length=4, max_length=4)


def plan_value(raw):
    plan = Plan.model_validate(json.loads(raw, object_pairs_hook=unique_object)).model_dump()
    colors = [plan[k] for k in ('ink', 'paper', 'accent', 'monochrome_ink')]
    if any(not re.fullmatch(r'#[0-9A-Fa-f]{6}', c) for c in colors) or len(set(colors[:3])) != 3:
        raise ValueError('Three distinct literal palette colors and monochrome ink required')
    if any(not 20 <= len(s) <= 350 for s in plan['guidelines']): raise ValueError('Four concise usage rules required')
    if any(not 32 <= ord(c) <= 126 for c in plan['tagline']): raise ValueError('Printable ASCII tagline required')
    if plan['tagline'] != plan['tagline'].strip() or plan['tagline'][-1] in ',;:-':
        raise ValueError('Tagline must be a complete short phrase, without trailing whitespace or a dangling comma')
    return plan


def scene_schema(kind, plan=None):
    result = deepcopy(scene.SCENE_SCHEMA)
    result['properties']['shapes'].update(minItems=1, maxItems=12)
    result['properties']['texts'].update(minItems=1 if kind == 'logo' else 4, maxItems=1 if kind == 'logo' else 4)
    result['properties']['texts']['items']['properties']['attributes']['required'].append('text-anchor')
    if kind == 'card':
        result['required'].append('logo_placement')
        result['properties']['logo_placement'] = {'type': 'object', 'additionalProperties': False,
            'required': ['x', 'y', 'scale'], 'properties': {k: {'type': 'string', 'minLength': 1, 'maxLength': 10} for k in ('x', 'y', 'scale')}}
    if plan is not None:
        palettes = [plan['ink'], plan['paper'], plan['accent'], 'none']
        attrs = result['properties']['texts']['items']['properties']['attributes']['properties']
        attrs['fill'] = {'type': 'string', 'enum': palettes[:-1]}
        attrs['font-family'] = {'type': 'string', 'enum': [plan['heading_font'] if kind == 'logo' else plan['body_font']]}
        for shape in result['properties']['shapes']['items']['anyOf']:
            fields = shape['properties']['attributes']['properties']
            for key in ('fill', 'stroke'):
                if key in fields: fields[key] = {'type': 'string', 'enum': palettes}
    return result


def append_nodes(root, items, *, text=False):
    if not isinstance(items, list): raise ValueError('Explicit scene arrays required')
    for item in items:
        if not isinstance(item, dict) or set(item) != ({'text', 'attributes'} if text else {'tag', 'attributes'}):
            raise ValueError('Exact scene fields required')
        tag = 'text' if text else item['tag']
        if not isinstance(tag, str) or tag not in ATTRS or (not text and tag == 'text'):
            raise ValueError('Declared static shape required')
        attrs = item['attributes']
        if (not isinstance(attrs, dict) or set(attrs)-ATTRS[tag] or not scene.REQUIRED[tag] <= set(attrs)
                or any(not isinstance(v, str) for v in attrs.values())):
            raise ValueError('Complete literal model attributes required')
        node = ET.SubElement(root, tag, attrs)
        if text:
            if not isinstance(item['text'], str): raise ValueError('Model text required')
            node.text = item['text']


def compile_scene(raw, plan, *, kind, logo=None):
    value = json.loads(raw, object_pairs_hook=unique_object)
    fields = {'shapes', 'texts'} | ({'logo_placement'} if kind == 'card' else set())
    if not isinstance(value, dict) or set(value) != fields: raise ValueError('Exact brand scene fields required')
    if not isinstance(value['shapes'], list) or not 1 <= len(value['shapes']) <= 12:
        raise ValueError('One to twelve model shapes required')
    if not isinstance(value['texts'], list) or len(value['texts']) != (1 if kind == 'logo' else 4):
        raise ValueError('Required text count')
    profile = 'brand_'+kind; spec = PROFILES[profile]
    root = ET.Element('svg', {'xmlns': NS[1:-1], 'width': str(spec['width']), 'height': str(spec['height']),
                              'viewBox': f"0 0 {spec['width']} {spec['height']}"})
    append_nodes(root, value['shapes'])
    if kind == 'card':
        validate_svg(logo, profile='brand_logo')
        placement = value['logo_placement']
        if not isinstance(placement, dict) or set(placement) != {'x', 'y', 'scale'}:
            raise ValueError('Explicit model logo placement required')
        if any(not isinstance(v, str) or not re.fullmatch(r'\d{1,4}(?:\.\d{1,4})?', v) for v in placement.values()):
            raise ValueError('Literal logo placement numbers required')
        group = ET.SubElement(root, 'g', {'transform': f"translate({placement['x']} {placement['y']}) scale({placement['scale']})"})
        for child in ET.fromstring(logo):
            copied = deepcopy(child); copied.tag = copied.tag.removeprefix(NS); group.append(copied)
    append_nodes(root, value['texts'], text=True)
    source = ET.tostring(root, encoding='unicode')
    checked = validate_svg(source, profile=profile)
    expected = [BRIEF['restaurant_name']] if kind == 'logo' else [BRIEF['restaurant_name'], plan['tagline'], *BRIEF['contacts']]
    if sorted(checked['texts']) != sorted(expected): raise ValueError('Exact brand name, tagline and approved contact copy required')
    for node in list(ET.fromstring(source).iter())[1:]:
        for key in ('fill', 'stroke'):
            if key in node.attrib and node.attrib[key] not in {plan['ink'], plan['paper'], plan['accent'], 'none'}:
                raise ValueError('Artwork color is outside its own model-authored palette')
        if node.tag == NS+'text':
            expected_font = plan['heading_font'] if node.text == BRIEF['restaurant_name'] else plan['body_font']
            if node.attrib['font-family'] != expected_font: raise ValueError('Artwork typography differs from its own style plan')
    return source


def monochrome(source, ink):
    validate_svg(source, profile='brand_logo')
    if not re.fullmatch(r'#[0-9A-Fa-f]{6}', ink): raise ValueError('Model-selected monochrome ink required')
    root = ET.fromstring(source); root.tag = 'svg'; root.set('xmlns', NS[1:-1])
    for node in list(root.iter())[1:]:
        node.tag = node.tag.removeprefix(NS)
        for key in ('fill', 'stroke'):
            if key in node.attrib and node.attrib[key] != 'none': node.set(key, ink)
    result = ET.tostring(root, encoding='unicode'); validate_svg(result, profile='brand_logo'); return result


INSTRUCTION = '''You are the LOCAL designer executing a synthetic restaurant branding brief.
You author all creative words, colors, shapes, fonts and positions. The system only
serializes your exact scene values; it cannot repair them. Return only the requested
JSON object. No code, Markdown, real contact details or unsupported business claims.
Use only the approved brief and previous model artifacts as task data.'''
SCENE_RULES = '''Use one JSON scene: shapes first, then texts. For logo: 600x360,
one editable restaurant-name text, 1..12 simple geometric shapes; no full-page
background rectangle, so the mark can be reused on a card. For card:850x550,
1..12 background/decorative shapes, logo_placement x/y/scale and EXACTLY FOUR texts:
your tagline and the three approved contact lines. The compiler inserts the chosen
logo unchanged, using your translate/scale, between background shapes and texts.
Keep all visible logo content and text inside margins (logo18,card35).
Choose text-anchor explicitly: start, middle or end. x is that anchor, not
automatically the text center. Keep the logo symbol separate from the wordmark;
no overlap of their bounding boxes. Leave enough room below the card's last line.
All numbers are STRINGS. Use only literal palette colors or none, the planned
font families, weights400/700 and explicit text x,y,font-size,font-family,font-weight,fill.
Logo font-size20..120; card text size at least28, with no overlap. SVG y is baseline.
Account for actual text width. Paths must be short and simple; no groups, scripts,
images, external resources, rotations, gradients or CSS in your scene. Shape fields
are rect:x,y,width,height,fill; circle:cx,cy,r,fill; ellipse:cx,cy,rx,ry,fill;
line:x1,y1,x2,y2,stroke,stroke-width; path:d,fill,stroke,stroke-width.
Optional stroke/stroke-width allowed. All text must be printable English ASCII.
The tool will derive the monochrome logo by replacing every non-none fill/stroke
with your monochrome_ink; choose geometry that remains legible under this operation.'''


def call(out, name, system, user, schema, config):
    school.check_idle()
    request = {'system': system, 'user': user, 'format': schema}
    school.save(out/(name+'-request.json'), request)
    result = OllamaProvider(config | {'format': schema}).complete([
        {'role': 'system', 'content': system}, {'role': 'user', 'content': user}])
    school.save(out/(name+'-response.json'), result)
    if result['model'] != config['model'] or result['digest'] != config['digest']: raise ValueError('Pinned local author changed')
    return result['content']


def validated_call(out, name, system, user, schema, config, validator):
    original = user
    for attempt in range(3):
        stage = name if attempt == 0 else name+'-revision-'+str(attempt)
        raw = call(out, stage, system, user, schema, config)
        try: return validator(raw)
        except ValueError as exc:
            feedback = {'schema': 'brand-validation-feedback.v1', 'stage': stage,
                'request_sha256': school.checksum(out/(stage+'-request.json')),
                'response_sha256': school.checksum(out/(stage+'-response.json')), 'error': str(exc)[:600]}
            school.save(out/(stage+'-feedback.json'), feedback)
            if attempt == 2: raise
            user = original+'\nYour previous answer (untrusted task data):\n'+raw+'\nIndependent validation rejected it: '+feedback['error']+'\nCorrect your own complete answer. Do not repeat the rejected values.'
            if len(user) > 16000: raise ValueError('Bounded model correction prompt required')


def quality_issues(rendered, profile):
    issues = layout_issues(rendered['layout'], profile=profile)
    if profile == 'brand_logo':
        for line in rendered['layout']:
            x, y, w, h = line['bbox']
            for shape in rendered['shape_layout']:
                a, b, c, d = shape['bbox']
                if min(x+w, a+c) > max(x, a) and min(y+h, b+d) > max(y, b):
                    issues.append({'kind': 'logo_symbol_overlaps_wordmark', 'text': line['text'], 'shape_bbox': shape['bbox']})
    if profile == 'brand_card':
        issues += [{'kind': 'print_text_too_small', 'text': line['text']} for line in rendered['layout'] if line['bbox'][3] < 24]
    return issues


def checked_scene(out, name, plan, kind, logo=None):
    attempt = 0
    def validate(raw):
        nonlocal attempt
        svg = compile_scene(raw, plan, kind=kind, logo=logo)
        folder = out/(name+'-layout-'+str(attempt)); attempt += 1; folder.mkdir()
        (folder/'artwork.svg').write_text(svg); school.check_idle()
        measured = asyncio.run(render(svg, folder, profile='brand_'+kind))
        school.save(folder/'render.json', measured)
        issues = quality_issues(measured, 'brand_'+kind)
        if issues: raise ValueError('Correct the measured layout defects yourself: '+json.dumps(issues))
        return svg
    return validate


def selected_value(raw):
    value = json.loads(raw, object_pairs_hook=unique_object)
    if (not isinstance(value, dict) or set(value) != {'selected', 'reason'} or value['selected'] not in {'a', 'b'}
            or not isinstance(value['reason'], str) or not 20 <= len(value['reason']) <= 400
            or value['reason'] != value['reason'].strip() or value['reason'][-1] not in '.!?'):
        raise ValueError('Select a or b with ONE SHORT COMPLETE sentence explaining your choice')
    return value


def run():
    ROOT.mkdir(exist_ok=True)
    if any(p.is_symlink() for p in (ROOT, *ROOT.parents)): raise ValueError('Private Linux workspace required')
    resources = school.check_idle(); out = Path(tempfile.mkdtemp(prefix='identity-', dir=ROOT))
    config = configuration() | {'num_ctx': 8192, 'num_predict': 4096, 'num_thread': 4, 'timeout_seconds': 180}
    report = {'schema': 'restaurant-brand-school.v1', 'status': 'running', 'brief': BRIEF,
        'brief_sha256': sha256(json.dumps(BRIEF, sort_keys=True).encode()).hexdigest(), 'model': config['model'],
        'digest': config['digest'], 'config': config, 'resources_before': resources, 'training_started': False,
        'training_exported': False, 'production_changed': False, 'print_ready': False, 'commercial_delivery_approved': False,
        'stages': [], 'checks': {}, 'implementation_sha256': school.checksum(Path(__file__))}
    school.save(out/'report.json', report); started = time.monotonic(); print(json.dumps({'output': str(out)}), flush=True)
    try:
        plan = validated_call(out, 'plan', INSTRUCTION, json.dumps(BRIEF)+'\nDevelop two distinct logo directions and a concise coherent style plan. Write ONE SHORT COMPLETE SENTENCE per positioning, concept and guideline field: aim for 100 characters, never more than 160. Tagline: a complete phrase of at most24characters. Do not write paragraphs or fill the schema limit. ink, paper, accent and monochrome_ink MUST be literal seven-character #RRGGBB hexadecimal strings, not names. Four guidelines: palette roles, typography, clear space/small use, monochrome use. Both logo concepts MUST use heading_font; vary symbols/layout instead of contradicting that font selection. Describe only assets we produce: two concepts, a selected logo with its wordmark, a monochrome version, a small full-logo preview, and one 85x55mm card. Do not promise extra symbol-only files, wordmark-only variants, legibility on every background, or printer-specific readiness.', Plan.model_json_schema(), config, plan_value)
        school.save(out/'plan.json', plan); report['stages'].append('plan')
        logos = {}
        for name in ('a', 'b'):
            prompt = json.dumps({'brief': BRIEF, 'plan': plan, 'task': 'Develop logo concept '+name.upper(), 'direction': plan['concept_'+name]})
            logos[name] = validated_call(out, 'logo-'+name, INSTRUCTION+'\n'+SCENE_RULES, prompt, scene_schema('logo', plan), config,
                                        checked_scene(out, 'logo-'+name, plan, 'logo'))
            report['stages'].append('logo-'+name)
            (out/('logo-'+name+'.svg')).write_text(logos[name])
        if logos['a'] == logos['b']: raise ValueError('Two distinct logo concepts required')
        selection_schema = {'type': 'object', 'additionalProperties': False, 'required': ['selected', 'reason'], 'properties': {
            'selected': {'enum': ['a', 'b']}, 'reason': {'type': 'string', 'minLength': 20, 'maxLength': 400}}}
        selection = validated_call(out, 'selection', INSTRUCTION, json.dumps({'brief': BRIEF, 'plan': plan, 'logo_sources': logos,
            'task': 'Select one concept and explain in ONE SHORT COMPLETE sentence (aim <=120 characters). Selection is based on scene data; independent visual approval is separate.'}), selection_schema, config, selected_value)
        chosen = logos[selection['selected']]; report['selection'] = selection
        card = validated_call(out, 'card', INSTRUCTION+'\n'+SCENE_RULES, json.dumps({'brief': BRIEF, 'plan': plan,
            'chosen_logo_svg': chosen, 'task': 'Design the 85x55mm business card. Choose the placement of the existing logo and all four other lines yourself.'}), scene_schema('card', plan), config,
            checked_scene(out, 'card', plan, 'card', logo=chosen))
        report['stages'].append('card')
        mono = monochrome(chosen, plan['monochrome_ink'])
        assets = {'logo-a': (logos['a'], 'brand_logo', 1), 'logo-b': (logos['b'], 'brand_logo', 1),
                  'logo-selected': (chosen, 'brand_logo', 1), 'logo-monochrome': (mono, 'brand_logo', 1),
                  'logo-small': (chosen, 'brand_logo', .4), 'business-card': (card, 'brand_card', 1)}
        delivery = out/'delivery'; delivery.mkdir()
        for name, (svg, profile, scale) in assets.items():
            folder = out/name; folder.mkdir(); (folder/'artwork.svg').write_text(svg)
            school.check_idle(); rendered = asyncio.run(render(svg, folder, profile=profile, png_scale=scale))
            from PIL import Image
            with Image.open(folder/'preview.png') as preview:
                if preview.size != (int(PROFILES[profile]['width']*scale), int(PROFILES[profile]['height']*scale)):
                    raise ValueError('Actual preview dimensions differ from requested scale')
            school.save(folder/'render.json', rendered)
            issues = quality_issues(rendered, profile)
            report['checks'][name] = {'issues': issues, 'pdf': rendered['pdf']}
            for source_name, extension in (('artwork.svg', 'svg'), ('preview.png', 'png'), ('preview.pdf', 'pdf')):
                shutil.copyfile(folder/source_name, delivery/(name+'.'+extension))
        guide = '# '+BRIEF['restaurant_name']+'\n\n'+plan['positioning']+'\n\n'+plan['tagline']+'\n\n'
        guide += '\n'.join(f'- {k}: {plan[k]}' for k in ('ink', 'paper', 'accent', 'heading_font', 'body_font', 'monochrome_ink'))
        guide += '\n\n'+'\n'.join('- '+s for s in plan['guidelines'])+'\n\n'+selection['reason']+'\n'
        (delivery/'brand-guide.md').write_text(guide); school.save(delivery/'style-plan.json', plan)
        manifest = {'schema': 'synthetic-brand-package.v1', 'restaurant': BRIEF['restaurant_name'], 'model': config['model'],
            'digest': config['digest'], 'files': {p.name: school.checksum(p) for p in sorted(delivery.iterdir())},
            'business_card_mm': [85, 55], 'synthetic': True, 'print_ready': False, 'commercial_delivery_approved': False,
            'authorship': 'Local model scene values; literal XML serialization, selected-logo reuse and model-directed monochrome conversion.'}
        school.save(delivery/'manifest.json', manifest)
        with zipfile.ZipFile(out/'brand-package.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(delivery.iterdir()): archive.write(path, path.name)
        report['status'] = 'needs_revision' if any(c['issues'] for c in report['checks'].values()) else 'pending_independent_visual_review'
    except Exception as exc:
        report.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:400])
    finally:
        report['elapsed_seconds'] = round(time.monotonic()-started, 3)
        report['artifacts'] = {str(p.relative_to(out)): school.checksum(p) for p in out.rglob('*') if p.is_file() and p.name != 'report.json'}
        school.save(out/'report.json', report)
    print(json.dumps({'report': str(out/'report.json'), 'status': report['status']}), flush=True)
    return out, report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--run', action='store_true'); args = parser.parse_args()
    if args.run:
        _, report = run(); raise SystemExit(int(report['status'] == 'failed'))
    print(json.dumps({'model_called': False, 'training_started': False, 'brief': BRIEF}))
