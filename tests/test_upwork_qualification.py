import pytest

from scripts.upwork_qualification import SERVICES, empty_evidence, evaluate


def test_empty_matrix_never_claims_parity():
    report = evaluate(empty_evidence(), checked_on='2026-09-24')
    assert report['qualified_count'] == 0
    assert report['all_five_qualified'] is False
    assert report['parity_claim_allowed'] is False
    assert all(item['missing'] for item in report['services'].values())


def test_only_complete_service_evidence_qualifies():
    evidence = empty_evidence()
    service = next(iter(SERVICES))
    for key in evidence[service]:
        evidence[service][key] = True
    report = evaluate(evidence, checked_on='2026-09-24')
    assert report['qualified_services'] == [service]
    assert report['services'][service]['parity_proven'] is True
    assert report['parity_claim_allowed'] is False


def test_matrix_rejects_missing_or_non_boolean_fields():
    with pytest.raises(ValueError):
        evaluate({})
    evidence = empty_evidence()
    evidence['vector_flyer']['svg_contract'] = 'passed'
    with pytest.raises(ValueError):
        evaluate(evidence)
