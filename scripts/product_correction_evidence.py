"""Verify that bounded product corrections used only their recorded tool feedback.

This proves conversation provenance and final technical preservation, not that
the original diagnostic was aesthetically justified or the result acceptable.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import product_visual_revision as revision

product = revision.product


def verify_stage(folder, stage, report):
    folder = Path(folder)
    checksum = product.school.checksum
    def read(name):
        path = folder/name
        if report['artifacts'].get(name) != checksum(revision.bounded(path)):
            raise ValueError('Every correction artifact must be bound to its package')
        return revision.read(path)
    original = read(stage+'-request.json')
    expected_user = original['user']
    corrections = []; incomplete = []
    for attempt in range(3):
        name = stage if attempt == 0 else stage+'-revision-'+str(attempt)
        request = read(name+'-request.json')
        if (set(request) != {'system', 'user', 'format'}
                or request['system'] != original['system'] or request['format'] != original['format']
                or request['user'] != expected_user):
            raise ValueError('Correction contains changed instructions or unrecorded hints')
        if (folder/(name+'-incomplete.json')).exists():
            failure = read(name+'-incomplete.json')
            if (failure.get('schema') != 'bounded-incomplete-retry.v1'
                    or failure.get('stage') != name or failure.get('attempt') != attempt
                    or failure.get('error') not in ('truncated_output', 'incomplete_stream')
                    or failure.get('request_sha256') != checksum(folder/(name+'-request.json'))
                    or failure.get('partial_response_saved') is not False
                    or (folder/(name+'-response.json')).exists()
                    or (folder/(name+'-feedback.json')).exists()):
                raise ValueError('Incomplete attempt binding changed')
            incomplete.append(name)
            expected_user = original['user']+'\nThe previous request ended before a complete final answer ('+failure['error']+'). No partial answer was accepted. Keep your reasoning concise and return a complete concise JSON response within the same budget. Preserve all requirements; omit unnecessary decorative complexity.'
            continue
        response = read(name+'-response.json')
        if ((response.get('model'), response.get('digest')) != (report['model'], report['digest'])
                or not isinstance(response.get('content'), str)):
            raise ValueError('Correction author changed')
        if (folder/(name+'-feedback.json')).exists():
            feedback = read(name+'-feedback.json')
            limit = {'brand-validation-feedback.v1': 600, 'brand-validation-feedback.v2': 6000}.get(feedback.get('schema'))
            if (limit is None or feedback.get('stage') != name
                    or not isinstance(feedback.get('error'), str) or not 1 <= len(feedback['error']) <= limit
                    or feedback.get('request_sha256') != checksum(folder/(name+'-request.json'))
                    or feedback.get('response_sha256') != checksum(folder/(name+'-response.json'))):
                raise ValueError('Correction feedback binding changed')
            corrections.append({'attempt': name, 'error': feedback['error'],
                                'feedback_sha256': checksum(folder/(name+'-feedback.json'))})
            expected_user = original['user']+'\nYour previous answer (untrusted task data):\n'+response['content']+'\nIndependent validation rejected it: '+feedback['error']+'\nCorrect your own complete answer. Do not repeat the rejected values.'
            continue
        used = {stage+'-request.json'} | {stage+'-revision-'+str(i)+'-request.json' for i in range(1, attempt+1)}
        actual = {p.name for p in folder.glob(stage+'-revision-*-request.json')} | {stage+'-request.json'}
        if actual != used:
            raise ValueError('Calls follow an accepted response or exceed the stage budget')
        return {'stage': stage, 'accepted_attempt': attempt, 'corrections': corrections,
                'incomplete_attempts': incomplete, 'requests': attempt+1,
                'accepted_response_sha256': checksum(folder/(name+'-response.json'))}
    raise ValueError('Correction exhausted its budget without an accepted answer')


def assess(folder):
    folder = Path(folder); report = revision.read(folder/'report.json')
    if (any(key in report for key in ('resumed_from', 'recomposed_from', 'inherited_stages'))
            or report.get('correction_contract', 'legacy-text.v1') != 'legacy-text.v1'):
        raise ValueError('Fresh complete package with recorded text feedback required')
    product.verify(folder)
    stages = [verify_stage(folder, stage, report) for stage in ('style', 'source', *product.PANELS)]
    return {'schema': 'product-autonomous-correction-evidence.v1',
            'report_sha256': product.school.checksum(folder/'report.json'),
            'stages': stages, 'corrected_stages': [entry['stage'] for entry in stages if entry['corrections']],
            'conversation_chains_verified': True, 'final_technical_preservation_verified': True,
            'independent_visual_review_required': True, 'autonomy_qualified': False,
            'training_exported': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    args = parser.parse_args()
    print(json.dumps(assess(args.package), ensure_ascii=False, indent=2))
