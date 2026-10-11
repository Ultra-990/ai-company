from hashlib import sha256
import json

import pytest

from scripts import refine_workshop_catalog_routes as refine


def test_feedback_is_app_only_explicit_about_urlparse_params_and_preserves_contract():
    text=refine.DESCRIPTION+" "+refine.EXPECTED
    assert refine.CHANGED_FILES=={"app.py"}
    for value in ("urlparse('/health;extra')","path='/health'","params='extra'",
                  "`';' in parsed.path` jest nieskuteczne","/api/sessions;extra?day=all&level=all",
                  "/health;extra","/;extra","/health;","404","all/all","200/6",
                  "5 plików","harness"):
        assert value in text
    assert len(text.encode())<=360


def test_round2_keeps_round1_pins_and_describes_empty_semicolon_without_patch_code():
    assert refine.ROUND1['source_sha256']==refine.SOURCE_SHA256
    assert refine.ROUND1['routes_sha256']==refine.ROUTES_SHA256
    assert refine.ROUND1['source_package_id']==18
    plan=refine.ROUND2;text=plan['description']+' '+plan['expected']
    assert plan['source_package_id']==25
    assert plan['source_package_checksum']=='b178c7960aa16934c91a2a98825f6895bcf1b5fa036d2e928ad52a6357f77fdb'
    for value in ("urlparse('/health;')","path='/health'","params=''","pełną nierozciętą ścieżkę",
                  '5 probes','/health; =>404','day/level','5 plików+harness'):
        assert value in text
    assert 'self.path' not in text and 'if self.path' not in text


def test_round3_keeps_base_package_and_binds_failed_unchanged_response():
    plan=refine.ROUND3;text=plan['description']+' '+plan['expected']
    assert plan['source_package_id']==refine.ROUND2['source_package_id']==25
    assert plan['source_package_checksum']==refine.ROUND2['source_package_checksum']
    assert plan['source_sha256']==refine.ROUND2['source_sha256']
    assert plan['routes_sha256']==refine.ROUND2['routes_sha256']
    for value in ('Poprzednia odpowiedź=base',"urlparse gubi pusty",
                  'urlsplit zachowuje',"pełnej nierozciętej ścieżki",'5 probes','Zmieniony app.py'):
        assert value in text
    assert len(text.encode())<=430


def test_failed_refinement_proof_requires_no_candidate_test_and_exact_base_app(monkeypatch,tmp_path):
    base={'app.py':'same app'};folder=tmp_path/'route-refinement-2';folder.mkdir()
    evidence=folder/'model-evidence'/'8641bc64be8d4d6ca92919efa6676e80';evidence.mkdir(parents=True)
    response={'content':json.dumps({'changes':{'app.py':'same app'}})}
    response_path=evidence/'repair-response.json';response_path.write_text(json.dumps(response))
    report={'schema':'workshop-catalog-route-refinement.v1','refinement_round':2,'status':'failed',
            'candidate_created':False,'revision':{'inference_id':5,'state':'failed',
            'error_code':'invalid_file_repair','new_package_id':None,'test_run_id':None},
            'inferences':[{'id':5,'state':'failed','error_code':'invalid_file_repair','result_checksum':None,
                           'metrics':{'raw_response_checksum':'raw-checksum'}}]}
    report_path=folder/'report.json';report_path.write_text(json.dumps(report))
    plan=refine.ROUND3|{'failed_report':report_path,
        'failed_report_sha256':sha256(report_path.read_bytes()).hexdigest(),
        'raw_response_sha256':sha256(response_path.read_bytes()).hexdigest(),
        'raw_response_checksum':'raw-checksum'}
    monkeypatch.setattr(refine,'checked',lambda value:value)
    monkeypatch.setattr(refine.route_checks,'load_source',lambda path:(path,'sha',{},base))
    assert refine.failed_refinement_state(plan)==(report_path,plan['failed_report_sha256'])
    report['revision']['new_package_id']=99;report_path.write_text(json.dumps(report))
    plan=plan|{'failed_report_sha256':sha256(report_path.read_bytes()).hexdigest()}
    with pytest.raises(ValueError,match='unchanged app.py response'):
        refine.failed_refinement_state(plan)


def test_scope_requires_only_app_change():
    base={name:name for name in ("app.py","test_app.py","index.html","style.css","app.js","README.md")}
    assert refine.repair_scope(base,base|{"app.py":"fixed"})
    assert not refine.repair_scope(base,base)
    assert not refine.repair_scope(base,base|{"app.py":"fixed","app.js":"changed"})


def test_pinned_failed_route_evidence_validates_four_raw_runs(monkeypatch,tmp_path):
    expected={
        '/api/sessions?day=all&level=all':(200,200,True),
        '/api/sessions;extra?day=all&level=all':(404,200,False),
        '/health;extra':(404,200,False),
        '/;extra':(404,200,False),
    }
    probes=[]
    for path,(wanted,seen,passed) in expected.items():
        probes.append({'path':path,'expected_status':wanted,'observed_status':seen,'passed':passed,
            'raw_run':{'exit_code':0,'cli_exit_code':0,'cleanup_confirmed':True,'reason':None,
                       'log':json.dumps({'schema':'python-web-preview.v1',
                                         'response':{'status':seen,'body':'fixture'}})}})
    data={'schema':'workshop-catalog-routes-check.v1','status':'failed',
          'source_report_sha256':refine.SOURCE_SHA256,'source_unchanged':True,
          'source_sha256':{'app.py':refine.SOURCE_APP_SHA256},'probes':probes}
    path=tmp_path/'routes.json';path.write_text(json.dumps(data));digest=sha256(path.read_bytes()).hexdigest()
    monkeypatch.setattr(refine,'checked',lambda value:value)
    plan=refine.ROUND1|{'routes':path,'routes_sha256':digest}
    assert refine.evidence_state(plan)==(path,digest)
    data['probes'][1]['raw_run']['cleanup_confirmed']=False;path.write_text(json.dumps(data))
    plan=plan|{'routes_sha256':sha256(path.read_bytes()).hexdigest()}
    with pytest.raises(ValueError,match='invalid probe run'):
        refine.evidence_state(plan)


def test_dry_run_uses_pinned_package_without_model_or_container(monkeypatch,capsys):
    monkeypatch.setattr('sys.argv',['refine_workshop_catalog_routes.py'])
    monkeypatch.setattr(refine,'check_idle',lambda:pytest.fail('unexpected runtime call'))
    assert refine.main()==0
    result=json.loads(capsys.readouterr().out)
    assert result['model_invoked'] is False
    assert result['source_package_id']==18
    assert result['source_package_checksum']==refine.PACKAGE_CHECKSUM
    assert result['requested_change']==['app.py']


def test_browser_registry_reuses_workshop_contract_for_refinement():
    from scripts import check_business_website_browser as browser
    assert browser.SCENARIOS['workshop-catalog-route-refinement.v1'] is browser.SCENARIOS['workshop-catalog-delivery.v1']
