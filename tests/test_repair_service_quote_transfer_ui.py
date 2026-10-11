import pytest

from scripts import repair_service_quote_transfer_ui as repair


def browser_fixture():
    required = ('required-content', 'labelled-fields', 'desktop-no-overflow', 'navigation',
                'quote-check-2-False', 'quote-restore-1-True', 'quote-restore-6-True',
                'faq-opens', 'mobile-no-overflow', 'mobile-menu-closed', 'mobile-menu-open',
                'mobile-escape', 'file-mode-safe')
    return {'schema': 'service-quote-transfer-browser.v1', 'status': 'failed',
            'source_report_sha256': repair.SOURCE_SHA256,
            'checks': [{'name': name, 'passed': name != 'mobile-menu-closed'} for name in required]}


def test_browser_evidence_requires_exact_single_menu_failure():
    report = browser_fixture()
    assert repair.validate_browser_data(report) is None
    report['checks'][10]['passed'] = False
    with pytest.raises(ValueError, match='12/13'):
        repair.validate_browser_data(report)


def test_repair_scope_requires_both_ui_files_and_byte_preserves_other_four():
    base = {'index.html': 'old html', 'style.css': 'old css', 'app.js': 'fixed js',
            'app.py': 'server', 'test_app.py': 'tests', 'README.md': 'readme'}
    fixed = base | {'index.html': 'new html', 'style.css': 'new css'}
    assert repair.repair_scope(base, fixed) is True
    assert all(fixed[name] == base[name] for name in ('app.js', 'app.py', 'test_app.py', 'README.md'))
    assert repair.repair_scope(base, base | {'index.html': 'new html'}) is False
    assert repair.repair_scope(base, fixed | {'app.js': 'changed'}) is False


def test_feedback_names_real_geometry_fault_and_preserved_app_logic():
    assert 'position:absolute' in repair.DESCRIPTION and 'top:100%' in repair.DESCRIPTION
    assert 'poza widoczny ekran' in repair.DESCRIPTION
    assert 'app.js bajt w bajt' in repair.DESCRIPTION
    assert 'telefonu, e-maila i adresu pocztowego' in repair.DESCRIPTION
    assert 'Restauracja (Restore)' in repair.DESCRIPTION and 'value=restore' in repair.DESCRIPTION
    assert 'rok 2024' in repair.DESCRIPTION
    assert repair.CHANGED_FILES == {'index.html', 'style.css'}
