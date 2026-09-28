from scripts.resume_learning_checkpoint import build


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
    )
    assert report['next_action'] == 'resume_isolated_amazon_panel_trial_with_local_model'

