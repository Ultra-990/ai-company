import subprocess

import pytest

from scripts.resume_learning_checkpoint import build, resource_state, ollama_state


def test_checkpoint_requires_ollama_before_model_work():
    report = build(
        qualification={'qualified_services': ['technical_review'], 'qualified_count': 1,
                       'all_five_qualified': False, 'parity_claim_allowed': False},
        git={'branch': 'main', 'commit': 'abc', 'worktree_clean': True},
        ollama={'reachable': False, 'reason': 'ConnectionRefusedError'},
    )
    assert report['next_action'] == 'start_or_restore_local_ollama_then_recheck'
    assert report['automatic_promotion'] is False


def test_checkpoint_selects_isolated_trial_when_runtime_is_ready():
    report = build(
        qualification={'qualified_services': ['technical_review'], 'qualified_count': 1,
                       'all_five_qualified': False, 'parity_claim_allowed': False},
        git={'branch': 'main', 'commit': 'abc', 'worktree_clean': True},
        ollama={'reachable': True, 'models': ['qwen3.8:27b']},
        resources={'ready': True},
    )
    assert report['next_action'] == 'resume_isolated_amazon_panel_trial_with_local_model'


@pytest.mark.parametrize('reason', ['PermissionError', 'TimeoutError', 'invalid_inventory'])
def test_unknown_access_never_recommends_service_restart(reason):
    report = build(qualification={}, git={'worktree_clean': True},
                   ollama={'reachable': False, 'reason': reason})
    assert report['next_action'] == 'verify_local_ollama_access_then_recheck'


@pytest.mark.parametrize('resources', [None, {'ready': False, 'reason': 'active_containers'},
                                      {'ready': False, 'reason': 'gpu_probe_failed'}])
def test_reachable_ollama_is_not_sufficient_to_resume_gpu_work(resources):
    report = build(qualification={}, git={'worktree_clean': True},
                   ollama={'reachable': True, 'models': ['qwen3.8:27b']}, resources=resources)
    assert report['next_action'] in {'resolve_resource_preflight_then_recheck', 'inspect_gpu_driver_then_recheck'}
    assert report['requires_fresh_preflight_before_execution'] is True
    assert report['automatic_promotion'] is False


def test_missing_model_blocks_trial():
    report = build(qualification={}, git={'worktree_clean': True},
                   ollama={'reachable': True, 'models': []}, resources={'ready': True})
    assert report['next_action'] == 'restore_required_local_model_then_recheck'


def test_gpu_failure_has_actionable_diagnostic_without_external_output(monkeypatch):
    from scripts import compare_local_models
    def fail():
        raise subprocess.CalledProcessError(9, ['nvidia-smi'], output='private output')
    monkeypatch.setattr(compare_local_models, 'check_idle', fail)
    assert resource_state() == {'ready': False, 'reason': 'gpu_probe_failed'}


@pytest.mark.parametrize('body', [b'{}', b'[]', b'{"models":[{}]}', b'{"models":[null]}'])
def test_malformed_inventory_is_rejected_and_connection_closed(monkeypatch, body):
    import http.client
    class Connection:
        status = 200
        closed = False
        def request(self, *args): pass
        def getresponse(self): return self
        def read(self, *args): return body
        def close(self): self.closed = True
    conn = Connection()
    monkeypatch.setattr(http.client, 'HTTPConnection', lambda *a, **kw: conn)
    assert ollama_state() == {'reachable': False, 'reason': 'invalid_inventory'}
    assert conn.closed
