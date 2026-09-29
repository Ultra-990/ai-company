import json
import re
import pytest
from scripts import brand_spatial_holdout as holdout


@pytest.fixture
def completed(tmp_path, monkeypatch, request):
    b = holdout.spatial.base.legacy.brand
    monkeypatch.setattr(b, 'ROOT', tmp_path)
    monkeypatch.setattr(b.school, 'check_idle', lambda: {})
    monkeypatch.setattr(b, 'configuration', lambda: {'model': 'fixture', 'digest': 'f'*64})
    subjects = getattr(request, 'param', False)
    suite = holdout
    if subjects: from scripts import brand_spatial_subject_holdout as suite
    calls = []
    class Provider:
        def __init__(self, config): pass
        def complete(self, messages):
            _, texts, expected = suite.CASES[len(calls)]
            assert json.loads(messages[1]['content']) == texts
            assert set(texts) == {'a', 'b'}
            calls.append(texts)
            value = {'concepts': [{'id': key, 'claims': [{'relation': relation,
                'quote': '' if relation == 'unspecified' else texts[key]} for relation in expected[key]]} for key in texts]}
            if subjects:
                for row in value['concepts']:
                    for c in row['claims']:
                        noun = '' if c['relation'] == 'unspecified' else re.search(suite.REVIEWER.SYMBOL_NOUN, texts[row['id']], re.I).group(0)
                        c.update(subject='symbol', subject_quote=noun)
            return {'model': 'fixture', 'digest': 'f'*64, 'content': json.dumps(value)}
    monkeypatch.setattr(b, 'OllamaProvider', Provider)
    out, report = holdout.run(subjects=subjects)
    assert len(calls) == 8
    return out, report


def test_language_only_holdout_replays_sixteen_claims_without_qualification(completed):
    result = holdout.verify(completed[0])
    assert result['correct'] == result['total'] == 16
    assert result['geometry_and_labels_withheld'] and not result['autonomy_qualified']


@pytest.mark.parametrize('completed', [True], indirect=True)
def test_subject_holdout_replays_raw_roles_and_code_normalization(completed):
    result = holdout.verify(completed[0])
    assert result['schema'] == 'brand-spatial-subject-holdout.v2'
    assert result['correct'] == result['total'] == 16 and result['geometry_and_labels_withheld']


@pytest.mark.parametrize('fault', ['label', 'geometry', 'score', 'quote'])
def test_spatial_holdout_rejects_rebound_evidence_changes(completed, fault):
    out, report = completed; b = holdout.spatial.base.legacy.brand
    if fault == 'score': report['correct'] = 15
    elif fault == 'label':
        p = out/'exam.json'; value = json.loads(p.read_text()); value['cases'][0][2]['a'] = ['below']
        b.school.save(p, value); report['exam_sha256'] = b.school.checksum(p)
    elif fault == 'geometry':
        p = out/'vertical-request.json'; value = json.loads(p.read_text())
        value['user'] = json.dumps(json.loads(value['user']) | {'actual_geometry': 'symbol above wordmark'})
        b.school.save(p, value)
    else:
        p = out/'vertical-response.json'; value = json.loads(p.read_text()); claims = json.loads(value['content'])
        claims['concepts'][0]['claims'][0]['quote'] = 'Invented text that was not supplied.'
        value['content'] = json.dumps(claims); b.school.save(p, value)
    report['artifacts'] = {str(p.relative_to(out)): b.school.checksum(p) for p in out.rglob('*') if p.is_file() and p.name != 'report.json'}
    b.school.save(out/'report.json', report)
    with pytest.raises(ValueError): holdout.verify(out)
