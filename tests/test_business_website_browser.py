import json
import pytest
from scripts import check_business_website_browser as browser
from scripts.service_quote_transfer_case import PROBES as FROZEN_TRANSFER_PROBES
from scripts.workshop_catalog_case import PROBES as FROZEN_WORKSHOP_PROBES


def test_scenario_selection_preserves_business_and_adds_fresh_transfer_quotes():
    business = browser.scenario_for({'schema': 'business-website-delivery.v1'})
    transfer = browser.scenario_for({'schema': 'service-quote-transfer-delivery.v1'})
    assert business['api_path'] == '/api/estimate'
    assert business['field_ids'] == ('service', 'bikes', 'express')
    assert business['quotes'] == (('basic', '1', False, 90), ('full', '3', True, 690),
                                  ('basic', '8', True, 1120))
    assert transfer['api_path'] == '/api/quote'
    assert transfer['field_ids'] == ('plan', 'machines', 'onsite')
    assert transfer['faq_id'] == 'faq-process' and transfer['file_mode'] is True
    frozen_paths = {path for path, _, _ in FROZEN_TRANSFER_PROBES}
    for plan, machines, onsite, total in transfer['quotes']:
        path = f'/api/quote?plan={plan}&machines={machines}&onsite={int(onsite)}'
        assert path not in frozen_paths
        assert total == {'check': 85, 'restore': 235}[plan] * int(machines) + (70 if onsite else 0)


def test_transfer_revision_uses_same_crema_contract_and_generic_boolean_interaction():
    delivery = browser.scenario_for({'schema': 'service-quote-transfer-delivery.v1'})
    revision = browser.scenario_for({'schema': 'service-quote-transfer-revision.v1'})
    assert revision is delivery
    assert browser.scenario_for({'schema': 'service-quote-transfer-ui-repair.v1'}) is delivery
    selected = browser.quote_interaction(revision, 'restore', '4', True)
    cleared = browser.quote_interaction(revision, 'check', '2', False)
    assert "flag.type==='checkbox'" in selected
    assert 'flag.checked=true' in selected and 'flag.value="1"' in selected
    assert 'flag.checked=false' in cleared and 'flag.value="0"' in cleared
    assert 'getElementById("onsite")' in selected


def test_workshop_scenario_uses_fresh_filters_and_public_dom_contract():
    selected=browser.scenario_for({'schema':'workshop-catalog-delivery.v1'})
    assert browser.scenario_for({'schema':'workshop-catalog-ui-repair.v1'}) is selected
    assert selected['api_path']=='/api/sessions'
    assert selected['field_ids']==('day','level')
    assert selected['action_id']=='apply-filters'
    assert selected['output_ids']==('sessions','filter-status')
    assert selected['faq_id']=='faq-filtering' and selected['file_mode'] is True
    frozen={path for path,_,_ in FROZEN_WORKSHOP_PROBES}
    expected={('tuesday','beginner'):('Błękitna cyjanotypia',),
              ('saturday','advanced'):('Mały drzeworyt',),('tuesday','intermediate'):()}
    actual={(day,level):tuple(row['title'] for row in sessions)
            for day,level,sessions in selected['filters']}
    assert actual==expected
    for day,level,_ in selected['filters']:
        assert f'/api/sessions?day={day}&level={level}' not in frozen
    expression=browser.filter_interaction(selected,'tuesday','beginner')
    assert 'getElementById("day").value="tuesday"' in expression
    assert 'getElementById("level").value="beginner"' in expression
    assert 'getElementById("apply-filters").click()' in expression


