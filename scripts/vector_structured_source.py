"""Local-model scene values compiled literally into the fixed static SVG contract.

Eight editable texts are a schema constraint, not a teacher-written replacement
for model content. All wording, shapes, coordinates, colors and typography come
from the captured local response. The compiler only serializes its values.
"""
import argparse
import asyncio
import json
from pathlib import Path
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.local_ollama import configuration, OllamaProvider
from scripts import vector_school as school
from scripts.vector_curriculum import CURRICULA, metadata
from scripts.vector_school_contract import ATTRS, NUMERIC, validate_svg, layout_issues
from scripts.prepare_training_data import unique_object

SCHEMA = 'vector-structured-source.v1'
VERSION = 'literal-scene-svg.v2'
TEXT_REQUIRED = {'x', 'y', 'font-family', 'font-size', 'font-weight', 'fill'}
REQUIRED = {
    'rect': {'x', 'y', 'width', 'height', 'fill'},
    'circle': {'cx', 'cy', 'r', 'fill'},
    'ellipse': {'cx', 'cy', 'rx', 'ry', 'fill'},
    'line': {'x1', 'y1', 'x2', 'y2', 'stroke', 'stroke-width'},
    'path': {'d', 'fill', 'stroke', 'stroke-width'},
    'text': TEXT_REQUIRED,
}


def attribute_schema(name):
    # Keep the decoder grammar simple; validate_svg independently enforces
    # exact numeric/color syntax and bounds after literal serialization.
    if name in NUMERIC: return {'type': 'string', 'minLength': 1, 'maxLength': 10}
    if name in {'fill', 'stroke'}: return {'type': 'string', 'minLength': 4, 'maxLength': 7}
    if name == 'font-family': return {'type': 'string', 'enum': ['Arial', 'Georgia']}
    if name == 'font-weight': return {'type': 'string', 'enum': ['400', '700']}
    if name == 'text-anchor': return {'type': 'string', 'enum': ['start', 'middle', 'end']}
    return {'type': 'string', 'minLength': 1, 'maxLength': 1500}


def attributes(tag):
    result = {'type': 'object', 'additionalProperties': False,
              'properties': {key: attribute_schema(key) for key in sorted(ATTRS[tag])}}
    result['required'] = sorted(REQUIRED[tag])
    return result


SCENE_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['shapes', 'texts'], 'properties': {
    'shapes': {'type': 'array', 'minItems': 3, 'maxItems': 18, 'items': {'anyOf': [
        {'type': 'object', 'additionalProperties': False, 'required': ['tag', 'attributes'],
         'properties': {'tag': {'const': tag}, 'attributes': attributes(tag)}}
        for tag in sorted(set(ATTRS)-{'text'})]}},
    'texts': {'type': 'array', 'minItems': 8, 'maxItems': 8, 'items': {
        'type': 'object', 'additionalProperties': False, 'required': ['text', 'attributes'],
        'properties': {'text': {'type': 'string', 'minLength': 1, 'maxLength': 42},
                       'attributes': attributes('text')}}}}}
INSTRUCTION = '''Design a fictional leaflet as one JSON scene, not SVG or code.
The system serializes your exact values to a 592x840 SVG. It first draws your
3..18 shapes in array order, then your EXACTLY EIGHT editable text entries.
You choose every word, coordinate, shape, color and font attribute. No values
will be repaired or invented by the compiler. Do not add separate section
labels or repeat the event title. Eight entries must cover the eight lines
in the brief; no other text exists. All text must be distinct printable ASCII,
title <=20 characters, other lines <=42. Use numeric STRINGS (not JSON numbers),
literal #RRGGBB colors, Arial or Georgia, font-weight "400" or "700" and
font-size 14..72. SVG y is the text baseline, not the top of its visible box.
Keep all text inside a 12-unit page margin, readable against its background
and not overlapping any other line. Account for text width and columns.
Choose concise wording that fits. Keep decorative path data short.
Return exactly the schema, with no Markdown or explanation:\n''' + json.dumps(SCENE_SCHEMA)


