from copy import deepcopy

import pytest

from scripts import product_source_lesson as lesson


def example(tmp_path, monkeypatch):
    monkeypatch.setattr(lesson.revision, 'ROOT', tmp_path)
    folder = tmp_path/'assembly'; folder.mkdir()
    original = tmp_path/'original'; original.mkdir()
    save = lesson.product.school.save; checksum = lesson.product.school.checksum
    save(original/'report.json', {'brief': deepcopy(lesson.product.DEFAULT_BRIEF)})
    save(folder/'report.json', {'original_package': str(original)})
    save(folder/'verification.json', {'fixture': True})
    images = {}
    for part in lesson.product.DEFAULT_PANELS:
        path = folder/part/'small/preview.png'; path.parent.mkdir(parents=True); path.write_bytes(b'fixture')
        images[part+'/small/preview.png'] = checksum(path)
    judgment = {'schema': 'product-reviewed-assembly-independent-review.v1',
        'reviewer': 'assistant_direct_visual_review', 'decision': 'approved_synthetic_development_package',
        'report_sha256': checksum(folder/'report.json'), 'verification_sha256': checksum(folder/'verification.json'),
        'inspected_images': images}
    save(folder/'independent-review.json', judgment)
    return folder, original, judgment


@pytest.mark.parametrize('split', ['validation', 'test'])
def test_reserved_family_cannot_become_a_lesson_even_with_a_positive_review(tmp_path, monkeypatch, split):
    folder, original, _ = example(tmp_path, monkeypatch)
    brief = deepcopy(lesson.product.DEFAULT_BRIEF); brief['split'] = split
    lesson.product.school.save(original/'report.json', {'brief': brief})
    with pytest.raises(ValueError, match='development family'): lesson.load(folder)


def test_self_review_and_changed_preview_are_rejected(tmp_path, monkeypatch):
    folder, _, judgment = example(tmp_path, monkeypatch)
    judgment['reviewer'] = 'local_model_self_review'
    lesson.product.school.save(folder/'independent-review.json', judgment)
    with pytest.raises(ValueError, match='independently approved'): lesson.load(folder)
    judgment['reviewer'] = 'assistant_direct_visual_review'
    lesson.product.school.save(folder/'independent-review.json', judgment)
    (folder/'care/small/preview.png').write_bytes(b'changed')
    with pytest.raises(ValueError, match='no longer matches'): lesson.load(folder)


def test_failed_example_verification_restores_the_active_brief(tmp_path, monkeypatch):
    folder, _, _ = example(tmp_path, monkeypatch)
    active_brief, active_panels = {'active': 'heldout'}, {'active': 'facts'}
    monkeypatch.setattr(lesson.product, 'BRIEF', active_brief)
    monkeypatch.setattr(lesson.product, 'PANELS', active_panels)
    def reject(path):
        assert lesson.product.BRIEF == lesson.product.DEFAULT_BRIEF
        raise ValueError('Original model evidence changed')
    monkeypatch.setattr(lesson.assembly, 'verify', reject)
    with pytest.raises(ValueError, match='model evidence'): lesson.load(folder)
    assert lesson.product.BRIEF is active_brief and lesson.product.PANELS is active_panels


@pytest.mark.parametrize('fault', [None, 'lesson', 'request', 'brief', 'style', 'author', 'inherited'])
def test_package_binds_reviewed_example_without_replacing_active_task(tmp_path, monkeypatch, fault):
    import json
    monkeypatch.setattr(lesson.revision, 'ROOT', tmp_path)
    value = {'contract': lesson.CONTRACT, 'split': 'train', 'assembly': str(tmp_path/'assembly'),
             'model': 'fixture', 'digest': 'f'*64, 'example': {'scene': 'local example'}}
    monkeypatch.setattr(lesson, 'load', lambda path: deepcopy(value))
    monkeypatch.setattr(lesson.product, 'accepted_raw', lambda *args: '{}')
    monkeypatch.setattr(lesson.product, 'style_value', lambda raw: {'ink': 'active'})
    task = {'brief': {'family': 'new test case'}, 'style': {'ink': 'active'}, 'task': 'Draw the new product'}
    saved = deepcopy(value)
    report = {'source_lesson_contract': lesson.CONTRACT, 'model': 'fixture', 'digest': 'f'*64, 'brief': deepcopy(task['brief'])}
    if fault == 'lesson': saved['example']['scene'] = 'manually changed'
    if fault == 'brief': task['brief'] = {'family': 'example instead of task'}
    if fault == 'style': task['style'] = {'ink': 'wrong'}
    if fault == 'author': report['model'] = 'different'
    if fault == 'inherited': report['inherited_stages'] = ['source']
    user = lesson.message(value)+'\nCURRENT TASK (use these facts and style):\n'+json.dumps(task)
    if fault == 'request': user = 'Different context'
    lesson.product.school.save(tmp_path/'source-lesson.json', saved)
    lesson.product.school.save(tmp_path/'source-request.json', {'user': user})
    report['artifacts'] = {p.name: lesson.product.school.checksum(p) for p in tmp_path.iterdir()}
    if fault:
        with pytest.raises(ValueError): lesson.verify_binding(tmp_path, report)
    else:
        assert lesson.verify_binding(tmp_path, report)['source_lesson_verified']


def test_lesson_continuation_is_rejected_before_resource_or_model_calls(tmp_path, monkeypatch):
    def unexpected(): raise AssertionError('No resource operation is needed')
    monkeypatch.setattr(lesson.product.school, 'check_idle', unexpected)
    for mode in ('resume', 'recompose'):
        with pytest.raises(ValueError, match='fresh package'):
            lesson.product.run(**{mode: tmp_path}, source_lesson=tmp_path)