def test_filter_expectation_executes_for_list_empty_state_and_rejects_stale_ui():
    import subprocess
    selected=browser.scenario_for({'schema':'workshop-catalog-delivery.v1'})
    one=selected['filters'][0][2]
    expressions=[browser.filter_expectation(one,selected['all_titles']),
                 browser.filter_expectation((),selected['all_titles'])]
    script="""
    const expressions=EXPRESSIONS;
    function run(expression,text,status){
      global.document={getElementById:id=>id==='sessions'?{innerText:text}:{innerText:status}};
      return eval(expression);
    }
    process.stdout.write(JSON.stringify([
      run(expressions[0],'Błękitna cyjanotypia','Znaleziono zajęcia'),
      run(expressions[1],'Brak pasujących zajęć','Brak wyników'),
      run(expressions[0],'Błękitna cyjanotypia Mały drzeworyt','Znaleziono zajęcia'),
      run(expressions[1],'Brak pasujących zajęć','')
    ]));
    """.replace('EXPRESSIONS',json.dumps(expressions,ensure_ascii=False))
    result=subprocess.run(['node','-'],input=script,text=True,capture_output=True,check=True,timeout=5)
    assert json.loads(result.stdout)==[True,True,False,False]


def test_file_warning_requires_visible_nonempty_startup_explanation():
    import subprocess
    script = """
    function run(text, display='block', visibility='visible', width=300, height=24) {
        global.document={getElementById:()=>({innerText:text,
            getBoundingClientRect:()=>({width,height})})};
        global.getComputedStyle=()=>({display,visibility});
        return EXPRESSION;
    }
    process.stdout.write(JSON.stringify([
        run('Uruchom python app.py'),run(''),run('Błąd'),
        run('python app.py','none'),run('python app.py','block','hidden'),
        run('python app.py','block','visible',0)
    ]));
    """.replace('EXPRESSION', browser.RUNTIME_NOTE_VISIBLE)
    result=subprocess.run(['node','-'],input=script,text=True,capture_output=True,check=True,timeout=5)
    assert json.loads(result.stdout)==[True,False,False,False,False,False]


def test_filter_response_accepts_query_order_and_exact_body_but_rejects_duplicates():
    selected=browser.scenario_for({'schema':'workshop-catalog-delivery.v1'})
    expected=selected['filters'][0][2]
    def request(path,sessions=expected,status=200):
        response={'status':status,'body':json.dumps({'sessions':list(sessions)},ensure_ascii=False)}
        return {'path':path,'run':{'log':json.dumps({'response':response},ensure_ascii=False)}}
    unrelated=request('/api/sessions?day=all&level=all',())
    reversed_order=request('/api/sessions?level=beginner&day=tuesday')
    assert browser.matching_filter_response([unrelated,reversed_order],0,selected,
        'tuesday','beginner',expected) is True
    duplicate=request('/api/sessions?day=tuesday&day=tuesday&level=beginner')
    wrong=request('/api/sessions?day=tuesday&level=beginner',())
    assert browser.matching_filter_response([duplicate],0,selected,'tuesday','beginner',expected) is False
    assert browser.matching_filter_response([wrong],0,selected,'tuesday','beginner',expected) is False
    assert browser.matching_filter_response([reversed_order,reversed_order],0,selected,
        'tuesday','beginner',expected) is False


def test_unknown_or_missing_source_schema_cannot_select_a_case():
    for report in ({}, {'schema': 'business-website-browser.v1'}, None):
        with pytest.raises(ValueError, match='Unsupported'):
            browser.scenario_for(report)