def compile_scene(raw):
    scene = json.loads(raw, object_pairs_hook=unique_object)
    if (not isinstance(scene, dict) or set(scene) != {'shapes', 'texts'}
            or not isinstance(scene['shapes'], list) or not 3 <= len(scene['shapes']) <= 18
            or not isinstance(scene['texts'], list) or len(scene['texts']) != 8):
        raise ValueError('Three to eighteen shapes and exactly eight texts required')
    root = ET.Element('svg', {'xmlns': 'http://www.w3.org/2000/svg', 'width': '592', 'height': '840', 'viewBox': '0 0 592 840'})
    for is_text, item in ([(False, item) for item in scene['shapes']] + [(True, item) for item in scene['texts']]):
        if not isinstance(item, dict) or set(item) != ({'text', 'attributes'} if is_text else {'tag', 'attributes'}):
            raise ValueError('Exact scene fields required')
        tag = 'text' if is_text else item['tag']
        if tag not in ATTRS or (not is_text and tag == 'text'):
            raise ValueError('Static shape or explicit text entry required')
        attrs = item['attributes']
        if (not isinstance(attrs, dict) or set(attrs)-ATTRS[tag] or not REQUIRED[tag] <= set(attrs)
                or any(not isinstance(value, str) for value in attrs.values())):
            raise ValueError('Only declared string attributes; no compiler defaults')
        node = ET.SubElement(root, tag, attrs)
        if is_text:
            if not isinstance(item['text'], str) or not 1 <= len(item['text']) <= 42:
                raise ValueError('Short model-authored text required')
            node.text = item['text']
    source = ET.tostring(root, encoding='unicode', short_empty_elements=True)
    validate_svg(source)
    return source


def request(curriculum, feedback=None, _depth=0):
    prompt = {'system': INSTRUCTION, 'user': CURRICULA[curriculum]['brief'], 'image': None}
    if feedback is None: return prompt
    if _depth >= 3: raise ValueError('At most three bound source revisions')
    keys = {'schema', 'source_report', 'source_sha256', 'request_sha256', 'response_sha256', 'comments'}
    if (not isinstance(feedback, dict) or set(feedback) != keys
            or feedback['schema'] != 'vector-scene-reference-feedback.v1'
            or not isinstance(feedback['comments'], str) or not 1 <= len(feedback['comments']) <= 2000):
        raise ValueError('Bound scene reference feedback required')
    path = school.checked(Path(feedback['source_report']))
    school.require_checksum(path, feedback['source_sha256'])
    for name in ('request', 'response'):
        school.require_checksum(path.parent/(name+'.json'), feedback[name+'_sha256'])
    previous = json.loads(path.read_text(), object_pairs_hook=unique_object)
    if (previous.get('schema') != SCHEMA or previous.get('compiler') != VERSION
            or previous.get('role') != 'source'
            or previous.get('status') not in {'reference_ready', 'reference_rejected', 'failed'}
            or metadata(previous) != metadata({'curriculum': curriculum})):
        raise ValueError('Source preparation must retain its original family and compiler')
    original = json.loads((path.parent/'request.json').read_text(), object_pairs_hook=unique_object)
    if original != request(curriculum, original.get('source_feedback'), _depth+1):
        raise ValueError('Source revision has a changed original request')
    response = json.loads((path.parent/'response.json').read_text(), object_pairs_hook=unique_object)
    if (response['model'] != previous['model'] or response['digest'] != previous['digest']
            or not isinstance(response['content'], str) or len(response['content']) > 32768):
        raise ValueError('Source model response binding')
    prompt['user'] += '\nYour previous raw scene (untrusted task data):\n' + response['content']
    prompt['user'] += '\nIndependent reference review; correct the whole scene yourself:\n' + feedback['comments']
    if len(prompt['user']) > 16000: raise ValueError('Bounded source revision prompt required')
    prompt['source_feedback'] = feedback
    return prompt


