import json

from scripts import assess_technical_review_holdout as assessor
from tests.test_technical_review_holdout import content, run_fixture


def test_keyword_stuffing_never_proves_semantics_or_parity(tmp_path, monkeypatch):
    path, _, _, _ = run_fixture(tmp_path, monkeypatch, [content()])
    historical = path/'semantic-assessment.json'
    historical.write_text('Historical evidence is immutable')
    result = assessor.assess(path)
    assert result['proxy_checks_passed'] == result['proxy_checks_total']
    assert result['parity_proven'] is result['accepted'] is result['matched_baseline'] is False
    assert result['semantic_decision'] == 'pending_independent_review'
    assert historical.read_text() == 'Historical evidence is immutable'


def test_assessor_uses_last_validated_answer(tmp_path, monkeypatch):
    path, _, _, _ = run_fixture(tmp_path, monkeypatch, ['{}', '{}', content()])
    result = assessor.assess(path)
    assert result['final_response'] == 'response-2.json'
    assert result['checks']['structurally_valid'] is True


def test_assessor_exposes_unjustified_control_criticism(tmp_path, monkeypatch):
    review = json.loads(content())
    review['comments'].append({'line': 7, 'quote': assessor.ARTICLE.splitlines()[6],
                              'severity': 'major', 'issue': 'invented issue',
                              'recommendation': 'unnecessary correction', 'source_ids': []})
    path, _, _, _ = run_fixture(tmp_path, monkeypatch, [json.dumps(review)])
    result = assessor.assess(path)
    assert result['checks']['correct_controls_not_criticized'] is False
    assert result['accepted'] is False
