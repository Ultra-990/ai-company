"""Bounded project preparation using existing durable tasks, attempts and packets."""
from hashlib import sha256
from datetime import datetime, timezone
import json


def encode_value(value):
    if isinstance(value, datetime):
        return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None
                else value.astimezone(timezone.utc)).isoformat()
    raise TypeError('Unsupported checkpoint value')


def checkpoint(detail, tasks, attempts, runs):
    # Exclude artifacts: saving/reopening an instruction must not invalidate a
    # retry after a lost response. Include attempt identity, not just its state.
    state = {key: detail[key] for key in ('project_id', 'plan_id', 'plan_status', 'brief', 'project_status', 'tasks', 'guidance')}
    state['task_versions'] = [(t.id, t.description, t.updated_at) for t in tasks]
    state['attempt_versions'] = sorted((t.id, t.task_id, t.status, t.verification_status,
                                       t.verified_at, t.result_checksum,
                                       sha256((t.result_content or '').encode()).hexdigest())
                                      for t in attempts.values())
    state['runs'] = sorted((r.id, r.task_id, r.state) for r in runs)
    revision = sha256(json.dumps(state, sort_keys=True, ensure_ascii=True, default=encode_value).encode()).hexdigest()
    current = detail['guidance']['current']
    task = next((t for t in detail['tasks'] if t['id'] == current['task_id']), None)
    allowed = bool(detail['project_status'] in {'planned', 'in_progress'}
                   and detail['plan_status'] in {'draft', 'ready', 'in_progress'}
                   and current['state'] in {'instruction', 'repair'}
                   and task and not task['queued'] and task.get('delegation')
                   and task['delegation']['planning_ready'])
    return {'revision': revision, 'task_id': current['task_id'], 'can_prepare': allowed,
            'execution_enabled': False, 'mode': 'prepare_one_stage'}
