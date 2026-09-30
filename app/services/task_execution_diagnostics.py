"""Read-only evidence about task attempts; timestamps cannot prove worker death."""
from datetime import datetime, timezone

from sqlalchemy import func, select

from app.models.task import Task, TaskAttempt, TaskStatus, utc_now


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    # SQLite's DateTime round trip omits timezone information; stored values are UTC.
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def inspect_execution(session, task_id: int, *, attention_after_seconds: int = 900):
    """Caller supplies a consistent read transaction. No probes or writes."""
    if type(attention_after_seconds) is not int or not 1 <= attention_after_seconds <= 604800:
        raise ValueError('Próg uwagi musi mieścić się w zakresie 1–604800 sekund.')
    task = session.get(Task, task_id)
    if task is None:
        raise LookupError(f'Nie znaleziono zadania {task_id}')
    checked_at = _utc(utc_now())
    latest = session.scalar(select(TaskAttempt).where(TaskAttempt.task_id == task_id)
        .order_by(TaskAttempt.id.desc()).limit(1))
    open_condition = (TaskAttempt.status == 'started') & TaskAttempt.finished_at.is_(None)
    counts = session.execute(select(
        func.count().label('total'),
        func.count().filter(open_condition).label('open'),
        func.count().filter(TaskAttempt.status == 'awaiting_review').label('review'),
        func.count().filter((TaskAttempt.status == 'started') & TaskAttempt.finished_at.is_not(None)).label('contradictory'),
        func.min(TaskAttempt.started_at).filter(open_condition).label('oldest_open'),
    ).where(TaskAttempt.task_id == task_id)).one()
    reasons = []
    if counts.open > 1:
        reasons.append('multiple_open_attempts')
    if counts.review > 1 or (counts.review and counts.open):
        reasons.append('conflicting_review_attempts')
    if counts.contradictory:
        reasons.append('started_attempt_has_finish_time')
    if counts.open and latest.status != 'started':
        reasons.append('older_attempt_still_open')
    if (counts.open or counts.review) and task.status is not TaskStatus.IN_PROGRESS:
        reasons.append('task_state_conflicts_with_attempt')
    if task.status is TaskStatus.IN_PROGRESS and not counts.open and not counts.review:
        reasons.append('missing_attempt' if latest is None else 'no_open_attempt_for_active_task')
    if latest is not None:
        start, finish = _utc(latest.started_at), _utc(latest.finished_at)
        if (start is None or (latest.status != 'started' and finish is None)
                or (finish is not None and (finish < start or finish > checked_at))):
            reasons.append('invalid_attempt_timestamps')
    state = ('inconsistent' if reasons else 'awaiting_review' if counts.review
             else 'awaiting_worker_confirmation' if counts.open else 'no_open_attempt')
    oldest = _utc(counts.oldest_open)
    age = int((checked_at - oldest).total_seconds()) if oldest is not None and oldest <= checked_at else None
    if oldest is not None and oldest > checked_at:
        reasons.append('attempt_start_is_in_future')
        state = 'inconsistent'
    if counts.open and oldest is None:
        reasons.append('missing_attempt_start')
        state = 'inconsistent'
    if age is not None and age >= attention_after_seconds:
        reasons.append('open_attempt_exceeds_attention_age')
    return {
        'schema': 'task-execution-diagnostics.v1',
        'task_id': task.id, 'task_status': task.status.value,
        'checked_at': checked_at, 'state': state,
        'attempt_count': counts.total, 'open_attempt_count': counts.open,
        'pending_review_count': counts.review,
        'oldest_open_started_at': oldest, 'open_age_seconds': age,
        'attention_after_seconds': attention_after_seconds,
        'needs_inspection': bool(reasons), 'inspection_reasons': reasons,
        'latest_attempt': ({
            'id': latest.id, 'worker_id': latest.worker_id, 'status': latest.status,
            'started_at': _utc(latest.started_at), 'finished_at': _utc(latest.finished_at),
            'verification_status': latest.verification_status,
        } if latest is not None else None),
        'worker_liveness': 'unknown', 'heartbeat_available': False,
        'failure_confirmed': False, 'automatic_retry_allowed': False,
        'task_changed': False,
        'message': ('Czas od rozpoczęcia jest sygnałem do sprawdzenia, nie dowodem awarii. '
                    'Sprawdź istniejącego wykonawcę i jego wynik przed decyzją o dalszej pracy.'),
    }
