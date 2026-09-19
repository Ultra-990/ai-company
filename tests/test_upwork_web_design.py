from hashlib import sha256
import json

import pytest

from scripts import design_upwork_web_pilot as design, upwork_web_case as case
from tests.test_upwork_web_repair import original_files


def baseline():
    files=original_files()
    report={'schema':'qwen-multifile-pilot.v1','scenario':'studio','status':'passed',
            'brief':case.BRIEF,'independent_tests':case.ACCEPTANCE,'accepted':False,'deployed':False,
            'repair_attempts':2,'generation':{'content':json.dumps({'files':files})},
            'source_checksums':{k:sha256(v.encode()).hexdigest() for k,v in files.items()}}
    browser={'schema':'studio-browser-audit.v1','status':'passed','source_report_sha256':'parent-hash',
             'source_checksums':report['source_checksums'],
             'checks':[{'id':key,'passed':True} for key in sorted(design.REQUIRED_BROWSER_CHECKS)]}
    return report,browser,files


def test_design_is_a_separate_css_only_stage_not_reset_of_repair_limit():
    report,browser,files=baseline()
    assert design.verified_baseline(report,browser,'parent-hash') == files
    content=json.dumps({'css':'body{color:#171717}', 'rationale':'Przejrzysty układ.', 'limitations':'Wymaga przeglądu.'})
    revised,notes=design.merge_design(files,content)
    assert revised['style.css'] == 'body{color:#171717}'
    assert {k:v for k,v in revised.items() if k!='style.css'} == {k:v for k,v in files.items() if k!='style.css'}
    assert report['repair_attempts'] == 2


@pytest.mark.parametrize('changes',[{'status':'failed'},{'accepted':True},{'deployed':True},
                                  {'design_attempts':1},{'brief':'changed'},{'source_checksums':{}}])
def test_bad_baseline_is_not_a_design_input(changes):
    report,browser,_=baseline()
    with pytest.raises(ValueError):design.verified_baseline(report|changes,browser,'parent-hash')


@pytest.mark.parametrize('changes',[{'source_report_sha256':'different'},{'status':'failed'},
                                  {'checks':[]},{'source_checksums':{}},
                                  {'checks':[{'id':'four-quote-interactions','passed':False}]}])
def test_design_requires_matching_browser_evidence(changes):
    report,browser,_=baseline()
    with pytest.raises(ValueError):design.verified_baseline(report,browser|changes,'parent-hash')


@pytest.mark.parametrize('content',['{}','[]','{"css":"x","css":"y"}',
    json.dumps({'css':'@import "remote";', 'rationale':'x', 'limitations':'y'}),
    json.dumps({'css':'body{background:url(https://remote)}','rationale':'x','limitations':'y'}),
    json.dumps({'css':'body{}','rationale':'','limitations':'y'}),
    json.dumps({'css':'body{}','rationale':'x','limitations':'y','app.js':'overwrite'}),
    json.dumps({'css':'x'*14001,'rationale':'x','limitations':'y'})])
def test_invalid_design_response_cannot_modify_sources(content):
    with pytest.raises(ValueError):design.merge_design(original_files(),content)


def test_dry_run_never_invokes_model(tmp_path,monkeypatch,capsys):
    report,browser,_=baseline()
    source=tmp_path/'report.json';source.write_text(json.dumps(report))
    browser['source_report_sha256']=sha256(source.read_bytes()).hexdigest()
    view=tmp_path/'browser.json';view.write_text(json.dumps(browser))
    monkeypatch.setattr(design,'ROOT',tmp_path)
    monkeypatch.setattr(design,'check_idle',lambda:pytest.fail('No resources in dry mode'))
    assert design.main([str(source),str(view)]) == 0
    result=json.loads(capsys.readouterr().out)
    assert result['editable'] == ['style.css'] and result['inference'] is False