def test_browser_report_stays_inside_workspace_without_following_symlinks(monkeypatch, tmp_path):
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    monkeypatch.setattr(browser, 'WORKSPACE', workspace)
    report = workspace / 'report.json'
    report.write_text('{}')
    assert browser.checked_report(report) == report
    outside = tmp_path / 'other.json'
    outside.write_text('{}')
    with pytest.raises(ValueError, match='Linux workspace'):
        browser.checked_report(outside)
    alias = workspace / 'alias.json'
    alias.symlink_to(report)
    with pytest.raises(ValueError, match='symlink'):
        browser.checked_report(alias)
    directory_alias = workspace / 'redirect'
    directory_alias.symlink_to(workspace, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        browser.checked_report(directory_alias / 'report.json')
    assert not (workspace / 'browser').exists()


def test_menu_closed_checks_rendered_links_and_keyboard_access_not_empty_nav_box():
    import subprocess
    script = """
    function run(width, focusable, expanded, count=1) {
        const link = {getBoundingClientRect:()=>({width,height:width,top:2000}),
            focus:()=>{if(focusable)document.activeElement=link}};
        global.document = {activeElement:null,
            getElementById:()=>({getAttribute:()=>String(expanded)}),
            querySelectorAll:()=>Array(count).fill(link)};
        global.getComputedStyle = ()=>({display:'block',visibility:'visible'});
        return REPLACE_EXPRESSION;
    }
    process.stdout.write(JSON.stringify([
        run(0,false,false), run(20,false,false), run(0,true,false),
        run(0,false,true), run(0,false,false,0)]));
    """.replace('REPLACE_EXPRESSION', browser.MENU_CLOSED)
    result = subprocess.run(['node', '-'], input=script, text=True,
                            capture_output=True, check=True, timeout=5)
    assert json.loads(result.stdout) == [True, False, False, False, False]


def test_evidence_directory_names_cannot_escape_report_parent(tmp_path):
    assert browser.evidence_output(tmp_path/'report.json', 'browser-v3') == tmp_path/'browser-v3'
    for name in ('../browser', '/tmp/browser', 'browser/../elsewhere', ''):
        with pytest.raises(ValueError, match='directory name'):
            browser.evidence_output(tmp_path/'report.json', name)


@pytest.mark.parametrize('report', [
    {'schema': 'business-website-delivery.v1', 'final_sources': {}},
    {'schema': 'business-website-resume.v1', 'source_report': 'report.json', 'final_sources': {}},
    {'schema': 'business-website-revision.v1', 'parent_report': 'resume-1/report.json', 'final_sources': {}},
    {'schema': 'business-website-edge-repair.v1', 'source_report': 'revision-1/report.json', 'final_sources': {}},
])
def test_real_business_report_stages_share_exact_rowerownia_browser_contract(report):
    selected = browser.scenario_for(report)
    original = browser.SCENARIOS['business-website-delivery.v1']
    assert selected is original
    assert selected['api_path'] == '/api/estimate'
    assert selected['field_ids'] == ('service', 'bikes', 'express')
    assert selected['quotes'] == (('basic', '1', False, 90), ('full', '3', True, 690),
                                  ('basic', '8', True, 1120))


@pytest.mark.parametrize('damage', [None, 'cleanup', 'profile', 'exit', 'schema', 'response'])
def test_preview_contract_matches_actual_harness_and_rejects_bad_runs(monkeypatch, damage):
    profile = {'profile': 'python-web-preview-v1', 'harness_checksum': 'fixture'}
    reply = {'schema': 'python-web-preview.v1', 'response': {'status': 200, 'body': '{"total":90}'}}
    run = {'profile': profile, 'exit_code': 0, 'cli_exit_code': 0,
           'cleanup_confirmed': True, 'reason': None}
    if damage == 'cleanup': run['cleanup_confirmed'] = False
    if damage == 'profile': run['profile'] = {}
    if damage == 'exit': run['exit_code'] = 1
    if damage == 'schema': reply['schema'] = 'wrong'
    if damage == 'response': reply['response'] = None
    run['log'] = json.dumps(reply)
    monkeypatch.setattr(browser, 'check_idle', lambda: None)
    monkeypatch.setattr(browser, 'preview_configuration', lambda: profile)
    class Runner:
        def __init__(self, path): assert path == '/api/estimate?service=basic&bikes=1&express=0'
        def run(self, files, config, name): return run
    monkeypatch.setattr(browser, 'PreviewRunner', Runner)
    if damage:
        with pytest.raises(ValueError): browser.backend_response({}, '/api/estimate?service=basic&bikes=1&express=0')
    else:
        response, _ = browser.backend_response({}, '/api/estimate?service=basic&bikes=1&express=0')
        assert response == reply['response']
