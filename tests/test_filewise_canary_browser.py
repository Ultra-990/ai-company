import json
import os
from pathlib import Path

import pytest

from scripts import check_filewise_canary_browser as browser


def synthetic_sources():
    return {'app.py':"keep_blank_values=True\n'/api/count'\n'/health'\n'/style.css'\n'/app.js'\nisalpha()",
        'test_app.py':"ThreadingHTTPServer(('127.0.0.1', 0), app.H)\n"+
            ''.join(f'    def test_{n}(self): pass\n' for n in range(7)),
        'index.html':'<!doctype html><label for="text">T</label><input id="text"><button id="calculate"></button><p id="result" aria-live="polite">file://</p>',
        'style.css':'body{display:block}',
        'app.js':'encodeURIComponent(text); result.textContent="x";',
        'README.md':'file://; brak zapisu i usług zewnętrznych'}


def synthetic_report():
    harness={'tests_ok':True,'http_ok':True,'source_not_exposed':True,'errors':[]}
    run={'cleanup_confirmed':True,'exit_code':0,'cli_exit_code':0,'reason':None,
        'profile':{'harness_checksum':browser.HARNESS_SHA256},'log':json.dumps(harness)}
    return {'schema':browser.SOURCE_SCHEMA,'state':'awaiting_review','owner_accepted':False,
        'candidate_created':False,'deployed':False,'isolated_test':{'run_id':2,'state':'passed'},
        'source':{'harness_sha256':browser.HARNESS_SHA256},
        'revision':{'new_package_id':browser.PACKAGE_ID,
            'new_package_checksum':browser.PACKAGE_CHECKSUM,'test_state':'passed','accepted':False},
        'tests':[{'id':2,'state':'passed','package_id':browser.PACKAGE_ID,'result':run}],
        'new_sources':synthetic_sources()}


def test_synthetic_gate_accepts_contract_shape_without_claiming_model_evidence():
    files=browser.checked_sources(synthetic_report());review=browser.source_assessment(files)
    assert review['six_files'] and review['real_http_server_tests']
    assert review['test_methods']==7 and review['none_handler_constructor'] is False
    assert review['api_contract'] and review['ui_contract']


def test_report_gate_rejects_wrong_state_provenance_or_invalid_sources():
    good=synthetic_report()
    for damaged in (good|{'schema':'wrong'},good|{'state':'accepted'},good|{'new_sources':{}},
        good|{'owner_accepted':True},good|{'isolated_test':{'run_id':2,'state':'failed'}},
        good|{'revision':good['revision']|{'new_package_checksum':'0'*64}},
        good|{'source':{'harness_sha256':'0'*64}},good|{'tests':[good['tests'][0]|{'state':'failed'}]}):
        with pytest.raises(ValueError):browser.checked_sources(damaged)
    with pytest.raises(ValueError):browser.checked_sources(good,'0'*64)


def test_source_assessment_records_sizes_without_turning_fixture_into_evidence():
    files=browser.checked_sources(synthetic_report());review=browser.source_assessment(files)
    assert review['characters']=={name:len(value) for name,value in files.items()}
    assert review['bytes']=={name:len(value.encode()) for name,value in files.items()}


def test_matching_response_requires_one_exact_query_and_semantic_http_json():
    def item(path,status=200,body={'letters':6}):
        return {'path':path,'run':{'log':json.dumps({'response':{
            'status':status,'body':json.dumps(body)}})}}
    valid=item('/api/count?text=Za%C5%BC%C3%B3%C5%82%C4%87%20123!')
    assert browser.matching_count_response([valid],0,'Zażółć 123!',6) is True
    assert browser.matching_count_response([valid,valid],0,'Zażółć 123!',6) is False
    assert browser.matching_count_response([item('/api/count?text=Za%C5%BC%C3%B3%C5%82%C4%87%20123!',body={'letters':7})],0,'Zażółć 123!',6) is False
    assert browser.matching_count_response([item('/api/count?text=123-!',body={'letters':0})],0,'123-!',0) is True


def test_visible_warning_requires_rendered_positive_box_and_both_messages():
    import subprocess
    script="""
    function run(text,display='block',visibility='visible',width=100,height=20){
      global.document={querySelector:()=>({innerText:text,getBoundingClientRect:()=>({width,height})})};
      global.getComputedStyle=()=>({display,visibility});return EXPR;
    }
    process.stdout.write(JSON.stringify([run('file:// zewnętrznych'),run('file://'),
      run('file:// zewnętrznych','none'),run('file:// zewnętrznych','block','hidden'),
      run('file:// zewnętrznych','block','visible',0,20)]));
    """.replace('EXPR',browser.VISIBLE_WARNING)
    result=subprocess.run(['node','-'],input=script,text=True,capture_output=True,check=True,timeout=5)
    assert json.loads(result.stdout)==[True,False,False,False,False]


def test_timeout_is_persistable_incomplete_state():
    report={'status':'running'};browser.mark_timeout(report)
    assert report=={'status':'incomplete','error_type':'TimeoutError','error':'bounded_browser_timeout'}


@pytest.mark.skipif(not os.environ.get('AIC_FILEWISE_CANARY_REVIEW_REPORT'),
    reason='Real immutable canary evidence requires an explicit local report path')
def test_real_canary_evidence_matches_pinned_review_without_executing_sources():
    source=Path(os.environ['AIC_FILEWISE_CANARY_REVIEW_REPORT'])
    raw=source.read_bytes();report=json.loads(raw);files=browser.checked_sources(
        report,browser.sha256(raw).hexdigest())
    review=browser.source_assessment(files)
    assert review['six_files'] and review['real_http_server_tests']
    assert review['test_methods']==7 and review['none_handler_constructor'] is False
    assert review['api_contract'] and review['ui_contract']
