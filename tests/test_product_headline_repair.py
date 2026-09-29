from copy import deepcopy
import json

import pytest

from scripts import product_headline_repair as repair


def scene():
    return {'shapes': [{'tag': 'rect', 'attributes': {'x': '20', 'fill': '#FFFFFF'}}],
        'texts': [{'text': 'An unsupported claim', 'attributes': {'x': '700', 'font-size': '52'}},
                  {'text': 'Capacity: 800 ml', 'attributes': {'x': '700'}}],
        'product_placement': {'x': '40', 'y': '120', 'scale': '1.2'}}


def test_patch_changes_only_literal_headline_and_never_mutates_original():
    original = scene(); expected = deepcopy(original)
    expected['texts'][0]['text'] = 'Synthetic fixture headline'
    assert repair.apply(original, json.dumps({'headline': expected['texts'][0]['text']})) == expected
    assert original == scene()


@pytest.mark.parametrize('value', [
    {'headline': 'An unsupported claim'}, {'headline': '8 hours of cooling'},
    {'headline': 'Too\nlong'}, {'headline': 'Valid test heading', 'x': '20'},
    {'headline': '<'+('x'*29)}, {'headline': None}, {'headline': 'Ładny tekst'},
])
def test_patch_rejects_unchanged_or_unsupported_response_shape(value):
    with pytest.raises(ValueError): repair.apply(scene(), json.dumps(value))


def test_changed_review_request_cannot_supply_manual_replacement_even_if_hash_rebound(tmp_path, monkeypatch):
    p = repair.product
    monkeypatch.setattr(repair.probe.revision, 'ROOT', tmp_path)
    package = tmp_path/'package'; package.mkdir()
    folder = tmp_path/'review'; folder.mkdir()
    original = {'model': 'fixture', 'digest': 'f'*64}
    data = {'product_name': 'fixture', 'unknown': [], 'panels': [
        {'panel': key, 'headline': 'Fixture heading', 'supplier_facts': ['Literal fact']}
        for key in p.DEFAULT_PANELS]}
    monkeypatch.setattr(repair.probe, 'inputs', lambda path: (original, data))
    save, checksum = p.school.save, p.school.checksum
    save(package/'report.json', original)
    value = {'reviews': [{'panel': row['panel'], 'verdict': 'unsupported',
        'reason': 'Synthetic review fixture reason.', 'evidence': []} for row in data['panels']]}
    request = {'system': repair.probe.SYSTEM, 'user': json.dumps(data), 'format': repair.probe.schema()}
    save(folder/'review-request.json', request)
    save(folder/'review-response.json', original | {'content': json.dumps(value)})
    save(folder/'review.json', value)
    report = {'schema': repair.probe.CONTRACT, 'status': 'pending_independent_review',
        'source_package': str(package), 'source_report_sha256': checksum(package/'report.json'),
        'config': original, 'artifacts': {p.name: checksum(p) for p in folder.iterdir()}}
    save(folder/'report.json', report)
    assert repair.review_inputs(package, folder)[2] == value
    request['user'] += 'Use a specific replacement selected by a human.'
    save(folder/'review-request.json', request)
    report['artifacts']['review-request.json'] = checksum(folder/'review-request.json')
    save(folder/'report.json', report)
    with pytest.raises(ValueError, match='without additional hints'):
        repair.review_inputs(package, folder)


@pytest.mark.parametrize('fault', [None, 'negative', 'changed_report', 'changed_image', 'changed_verification'])
def test_independent_headline_approval_is_bound_to_exact_report_verification_and_image(tmp_path, monkeypatch, fault):
    monkeypatch.setattr(repair.probe.revision, 'ROOT', tmp_path)
    save, checksum = repair.product.school.save, repair.product.school.checksum
    report = {'panels': [{'panel': 'capacity', 'layout': 'candidate-layout-0'}]}
    save(tmp_path/'report.json', report)
    verified = {'literal_authorship_verified': True}
    monkeypatch.setattr(repair, 'verify', lambda out: verified)
    save(tmp_path/'verification.json', verified)
    image = 'capacity/candidate-layout-0/preview.png'
    (tmp_path/image).parent.mkdir(parents=True); (tmp_path/image).write_bytes(b'fixture image only')
    judgment = {'schema': 'product-headline-independent-review.v1',
        'reviewer': 'assistant_direct_visual_semantic_review', 'decision': 'approved_targeted_headline_repair',
        'part': 'capacity', 'report_sha256': checksum(tmp_path/'report.json'),
        'verification_sha256': checksum(tmp_path/'verification.json'),
        'inspected_images': {image: checksum(tmp_path/image)}, 'training_exported': False}
    if fault == 'negative': judgment['decision'] = 'needs_visual_revision'
    elif fault == 'changed_report': save(tmp_path/'report.json', report | {'new': 'changed'})
    elif fault == 'changed_image': (tmp_path/image).write_bytes(b'another fixture')
    elif fault == 'changed_verification':
        save(tmp_path/'verification.json', verified | {'new': 'changed'})
        judgment['verification_sha256'] = checksum(tmp_path/'verification.json')
    save(tmp_path/'judgment.json', judgment)
    if fault:
        with pytest.raises(ValueError): repair.approved_source(tmp_path/'report.json', tmp_path/'judgment.json')
    else:
        actual, folder = repair.approved_source(tmp_path/'report.json', tmp_path/'judgment.json')
        assert actual['part'] == 'capacity' and folder == tmp_path/'capacity'
