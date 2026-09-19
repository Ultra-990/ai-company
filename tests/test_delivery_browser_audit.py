"""Offline tests of the trusted pilot tools; no generated code is executed."""
import json
from hashlib import sha256
import pytest
from scripts import check_delivery_browser as browser
from tests.application_pilot_checks import PROBES,harness_source
from tests.test_package_runner import FILES


def test_browser_input_is_a_bounded_successful_synthetic_report(tmp_path,monkeypatch):
    monkeypatch.setattr(browser,'WORKSPACE_ROOT',tmp_path/'workspaces')
    browser.WORKSPACE_ROOT.mkdir()
    report=browser.WORKSPACE_ROOT/'report.json'
    content=json.dumps({'quality':{'state':'passed'},'candidate_created':True,'final_sources':FILES})
    report.write_text(content)
    files,checksum=browser.load_sources(report)
    assert files==FILES and checksum==sha256(content.encode()).hexdigest()
    outside=tmp_path/'other.json';outside.write_text(content)
    with pytest.raises(ValueError):browser.load_sources(outside)
    link=browser.WORKSPACE_ROOT/'link.json';link.symlink_to(outside)
    with pytest.raises(ValueError):browser.load_sources(link)
    report.write_text('x'*(2*1024*1024+1))
    with pytest.raises(ValueError):browser.load_sources(report)
    for data in ({'quality':{'state':'failed'}},
                 {'quality':{'state':'passed'},'candidate_created':False},
                 {'quality':{'state':'passed'},'candidate_created':True,'final_sources':FILES|{'../escape.py':'x'}}):
        report.write_text(json.dumps(data))
        with pytest.raises(ValueError):browser.load_sources(report)


@pytest.mark.parametrize('case',['valid','empty_discount','inner_html','no_file_notice'])
def test_independent_checks_detect_regressions(case):
    # Only execute our trusted wrapper over an in-memory HTTP stub.
    # Neither app.py nor any model-authored source is imported/executed here.
    hook=harness_source().split('_basic_fetch=fetch',1)[1].rsplit("if __name__=='__main__':sys.exit(main())",1)[0]
    html="<!doctype html><script>if(location.protocol==='file:')notice.textContent='Start server';</script>"
    if case=='inner_html':html+='<script>result.innerHTML = data;</script>'
    if case=='no_file_notice':html='<p>ordinary page</p>'
    observed=[]
    def fetch(path):
        observed.append(path)
        if path=='/':return 200,html
        if case=='empty_discount' and path.endswith('discount='):return 200,'{}'
        status,body=next((status,body) for target,status,body in PROBES if target==path)
        return status,json.dumps(body)
    scope={'fetch':fetch,'json':json}
    exec(compile('_basic_fetch=fetch'+hook,'trusted-pilot-wrapper','exec'),scope)
    if case=='valid':
        assert scope['fetch']('/')==(200,html)
        assert len(observed)==1+len(PROBES)
    else:
        with pytest.raises(ValueError,match='Independent acceptance'):scope['fetch']('/')
