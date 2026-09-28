"""Reconstruct the local learning state after a host restart.

This is an observation tool only: it never starts Ollama, loads weights, or
changes qualification evidence.  The report gives the next safe action so a
new process can continue from durable files rather than from chat memory.
"""
import argparse
import json
import subprocess
from datetime import date
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
WORKSPACE = Path('/home/marcin/ai-company-workspaces/learning-autopilot')
QUALIFICATION = WORKSPACE / 'upwork-qualification-current.json'
CHECKPOINT = WORKSPACE / 'resume-checkpoint.json'


def git_state() -> dict[str, Any]:
    def run(*args: str) -> str:
        return subprocess.check_output(['git', '-C', str(REPO), *args], text=True).strip()
    return {'branch': run('branch', '--show-current'), 'commit': run('rev-parse', 'HEAD'),
            'worktree_clean': not bool(run('status', '--short'))}


def ollama_state() -> dict[str, Any]:
    import http.client
    connection = http.client.HTTPConnection('127.0.0.1', 11434, timeout=2)
    try:
        connection.request('GET', '/api/tags')
        response = connection.getresponse()
        raw = response.read(1024 * 1024 + 1)
        if response.status != 200 or len(raw) > 1024 * 1024:
            return {'reachable': False, 'reason': 'http_status_or_size'}
        payload = json.loads(raw)
        return {'reachable': True, 'models': sorted(item.get('name') for item in payload.get('models', []))}
    except Exception as exc:
        return {'reachable': False, 'reason': type(exc).__name__}
    finally:
        connection.close()


def build(*, qualification: dict[str, Any], git: dict[str, Any], ollama: dict[str, Any]) -> dict[str, Any]:
    if not ollama.get('reachable'):
        next_action = 'start_or_restore_local_ollama_then_recheck'
    elif not git.get('worktree_clean'):
        next_action = 'review_and_commit_or_discard_uncommitted_changes'
    elif qualification.get('all_five_qualified') is not True:
        next_action = 'resume_isolated_amazon_panel_trial_with_local_model'
    else:
        next_action = 'run_final_completion_audit'
    return {
        'schema': 'learning-resume-checkpoint.v1',
        'checked_on': date.today().isoformat(),
        'git': git,
        'ollama': ollama,
        'qualification': {
            'qualified_services': qualification.get('qualified_services', []),
            'qualified_count': qualification.get('qualified_count', 0),
            'all_five_qualified': qualification.get('all_five_qualified', False),
            'parity_claim_allowed': qualification.get('parity_claim_allowed', False),
        },
        'next_action': next_action,
        'automatic_promotion': False,
        'production_routing_changed': False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='write the private checkpoint file')
    args = parser.parse_args()
    qualification = json.loads(QUALIFICATION.read_text(encoding='utf-8'))
    report = build(qualification=qualification, git=git_state(), ollama=ollama_state())
    if args.write:
        CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
        CHECKPOINT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