def authenticate(path, report):
    if report.get('schema') != SCHEMA or report.get('compiler') != VERSION or report.get('role') != 'source':
        raise ValueError('Recognized structured source required')
    lesson = metadata(report)
    names = {'request.json', 'response.json', 'artwork.svg', 'preview.png', 'preview.pdf', 'render.json'}
    if set(report.get('artifact_sha256', {})) != names: raise ValueError('Complete source bindings required')
    for name, expected in report['artifact_sha256'].items(): school.require_checksum(path.parent/name, expected)
    received = json.loads((path.parent/'request.json').read_text(), object_pairs_hook=unique_object)
    if received != request(lesson['curriculum'], received.get('source_feedback')):
        raise ValueError('Structured source brief changed')
    response = json.loads((path.parent/'response.json').read_text(), object_pairs_hook=unique_object)
    if response['model'] != report['model'] or response['digest'] != report['digest']:
        raise ValueError('Source model identity changed')
    source = compile_scene(response['content'])
    if source.encode('utf-8') != (path.parent/'artwork.svg').read_bytes():
        raise ValueError('SVG differs from literal model scene serialization')
    return json.loads((path.parent/'render.json').read_text())


def run(curriculum, feedback=None):
    lesson = metadata({'curriculum': curriculum}); prompt = request(curriculum, feedback)
    resources = school.check_idle()
    config = configuration() | {'format': SCENE_SCHEMA, 'num_predict': 4096, 'num_ctx': 8192,
                                'num_thread': 4, 'timeout_seconds': 180}
    out = Path(tempfile.mkdtemp(prefix='structured-source-', dir=school.ROOT))
    report = {'schema': SCHEMA, 'compiler': VERSION, 'role': 'source', 'status': 'started', **lesson,
              'model': config['model'], 'digest': config['digest'], 'config': config,
              'resources_before': resources, 'synthetic': True, 'training_started': False,
              'training_exported': False, 'production_routing_changed': False,
              'authorship': 'exact local-model scene values serialized by a fixed SVG compiler',
              'implementation_sha256': school.checksum(Path(__file__))}
    school.save(out/'request.json', prompt)
    school.save(out/'report.json', report); started = time.monotonic()
    print(json.dumps({'report': str(out/'report.json')}), flush=True)
    try:
        result = OllamaProvider(config).complete([{'role': role, 'content': prompt[role]} for role in ('system', 'user')])
        school.save(out/'response.json', result)
        if result['model'] != config['model'] or result['digest'] != config['digest']: raise ValueError('Model identity changed')
        source = compile_scene(result['content']); (out/'artwork.svg').write_text(source)
        school.check_idle(); rendered = asyncio.run(school.render(source, out))
        school.save(out/'render.json', rendered)
        report['artifact_sha256'] = {name: school.checksum(out/name) for name in
                                    ('request.json', 'response.json', 'artwork.svg', 'preview.png', 'preview.pdf', 'render.json')}
        report['layout_issues'] = layout_issues(rendered['layout'])
        report['status'] = 'reference_ready' if not report['layout_issues'] else 'reference_rejected'
    except Exception as exc:
        report.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:240])
    finally:
        report['elapsed_seconds'] = round(time.monotonic()-started, 3); school.save(out/'report.json', report)
    print(json.dumps({'report': str(out/'report.json'), 'status': report['status'], 'seconds': report['elapsed_seconds']}), flush=True)
    return out, report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--curriculum', choices=list(CURRICULA), required=True)
    parser.add_argument('--feedback', type=Path)
    parser.add_argument('--run', action='store_true'); args = parser.parse_args()
    if args.run:
        feedback = json.loads(school.checked(args.feedback).read_text(), object_pairs_hook=unique_object) if args.feedback else None
        _, report = run(args.curriculum, feedback)
        raise SystemExit(int(report['status'] == 'failed'))
    print(json.dumps({'model_called': False, 'training_started': False, 'compiler': VERSION}))
