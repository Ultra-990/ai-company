import json
import pytest
from scripts.check_model_quality import check


def test_question_check_accepts_polish_currency_inflection():
    check('questions',json.dumps({'questions':['W jakiej walucie będzie płatność?','Jaki czas realizacji?']}))


@pytest.mark.parametrize('questions',[
    ['Jaka waluta?']*7,
    ['Jaka waluta?','Jaka waluta?'],
    ['Czy przyjąć 23% podatku i walutę PLN?'],
    ['Jaka waluta']])
def test_question_check_rejects_bad_results(questions):
    with pytest.raises(AssertionError):check('questions',json.dumps({'questions':questions}))


def test_calculation_check_checks_actual_value_and_unknown_tax():
    check('calculation',json.dumps({'subtotal':2576,'tax_rate':None,'missing':['waluta']}))
    for total,tax in [(2577,None),(2576,.23)]:
        with pytest.raises(AssertionError):
            check('calculation',json.dumps({'subtotal':total,'tax_rate':tax,'missing':['waluta']}))
