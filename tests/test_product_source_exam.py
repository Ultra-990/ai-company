import json

from scripts import product_source_exam as exam


def setup_exam(tmp_path, monkeypatch):
    monkeypatch.setattr(exam.product, 'ROOT', tmp_path)
    monkeypatch.setattr(exam.school, 'check_idle', lambda: {'fixture': True})
    monkeypatch.setattr(exam, 'configuration', lambda: {'model': 'fixture', 'digest': 'f'*64})


def test_paired_exam_freezes_inputs_shares_style_and_restores_training_brief(tmp_path, monkeypatch):
    setup_exam(tmp_path, monkeypatch)
    original = exam.product.BRIEF
    calls = []
    def call(out, stage, system, user, schema, config, validator):
        manifest = json.loads(next(tmp_path.glob('source-exam-*/exam.json')).read_text())
        assert manifest['training_export_allowed'] is False
        assert len(manifest['cases']) == 3
        exam.school.save(out/(stage+'-response.json'), {'content': 'fixture'})
        if stage == 'style':
            return {key: '#123456' for key in ('ink', 'paper', 'accent', 'body_color', 'cap_color')} | {
                'heading_font': 'Arial', 'body_font': 'Arial'}
        calls.append({'family': exam.product.BRIEF['family'], 'split': exam.product.BRIEF['split'],
                      'user': user, 'schema': schema, 'config': config, 'system': system})
        if out.name == 'combined': raise ValueError('fixture failure')
        return 'fixture exact source'
    monkeypatch.setattr(exam.brand, 'validated_call', call)
    out, result = exam.run()
    assert result['status'] == 'completed'
    assert result['scores'] == {'combined': 0, 'focused': 3}
    assert exam.product.BRIEF is original
    for a, b in zip(calls[::2], calls[1::2]):
        assert a['split'] == b['split'] == 'test'
        for key in ('family', 'user', 'schema', 'config'): assert a[key] == b[key]
        assert a['system'] != b['system']
    assert result['exam_sha256'] == exam.school.checksum(out/'exam.json')
    assert not result['training_exported'] and not result['visual_acceptance']


def test_style_failure_still_restores_original_brief_and_saves_report(tmp_path, monkeypatch):
    setup_exam(tmp_path, monkeypatch)
    original = exam.product.BRIEF
    def fail(*args): raise ValueError('fixture style failure')
    monkeypatch.setattr(exam.brand, 'validated_call', fail)
    out, result = exam.run()
    assert result['status'] == 'failed' and result['error'] == 'fixture style failure'
    assert exam.product.BRIEF is original
    assert (out/'report.json').exists()
