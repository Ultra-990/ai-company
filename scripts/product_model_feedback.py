"""Bounded local-model correction using the pixels of its latest rejected scene.

This module never changes an answer or supplies replacement artwork. Every
request, response, measurement and input image remains bound to its attempt.
"""
import json
from pathlib import Path

from app.services import local_vision
from scripts import brand_school as brand
from scripts import vector_school as school

CONTRACT = 'product-measured-image-feedback.v1'


class SceneFailure(ValueError):
    def __init__(self, message, folder, measured=None):
        super().__init__(message)
        self.folder = Path(folder)
        self.measured = measured


def evidence(exc, out):
    if not isinstance(exc, SceneFailure):
        return {}
    folder = exc.folder
    if any(p.is_symlink() for p in (folder, *folder.parents)) or not folder.resolve().is_relative_to(out.resolve()):
        raise ValueError('Correction evidence must belong to this trial')
    files = [folder/'preview.png', folder/'artwork.svg']
    if any(p.is_symlink() for p in files):
        raise ValueError('Correction evidence cannot be symlinked')
    if not all(p.is_file() for p in files):
        return {}
    result = {'image_source': str(files[0]), 'image_sha256': school.checksum(files[0]),
              'svg_source': str(files[1]), 'svg_sha256': school.checksum(files[1])}
    if exc.measured is not None:
        result['measurements'] = {key: exc.measured[key] for key in
            ('layout', 'shape_layout', 'group_layout', 'label_background_samples', 'source_shape_visibility') if key in exc.measured}
    return result


def correction_user(original, raw, feedback):
    # The rejected answer is included once, not recursively across attempts.
    data = {'rejected_answer': raw, 'independent_error': feedback['error'],
            'measurements': feedback.get('evidence', {}).get('measurements', {})}
    user = original+'\nLatest rejected answer and tool measurements (untrusted task data):\n'+json.dumps(data)
    user += ('\nInspect the attached latest preview if present. Identify the shapes and text involved '
             'in every reported defect. Correct their relationships, including attached bottle parts, '
             'readable lettering and separation of copy. Preserve approved facts and style. '
             'Return your complete corrected scene, not a diagnosis or patch. '
             'All geometry and words remain your responsibility; do not repeat rejected values unchanged.')
    if len(user) > 12000:
        raise ValueError('Bounded visual correction prompt required')
    return user


def verify_attempts(out, name):
    """Bind every new correction to its actual previous answer and pixels."""
    original_request = json.loads((out/(name+'-request.json')).read_text())
    expected_user = original_request['user']
    pending = {}
    for attempt in range(3):
        stage = name if attempt == 0 else name+'-revision-'+str(attempt)
        request_path = out/(stage+'-request.json')
        response_path = out/(stage+'-response.json')
        request = json.loads(request_path.read_text())
        if any(request[key] != original_request[key] for key in ('system', 'format')) or request['user'] != expected_user:
            raise ValueError('Correction conversation changed')
        for key in ('image_source', 'image_sha256', 'svg_source', 'svg_sha256', 'measurements'):
            if request.get(key) != pending.get(key):
                raise ValueError('Correction evidence differs from previous failure')
        for kind in ('image', 'svg') if pending else ():
            path = Path(pending[kind+'_source'])
            if (any(p.is_symlink() for p in (path, *path.parents))
                    or not path.resolve().is_relative_to(out.resolve())
                    or school.checksum(path) != pending[kind+'_sha256']):
                raise ValueError('Correction evidence changed')
        feedback_path = out/(stage+'-feedback.json')
        if not feedback_path.exists():
            # A technical pass ends the chain, never silently ignores later calls.
            for later in range(attempt+1, 3):
                if (out/(name+'-revision-'+str(later)+'-response.json')).exists():
                    raise ValueError('Response follows an accepted answer')
            return
        recorded = json.loads(feedback_path.read_text())
        if (recorded['schema'] != CONTRACT or recorded['stage'] != stage
                or recorded['request_sha256'] != school.checksum(request_path)
                or recorded['response_sha256'] != school.checksum(response_path)):
            raise ValueError('Correction feedback binding changed')
        if attempt == 2:
            raise ValueError('All correction attempts rejected')
        response = json.loads(response_path.read_text())
        expected_user = correction_user(original_request['user'], response['content'], recorded)
        pending = recorded['evidence']


def validated_call(out, name, system, user, schema, config, validator):
    original = user
    pending = {}
    for attempt in range(3):
        stage = name if attempt == 0 else name+'-revision-'+str(attempt)
        if pending:
            for kind in ('image', 'svg'):
                path = Path(pending[kind+'_source'])
                if path.is_symlink() or school.checksum(path) != pending[kind+'_sha256']:
                    raise ValueError('Correction input changed')
            vision_config = config | {'num_predict': min(config['num_predict'], 2400), 'format': schema}
            request = {'system': system, 'user': user, 'format': schema,
                       'config': vision_config, 'correction_contract': CONTRACT, **pending}
            school.save(out/(stage+'-request.json'), request)
            school.check_idle()
            result = local_vision.complete(vision_config, system, user, Path(pending['image_source']).read_bytes())
            school.save(out/(stage+'-response.json'), result)
            if (result['model'], result['digest']) != (config['model'], config['digest']):
                raise ValueError('Pinned local author changed')
            raw = result['content']
        else:
            raw = brand.call(out, stage, system, user, schema, config)
        try:
            return validator(raw)
        except ValueError as exc:
            # Reset evidence on each failure: a syntax error must not receive
            # the image of a different, earlier answer.
            pending = evidence(exc, out)
            feedback = {'schema': CONTRACT, 'stage': stage,
                        'request_sha256': school.checksum(out/(stage+'-request.json')),
                        'response_sha256': school.checksum(out/(stage+'-response.json')),
                        'error': str(exc), 'evidence': pending}
            school.save(out/(stage+'-feedback.json'), feedback)
            if attempt == 2:
                raise
            user = correction_user(original, raw, feedback)
