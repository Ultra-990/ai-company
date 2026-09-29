from copy import deepcopy
import json

import pytest

from scripts import product_headline_probe as probe


@pytest.mark.parametrize('fault', [None, 'missing', 'duplicate', 'foreign_fact', 'invented_fact', 'extra_field', 'bad_verdict'])
def test_probe_requires_complete_reviews_and_literal_evidence_but_never_asserts_semantic_truth(fault):
    data = {'panels': [{'panel': panel, 'supplier_facts': facts} for panel, facts in probe.product.DEFAULT_PANELS.items()]}
    value = {'reviews': [{'panel': row['panel'], 'verdict': 'uncertain', 'reason': 'A model verdict still requires independent review.',
                         'evidence': [row['supplier_facts'][0]]} for row in data['panels']]}
    if fault == 'missing': value['reviews'].pop()
    elif fault == 'duplicate': value['reviews'][1] = deepcopy(value['reviews'][0])
    elif fault == 'foreign_fact': value['reviews'][0]['evidence'] = data['panels'][1]['supplier_facts']
    elif fault == 'invented_fact': value['reviews'][0]['evidence'] = ['A newly invented guarantee']
    elif fault == 'extra_field': value['reviews'][0]['approved_for_delivery'] = True
    elif fault == 'bad_verdict': value['reviews'][0]['verdict'] = 'commercially_approved'
    if fault:
        with pytest.raises(ValueError): probe.validate(json.dumps(value), data)
    else:
        assert probe.validate(json.dumps(value), data) == value


def test_probe_reads_literal_headlines_without_human_review_or_expected_verdict(tmp_path, monkeypatch):
    p = probe.product
    report = {'brief': deepcopy(p.DEFAULT_BRIEF), 'supplier_copy': deepcopy(p.DEFAULT_PANELS)}
    monkeypatch.setattr(probe.revision, 'read', lambda path: report if path.name == 'report.json' else pytest.fail('Human review must not be read'))
    monkeypatch.setattr(p, 'verify', lambda path: {})
    monkeypatch.setattr(p, 'accepted_raw', lambda folder, panel: json.dumps({'texts': [{'text': 'Literal local '+panel}]}))
    _, data = probe.inputs(tmp_path)
    assert [row['headline'] for row in data['panels']] == ['Literal local '+panel for panel in p.DEFAULT_PANELS]
    assert set(data) == {'product_name', 'unknown', 'panels'}
    assert all(set(row) == {'panel', 'headline', 'supplier_facts'} for row in data['panels'])
