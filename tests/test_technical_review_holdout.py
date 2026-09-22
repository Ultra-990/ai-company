import json
from scripts import technical_review_holdout as holdout


def test_holdout_expectations_are_not_in_model_request():
    request = json.dumps({'article': holdout.ARTICLE, 'sources': holdout.SOURCES})
    assert 'EXPECTED' not in request and str(sorted(holdout.EXPECTED)) not in request
    assert 'EDITORIAL TRAP' in request


def test_holdout_has_distinct_reserved_family_and_correct_line_contract():
    assert holdout.ARTICLE.splitlines()[2].startswith('Because')
    assert holdout.EXPECTED == {3, 4, 5, 6}
    assert holdout.CONTROLS == {2, 7}


def test_correction_protocol_is_bounded_and_keeps_first_answer():
    import inspect
    source = inspect.getsource(holdout.run)
    assert 'Two bounded structural corrections' in source
    assert 'structural-feedback-{attempt}.json' in source and 'correction-response-{attempt}.json' in source
