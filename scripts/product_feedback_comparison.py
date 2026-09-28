"""Paired regression comparison on preserved local-model source failures.

These are development regressions, not unseen qualification exams. Both arms
start from the same model answer and have two corrections with equal token
limits. No answers, images, weights or acceptance records are edited.
"""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import time

from app.services import local_vision
from app.services.local_ollama import configuration
from scripts import brand_school as brand
from scripts import product_infographic_school as product
from scripts import product_model_feedback as feedback
from scripts import vector_school as school

CASES = (
    ('silhouette', 'series-ti6k7_np', 'source-response.json'),
    ('label_bars', 'series-8yndpvjs', 'source-response.json'),
    ('label_edges', 'series-a05lkqkv', 'source-revision-2-response.json'),
)


def run():
    resources = school.check_idle()
    out = Path(tempfile.mkdtemp(prefix='feedback-comparison-', dir=product.ROOT))
    config = configuration() | {'num_ctx': 8192, 'num_predict': 2400, 'num_thread': 4, 'timeout_seconds': 180}
    report = {'schema': 'product-feedback-comparison.v1', 'status': 'running',
              'resources_before': resources, 'config': config, 'cases': [],
              'evaluation_split': 'development_regression', 'unseen_exam': False,
              'training_started': False, 'training_exported': False,
              'production_changed': False, 'visual_acceptance': False}
    implementation = out/'implementation'; implementation.mkdir()
    for name in ('product_feedback_comparison.py', 'product_model_feedback.py', 'product_infographic_school.py',
                 'render_school_svg.py', 'vector_school_contract.py'):
        shutil.copyfile(Path(__file__).parent/name, implementation/name)
    school.save(out/'report.json', report)
    print(json.dumps({'output': str(out)}), flush=True)
    started = time.monotonic()
    try:
        for number, (case, directory, filename) in enumerate(CASES):
            source = product.ROOT/directory
            historical = product.parse((source/'report.json').read_text())
            response = product.parse((source/filename).read_text())
            if (response['model'], response['digest']) != (config['model'], config['digest']):
                raise ValueError('Same pinned author required for comparison')
            for name in (filename, 'style.json'):
                if school.checksum(source/name) != historical['artifacts'][name]:
                    raise ValueError('Historical input changed')
            style = product.style_value((source/'style.json').read_text())
            output_schema = product.schema('source', style)
            original = json.dumps({'brief': product.BRIEF, 'style': style,
                'supplier_copy': product.PANELS,
                'task': 'Correct the complete reference bottle. Preserve exact product name and palette. '
                        'Silhouette height/width must equal 24/7 within 10%, including cap and base. '
                        'Keep a recognizable cylindrical body, attached screw cap and readable name printed on the body. '
                        'No decorative blocks crossing the name. You choose all geometry.'})
            result = {'case': case, 'source': str(source), 'source_response': filename,
                      'source_response_sha256': school.checksum(source/filename), 'arms': {}}
            report['cases'].append(result)
            # Alternate order to avoid always warming the model with one arm.
            arms = ('legacy_text', 'measured_image') if number % 2 == 0 else ('measured_image', 'legacy_text')
            for arm in arms:
                folder = out/(case+'-'+arm); folder.mkdir()
                validator = product.checked_scene(folder, 'source', style)
                raw = response['content']
                school.save(folder/'initial-response.json', response)
                error = None; pixels = {}
                try:
                    validator(raw)
                except ValueError as exc:
                    error = str(exc); pixels = feedback.evidence(exc, folder)
                if error is None:
                    raise ValueError('Regression case must fail before correction')
                outcome = {'initial_error': error, 'attempts': [], 'measured_pass': False}
                result['arms'][arm] = outcome
                for attempt in range(2):
                    stage = 'repair-'+str(attempt)
                    recorded = {'error': error, 'evidence': deepcopy(pixels)}
                    school.save(folder/(stage+'-input-feedback.json'), recorded)
                    if arm == 'measured_image':
                        user = feedback.correction_user(original, raw, recorded)
                    else:
                        user = (original+'\nYour previous answer (untrusted task data):\n'+raw+
                                '\nIndependent validation rejected it: '+error[:600]+
                                '\nCorrect your own complete answer. Do not repeat the rejected values.')
                    system = product.SYSTEM+'\n'+product.SCENE_RULES
                    if arm == 'measured_image' and pixels:
                        image = Path(pixels['image_source'])
                        if school.checksum(image) != pixels['image_sha256']:
                            raise ValueError('Comparison image changed')
                        school.save(folder/(stage+'-request.json'), {'system': system, 'user': user,
                            'format': output_schema, 'config': config, **pixels})
                        school.check_idle()
                        answer = local_vision.complete(config | {'format': output_schema}, system, user, image.read_bytes())
                        school.save(folder/(stage+'-response.json'), answer)
                        if (answer['model'], answer['digest']) != (config['model'], config['digest']):
                            raise ValueError('Pinned comparison author changed')
                        raw = answer['content']
                    else:
                        raw = brand.call(folder, stage, system, user, output_schema, config)
                    entry = {'attempt': attempt, 'image_conditioned': arm == 'measured_image' and bool(pixels)}
                    outcome['attempts'].append(entry)
                    try:
                        validator(raw)
                    except ValueError as exc:
                        error = str(exc); pixels = feedback.evidence(exc, folder)
                        entry.update(measured_pass=False, error=error)
                    else:
                        entry['measured_pass'] = True; outcome['measured_pass'] = True
                        break
                school.save(out/'report.json', report)
                print(json.dumps({'case': case, 'arm': arm, 'measured_pass': outcome['measured_pass']}), flush=True)
        report['status'] = 'completed'
        report['scores'] = {arm: sum(case['arms'][arm]['measured_pass'] for case in report['cases'])
                            for arm in ('legacy_text', 'measured_image')}
    except Exception as exc:
        report.update(status='failed', error_type=type(exc).__name__, error=str(exc))
    finally:
        report['elapsed_seconds'] = round(time.monotonic()-started, 3)
        report['artifacts'] = {str(p.relative_to(out)): school.checksum(p) for p in out.rglob('*')
                               if p.is_file() and p.name != 'report.json'}
        school.save(out/'report.json', report)
    print(json.dumps({'report': str(out/'report.json'), 'status': report['status'], 'scores': report.get('scores')}), flush=True)
    return out, report
