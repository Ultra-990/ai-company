from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text

from app.models.task import Task, TaskAttempt, TaskStatus
from tests.conftest import OWNER_HEADERS, WORKER_HEADERS

NOW = datetime(2026, 9, 30, 10, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setattr('app.services.task_execution_diagnostics.utc_now', lambda: NOW)


def claimed(repository, *, seconds=60):
    task = repository.create(title='Diagnostyka próby')
    repository.approve(task.id)
    repository.claim(task.id, worker_id='diagnostic-worker')
    with repository._session_factory() as session:
        attempt = session.scalar(select(TaskAttempt).where(TaskAttempt.task_id == task.id))
        attempt.started_at = NOW - timedelta(seconds=seconds)
        session.commit()
    return task


def snapshot(repository):
    with repository._session_factory() as session:
        return [session.execute(text(f'SELECT * FROM {table} ORDER BY id')).all()
                for table in ('tasks', 'task_attempts', 'audit_events')]


def get(client, task_id, **params):
    return client.get(f'/api/tasks/{task_id}/execution-diagnostics',
                      headers=OWNER_HEADERS, params=params)


@pytest.mark.parametrize('headers', [{}, WORKER_HEADERS])
def test_diagnostics_owner_only(client, task_repository, headers):
    task = claimed(task_repository)
    response = client.get(f'/api/tasks/{task.id}/execution-diagnostics', headers=headers)
    assert response.status_code in {401, 403}


def test_missing_task_and_bounded_threshold(client, task_repository):
    assert get(client, 999999).status_code == 404
    task = claimed(task_repository)
    for invalid in (0, -1, 604801, 'not-a-number'):
        assert get(client, task.id, attention_after_seconds=invalid).status_code == 422
    for invalid in (True, 0, 604801):
        with pytest.raises(ValueError):
            task_repository.execution_diagnostics(task.id, attention_after_seconds=invalid)


@pytest.mark.parametrize('age,attention', [(60, False), (900, True), (3600, True)])
def test_unfinished_attempt_age_does_not_prove_failure_or_change_database(
    client, task_repository, age, attention,
):
    task = claimed(task_repository, seconds=age)
    before = snapshot(task_repository)
    response = get(client, task.id)
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    body = response.json()
    assert body['state'] == 'awaiting_worker_confirmation'
    assert body['open_age_seconds'] == age
    assert body['needs_inspection'] is attention
    assert body['worker_liveness'] == 'unknown'
    assert body['failure_confirmed'] is False
    assert body['automatic_retry_allowed'] is False
    assert body['heartbeat_available'] is False
    assert body['task_changed'] is False
    assert body['latest_attempt']['worker_id'] == 'diagnostic-worker'
    assert body['oldest_open_started_at'].endswith('Z')
    assert snapshot(task_repository) == before
    if age == 900:
        assert get(client, task.id, attention_after_seconds=901).json()['needs_inspection'] is False


def test_finished_and_awaiting_review_are_not_mistaken_for_abandoned_work(client, task_repository):
    task = claimed(task_repository, seconds=100000)
    task_repository.submit_result(task.id, result_content='PRIVATE RESULT', reason='PRIVATE REASON')
    with task_repository._session_factory() as session:
        attempt = session.scalar(select(TaskAttempt).where(TaskAttempt.task_id == task.id))
        attempt.finished_at = NOW - timedelta(seconds=100)
        session.commit()
    review = get(client, task.id).json()
    assert review['state'] == 'awaiting_review'
    assert review['needs_inspection'] is False
    assert review['open_age_seconds'] is None
    assert 'PRIVATE' not in str(review)
    with task_repository._session_factory() as session:
        attempt = session.scalar(select(TaskAttempt).where(TaskAttempt.task_id == task.id))
        attempt.status = 'completed'
        attempt.verification_status = 'pending'
        session.get(Task, task.id).status = TaskStatus.COMPLETED
        session.commit()
    before = snapshot(task_repository)
    done = get(client, task.id).json()
    assert done['state'] == 'no_open_attempt'
    assert done['latest_attempt']['verification_status'] == 'pending'
    assert not done['needs_inspection']
    assert snapshot(task_repository) == before


def test_missing_attempt_and_conflicting_task_state_require_inspection(client, task_repository):
    task = task_repository.create(title='Stare zadanie bez próby')
    assert get(client, task.id).json()['state'] == 'no_open_attempt'
    with task_repository._session_factory() as session:
        session.get(Task, task.id).status = TaskStatus.IN_PROGRESS
        session.commit()
    assert get(client, task.id).json()['inspection_reasons'] == ['missing_attempt']
    second = claimed(task_repository)
    with task_repository._session_factory() as session:
        session.get(Task, second.id).status = TaskStatus.BLOCKED
        session.commit()
    body = get(client, second.id).json()
    assert body['state'] == 'inconsistent'
    assert 'task_state_conflicts_with_attempt' in body['inspection_reasons']
    assert not body['failure_confirmed']


def test_older_open_attempt_is_not_hidden_by_latest_finished_attempt(client, task_repository):
    task = claimed(task_repository, seconds=3600)
    with task_repository._session_factory() as session:
        session.add(TaskAttempt(task_id=task.id, worker_id='another', status='completed',
            started_at=NOW-timedelta(seconds=120), finished_at=NOW-timedelta(seconds=60)))
        session.commit()
    body = get(client, task.id).json()
    assert body['open_attempt_count'] == 1
    assert body['latest_attempt']['status'] == 'completed'
    assert body['state'] == 'inconsistent'
    assert 'older_attempt_still_open' in body['inspection_reasons']
    assert body['open_age_seconds'] == 3600


@pytest.mark.parametrize('bad_time', ['future', 'reversed', 'malformed'])
def test_invalid_timestamps_never_confirm_failure(client, task_repository, bad_time):
    task = claimed(task_repository)
    with task_repository._session_factory() as session:
        attempt = session.scalar(select(TaskAttempt).where(TaskAttempt.task_id == task.id))
        if bad_time == 'future':
            attempt.started_at = NOW + timedelta(microseconds=1)
        elif bad_time == 'reversed':
            attempt.finished_at = NOW - timedelta(seconds=120)
        else:
            session.execute(text("UPDATE task_attempts SET started_at='invalid' WHERE task_id=:task"), {'task': task.id})
        session.commit()
    response = get(client, task.id)
    if bad_time == 'malformed':
        assert response.status_code == 503
    else:
        body = response.json()
        assert body['state'] == 'inconsistent'
        assert body['needs_inspection'] and not body['failure_confirmed']
        if bad_time == 'future':
            assert body['open_age_seconds'] is None


def test_read_uses_explicit_snapshot_and_does_not_commit(task_repository):
    from sqlalchemy import event
    task = claimed(task_repository)
    statements = []
    def capture(connection, cursor, statement, parameters, context, many):
        statements.append(statement)
    event.listen(task_repository._engine, 'before_cursor_execute', capture)
    try:
        task_repository.execution_diagnostics(task.id)
    finally:
        event.remove(task_repository._engine, 'before_cursor_execute', capture)
    assert statements[0] == 'BEGIN'
    assert all(statement == 'BEGIN' or statement.lstrip().startswith('SELECT') for statement in statements)


def test_finishing_between_reads_preserves_original_snapshot(task_repository):
    from sqlalchemy import event
    from app.services.tasks import TaskRepository

    task = claimed(task_repository)
    with task_repository._engine.connect() as connection:
        connection.exec_driver_sql('PRAGMA journal_mode=WAL')
    other = TaskRepository(str(task_repository._engine.url), initialize=False)
    finished = []

    def finish_between_reads(connection, cursor, statement, parameters, context, many):
        if 'FROM task_attempts' in statement and 'ORDER BY' in statement and not finished:
            finished.append(True)
            # Another connection commits while the diagnostic reader retains
            # its earlier view; WAL permits this without blocking the writer.
            other.submit_result(task.id, result_content='Result', reason='Finished independently')

    event.listen(task_repository._engine, 'before_cursor_execute', finish_between_reads)
    try:
        body = task_repository.execution_diagnostics(task.id)
    finally:
        event.remove(task_repository._engine, 'before_cursor_execute', finish_between_reads)
        other.close()
    assert finished == [True]
    assert body['latest_attempt']['status'] == 'started'
    assert body['open_attempt_count'] == 1
    assert body['pending_review_count'] == 0
    assert body['state'] == 'awaiting_worker_confirmation'
    assert task_repository.pending_review(task.id).status == 'awaiting_review'


def test_multiple_open_attempts_and_review_conflicts_are_reported(client, task_repository):
    task = claimed(task_repository)
    with task_repository._session_factory() as session:
        session.add(TaskAttempt(task_id=task.id, worker_id='second', status='started',
            started_at=NOW-timedelta(seconds=30)))
        session.add(TaskAttempt(task_id=task.id, worker_id='third', status='awaiting_review',
            started_at=NOW-timedelta(seconds=20), finished_at=NOW-timedelta(seconds=10)))
        session.commit()
    body = get(client, task.id).json()
    assert body['state'] == 'inconsistent'
    assert body['open_attempt_count'] == 2
    assert body['pending_review_count'] == 1
    assert {'multiple_open_attempts', 'conflicting_review_attempts'} <= set(body['inspection_reasons'])
    assert not body['failure_confirmed']


def test_closed_attempt_without_finish_time_is_inconsistent(client, task_repository):
    task = claimed(task_repository)
    with task_repository._session_factory() as session:
        attempt = session.scalar(select(TaskAttempt).where(TaskAttempt.task_id == task.id))
        attempt.status = 'completed'
        session.get(Task, task.id).status = TaskStatus.COMPLETED
        session.commit()
    body = get(client, task.id).json()
    assert body['state'] == 'inconsistent'
    assert body['inspection_reasons'] == ['invalid_attempt_timestamps']
    assert not body['failure_confirmed']
