import json

import pytest

from scripts import repair_workshop_catalog_ui as repair


def browser_fixture():
    names=('required-content','labelled-fields','desktop-no-overflow','navigation',
           'filter-tuesday-beginner','filter-saturday-advanced','filter-tuesday-intermediate',
           'faq-opens','mobile-no-overflow','mobile-menu-closed','mobile-menu-open',
           'mobile-menu-links-in-viewport','mobile-escape','mobile-escape-hides-links','file-mode-safe')
    return {'schema':'workshop-catalog-browser.v1','status':'failed',
            'source_report_sha256':repair.SOURCE_SHA256,
            'checks':[{'name':name,'passed':name!='file-mode-safe'} for name in names]}


def test_browser_evidence_requires_exact_single_file_mode_failure():
    report=browser_fixture();assert repair.validate_browser_data(report) is None
    report['checks'][10]['passed']=False
    with pytest.raises(ValueError,match='14/15'):repair.validate_browser_data(report)


def test_scope_requires_exactly_html_and_javascript_and_preserves_other_four():
    base={'index.html':'old','app.js':'old js','app.py':'server','test_app.py':'tests',
          'style.css':'css','README.md':'readme'}
    fixed=base|{'index.html':'new','app.js':'new js'}
    assert repair.repair_scope(base,fixed) is True
    assert all(fixed[name]==base[name] for name in ('app.py','test_app.py','style.css','README.md'))
    assert repair.repair_scope(base,base|{'index.html':'new'}) is False
    assert repair.repair_scope(base,fixed|{'style.css':'changed'}) is False


def test_feedback_covers_observed_failures_without_changing_api_values():
    assert 'bez początkowego /' in repair.DESCRIPTION
    assert 'all/all' in repair.DESCRIPTION and 'sześć rekordów' in repair.DESCRIPTION
    assert 'po polsku, zachowując wartości API' in repair.DESCRIPTION
    assert repair.CHANGED_FILES=={'index.html','app.js'}


def test_dry_run_never_invokes_model_or_private_database(monkeypatch,capsys):
    monkeypatch.setattr(repair.sys,'argv',['repair_workshop_catalog_ui.py'])
    monkeypatch.setattr(repair,'source_state',lambda:({'task_id':1},{},'/synthetic/test.db'))
    monkeypatch.setattr(repair,'evidence_state',lambda:repair.BROWSER_SHA256)
    monkeypatch.setattr(repair,'run',lambda:pytest.fail('model invoked'))
    assert repair.main()==0
    result=json.loads(capsys.readouterr().out)
    assert result['model_invoked'] is False
    assert result['source_package_id']==2
    assert result['requested_change']==['app.js','index.html']
