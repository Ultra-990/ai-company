import json
import pytest
from scripts import brand_guide_holdout as holdout


@pytest.fixture
def completed(tmp_path, monkeypatch):
    b = holdout.guide.brand
    monkeypatch.setattr(b, 'ROOT', tmp_path)
    monkeypatch.setattr(b.school, 'check_idle', lambda: {})
    monkeypatch.setattr(b, 'configuration', lambda: {'model': 'fixture', 'digest': 'f'*64})
    calls = []
    class Provider:
        def __init__(self, config): pass
        def complete(self, messages):
            case = holdout.CASES[len(calls)]
            payload = json.loads(messages[1]['content'])
            assert payload == holdout.data(case)
            assert 'expected_flags' not in payload and 'reviews' not in payload
            calls.append(payload)
            review = {'reviews': [{'index': i, 'verdict': 'unsupported' if flag else 'supported',
                                  'reason': 'A specific fixture justification.'} for i, flag in enumerate(case[2])]}
            return {'model': 'fixture', 'digest': 'f'*64, 'content': json.dumps(review)}
    monkeypatch.setattr(b, 'OllamaProvider', Provider)
    out, report = holdout.run()
    assert len(calls) == 4
    return out, report


def test_frozen_holdout_recounts_all_sixteen_labels_without_qualification(completed):
    result = holdout.verify(completed[0])
    assert result['correct'] == result['total'] == 16
    assert result['expected_flags_withheld'] and not result['autonomy_qualified']
    assert sum(sum(c[2]) for c in holdout.CASES) == 8


@pytest.mark.parametrize('fault', ['label', 'hint', 'score', 'author'])
def test_holdout_rejects_rebound_changes(completed, fault):
    out, report = completed; b = holdout.guide.brand
    if fault == 'label':
        path = out/'exam.json'; value = json.loads(path.read_text())
        value['cases'][0][2][0] = True; b.school.save(path, value)
        report['exam_sha256'] = b.school.checksum(path)
    elif fault == 'score': report['correct'] = 15
    else:
        suffix = '-request.json' if fault == 'hint' else '-response.json'
        path = out/(holdout.CASES[0][0]+suffix); value = json.loads(path.read_text())
        if fault == 'hint': value['user'] += ' Expected answers: true, false.'
        else: value['model'] = 'replacement'
        b.school.save(path, value)
    report['artifacts'] = {str(p.relative_to(out)): b.school.checksum(p)
        for p in out.rglob('*') if p.is_file() and p.name != 'report.json'}
    b.school.save(out/'report.json', report)
    with pytest.raises(ValueError): holdout.verify(out)
