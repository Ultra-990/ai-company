import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import revise_service_quote_transfer as revision
from scripts.filewise_application_provider import FILES


def synthetic_parent():
    return {'task_id': 1, 'final_sources': {name: f'synthetic {name}' for name in FILES}}


class ScalarSession:
    def __init__(self, *rows): self.rows = iter(rows)
    def scalar(self, _statement): return next(self.rows)


def test_database_gate_accepts_only_failed_repair_with_exact_source_package(monkeypatch):
    parent = synthetic_parent()
    latest = SimpleNamespace(state='failed', error_code='invalid_file_repair')
    origin = SimpleNamespace(metrics={'package_id': 2,
                                      'package_checksum': revision.EXPECTED_PACKAGE_CHECKSUM})
    package = SimpleNamespace(checksum=revision.EXPECTED_PACKAGE_CHECKSUM)
    manifest = {'files': [{'path': name, 'content': content}
                          for name, content in parent['final_sources'].items()]}
    monkeypatch.setattr(revision, 'read_package', lambda session, task_id, package_id:
                        (package, manifest))
    assert revision.validate_database(ScalarSession(latest, origin), parent) == 1


@pytest.mark.parametrize('latest', [
    SimpleNamespace(state='awaiting_review', error_code=None),
    SimpleNamespace(state='failed', error_code='different_failure'),
])
def test_database_gate_rejects_completed_or_wrong_transition(monkeypatch, latest):
    parent = synthetic_parent()
    origin = SimpleNamespace(metrics={'package_id': 2,
                                      'package_checksum': revision.EXPECTED_PACKAGE_CHECKSUM})
    monkeypatch.setattr(revision, 'read_package', lambda *args:
                        (_ for _ in ()).throw(AssertionError('package must not be read')))
    with pytest.raises(ValueError, match='failed-repair checkpoint'):
        revision.validate_database(ScalarSession(latest, origin), parent)


def test_dry_run_reports_contract_without_workspace_or_model(monkeypatch, capsys):
    parent = synthetic_parent()
    database = Path('/synthetic/private/test.db')

    class Engine:
        disposed = False
        def dispose(self): self.disposed = True

    class Context:
        def __enter__(self): return object()
        def __exit__(self, *args): return False

    engine = Engine()
    monkeypatch.setattr(revision.sys, 'argv', ['revise_service_quote_transfer.py'])
    monkeypatch.setattr(revision, 'load_parent', lambda: (parent, database))
    monkeypatch.setattr(revision, 'create_database_engine', lambda url: engine)
    monkeypatch.setattr(revision, 'create_session_factory', lambda value: lambda: Context())
    monkeypatch.setattr(revision, 'validate_database', lambda session, value: 1)
    monkeypatch.setattr(revision, 'digest', lambda path: {
        revision.PARENT_REPORT: 'parent-sha',
        revision.HARNESS: revision.EXPECTED_HARNESS_CHECKSUM}[path])
    monkeypatch.setattr(revision, 'run', lambda: (_ for _ in ()).throw(AssertionError('model invoked')))
    assert revision.main() == 0
    result = json.loads(capsys.readouterr().out)
    assert result['model_invoked'] is False
    assert result['source_package_id'] == 2
    assert result['parent_report_sha256'] == 'parent-sha'
    assert result['frozen_harness_sha256'] == revision.EXPECTED_HARNESS_CHECKSUM
    assert engine.disposed is True


def test_revision_request_keeps_test_strength_and_requires_all_ui_repairs():
    request = revision.DESCRIPTION
    for required in ('Handler.do_GET', 'json.loads', 'zewnętrzne style.css i app.js',
                     'dokładnie jeden widoczny h1', 'poza ukrywanym mobilnie nav#site-nav',
                     'osobną, widoczną sekcję procesu', 'selectem 0/1 albo checkboxem'):
        assert required in request
    assert 'nie usuwaj ani nie osłabiaj testów' in request
