import json

import pytest

from scripts import check_qwen_multifile as pilot


def test_default_is_dry_and_never_loads_models(monkeypatch,capsys):
    def forbidden():raise AssertionError('No execution in dry mode')
    monkeypatch.setattr(pilot,'configuration',forbidden)
    monkeypatch.setattr(pilot,'ensure_idle',forbidden)
    assert pilot.main([])==0
    result=json.loads(capsys.readouterr().out)
    assert result['model_invoked'] is False and result['http_checks']==7
    assert len(result['independent_tests_sha256'])==64


def good_result():
    return {'exit_code':0,'cli_exit_code':0,'cleanup_confirmed':True,'reason':None,
            'log':json.dumps({'schema':'example','errors':[],
                'isolation':{k:True for k in pilot.ISOLATION_KEYS}})}


@pytest.mark.parametrize('changes',[{'exit_code':1},{'cli_exit_code':1},
    {'cleanup_confirmed':False},{'reason':'timeout'},{'log':'{}'}])
def test_does_not_count_invalid_execution_as_success(changes):
    with pytest.raises(ValueError):pilot.checked_report(good_result()|changes,'example')


def test_all_isolation_keys_required():
    result=good_result()
    assert pilot.checked_report(result,'example')['errors']==[]
    data=json.loads(result['log']);data['isolation'].pop(next(iter(data['isolation'])))
    with pytest.raises(ValueError):pilot.checked_report(result|{'log':json.dumps(data)},'example')


def test_http_checks_real_response_and_not_truthiness():
    pilot.verify_response({'response':{'status':200,'body':'{"total":0}'}},'/api/quote',200,0)
    for body in ('{"total":false}','{"total":"0"}','{"total":1}'):
        with pytest.raises(ValueError):
            pilot.verify_response({'response':{'status':200,'body':body}},'/api/quote',200,0)
    with pytest.raises(ValueError):
        pilot.verify_response({'response':{'status':200,'body':'{"error":"bad"}'}},'/api/quote',400,None)
    pilot.verify_response({'response':{'status':400,'body':'{"error":"bad"}'}},'/api/quote',400,None)
