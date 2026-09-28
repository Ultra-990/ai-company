import json

import pytest

from scripts import product_exam_visual_assessment as visual


def reviewed_package(tmp_path, monkeypatch, decision=visual.APPROVED):
    monkeypatch.setattr(visual.technical.revision, 'ROOT', tmp_path)
    folder = tmp_path/'package'; folder.mkdir()
    files = ['report.json', 'verification.json', 'source/preview.png']+[
        f'delivery/{part}-small.png' for part in visual.PARTS[1:]]
    for name in files:
        path = folder/name; path.parent.mkdir(exist_ok=True)
        path.write_text('fixture '+name)
    checksum = visual.technical.product.school.checksum
    review = {'schema': 'product-infographic-independent-review.v1',
              'reviewer': 'assistant_direct_visual_review', 'decision': decision,
              'report_sha256': checksum(folder/'report.json'),
              'verification_sha256': checksum(folder/'verification.json'),
              'inspected_images': {name: checksum(folder/name) for name in files[2:]},
              'comments': {part: ['Independent observation.'] for part in visual.PARTS},
              'training_exported': False, 'commercial_approved': False,
              'autonomy_qualified': False, 'exam_feedback_used': False}
    (folder/'independent-review.json').write_text(json.dumps(review))
    return folder, review


@pytest.mark.parametrize('decision,accepted', [(visual.APPROVED, True), (visual.REJECTED, False)])
def test_bound_independent_review_preserves_actual_decision(tmp_path, monkeypatch, decision, accepted):
    folder, _ = reviewed_package(tmp_path, monkeypatch, decision)
    assert visual.review_package(folder)['accepted'] is accepted


@pytest.mark.parametrize('fault', ['pixels', 'source_missing', 'report', 'reviewer', 'assisted', 'comments'])
def test_rejects_incomplete_changed_or_assisted_evidence(tmp_path, monkeypatch, fault):
    folder, review = reviewed_package(tmp_path, monkeypatch)
    if fault == 'pixels': (folder/'delivery/care-small.png').write_text('changed')
    elif fault == 'source_missing': del review['inspected_images']['source/preview.png']
    elif fault == 'report': (folder/'report.json').write_text('changed')
    elif fault == 'reviewer': review['reviewer'] = 'local_model_self_review'
    elif fault == 'assisted': review['exam_feedback_used'] = True
    else: del review['comments']['source']
    (folder/'independent-review.json').write_text(json.dumps(review))
    with pytest.raises(ValueError): visual.review_package(folder)


def test_missing_review_cannot_turn_technical_pass_into_acceptance(tmp_path, monkeypatch):
    evidence = {'scores': {'baseline': 0, 'deliberate': 3}, 'exam_report_sha256': 'fixture',
                'cases': [{'case': str(i), 'arm': 'deliberate', 'package': str(tmp_path),
                           'measured_pass': True} for i in range(3)]}
    monkeypatch.setattr(visual.technical, 'assess', lambda path: evidence)
    result = visual.assess(tmp_path)
    assert result['visually_accepted_scores'] == {'baseline': 0, 'deliberate': 0}
    assert not result['reviews_complete'] and not result['autonomy_qualified']


def test_three_visual_acceptances_still_require_autonomous_corrections(tmp_path, monkeypatch):
    evidence = {'scores': {'baseline': 0, 'deliberate': 3}, 'exam_report_sha256': 'fixture',
                'cases': [{'case': str(i), 'arm': 'deliberate', 'package': str(tmp_path),
                           'measured_pass': True} for i in range(3)]}
    monkeypatch.setattr(visual.technical, 'assess', lambda path: evidence)
    monkeypatch.setattr(visual, 'review_package', lambda path: {'accepted': True, 'status': 'accepted'})
    result = visual.assess(tmp_path)
    assert result['all_three_packages_accepted']['deliberate']
    assert result['autonomous_correction_evidence_required'] and not result['autonomy_qualified']
