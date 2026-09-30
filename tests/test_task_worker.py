from pathlib import Path

import pytest

from app.models.task import TaskStatus
from app.services.tasks import TaskRepository
from app.services.worker import TaskWorker


@pytest.fixture
def task_repository(tmp_path: Path):
    repository = TaskRepository(
        f"sqlite:///{tmp_path / 'tasks_test.sqlite3'}",
    )

    try:
        yield repository
    finally:
        repository.close()


def test_worker_claims_oldest_ready_task(
    task_repository: TaskRepository,
) -> None:
    first = task_repository.create(title="Pierwsze")
    second = task_repository.create(title="Drugie")

    task_repository.approve(first.id)
    task_repository.approve(second.id)

    worker = TaskWorker(task_repository, worker_id="worker-1")

    claimed = worker.claim_next()

    assert claimed is not None
    assert claimed.id == first.id
    assert claimed.status is TaskStatus.IN_PROGRESS
    assert task_repository.get_required(first.id).status is TaskStatus.IN_PROGRESS
    assert task_repository.get_required(second.id).status is TaskStatus.PENDING


def test_worker_returns_none_when_queue_is_empty(
    task_repository: TaskRepository,
) -> None:
    worker = TaskWorker(task_repository, worker_id="worker-1")

    assert worker.claim_next() is None


def test_worker_does_not_claim_unapproved_task(
    task_repository: TaskRepository,
) -> None:
    task_repository.create(title="Niezaakceptowane")

    worker = TaskWorker(task_repository, worker_id="worker-1")

    assert worker.claim_next() is None


def test_worker_validates_worker_id(
    task_repository: TaskRepository,
) -> None:
    with pytest.raises(ValueError, match="nie może być pusty"):
        TaskWorker(task_repository, worker_id="   ")

    with pytest.raises(ValueError, match="100 znaków"):
        TaskWorker(task_repository, worker_id="x" * 101)


@pytest.mark.parametrize('task_count', [1, 3])
def test_concurrent_workers_reserve_distinct_tasks_with_one_audit_each(
    task_repository, tmp_path, task_count,
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from sqlalchemy import select
    from app.models.audit import AuditEvent
    from app.models.task import TaskAttempt

    tasks = [task_repository.create(title=f'Praca {i}') for i in range(task_count)]
    for task in tasks:
        task_repository.approve(task.id)
    start = Barrier(3)
    # Separate engines/connections, as in separate API workers; never the live DB.
    repositories = [TaskRepository(
        f"sqlite:///{tmp_path / 'tasks_test.sqlite3'}", initialize=False,
    ) for _ in range(3)]

    def claim(index):
        start.wait(timeout=5)
        return TaskWorker(repositories[index], worker_id=f'worker-{index}').claim_next()

    try:
        with ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(claim, range(3)))
    finally:
        for repository in repositories:
            repository.close()
    claimed = [task for task in results if task is not None]
    assert sorted(task.id for task in claimed) == sorted(task.id for task in tasks)
    assert all(task.status is TaskStatus.IN_PROGRESS for task in claimed)
    with task_repository._session_factory() as session:
        attempts = list(session.scalars(select(TaskAttempt)))
        events = list(session.scalars(select(AuditEvent).where(
            AuditEvent.event_type == 'task_execution', AuditEvent.operation == 'claim',
        )))
    assert len(attempts) == len(events) == task_count
    assert {attempt.task_id for attempt in attempts} == {task.id for task in tasks}
    assert len({attempt.worker_id for attempt in attempts}) == task_count
    assert task_repository.claim_next(worker_id='after') is None


def test_atomic_dispatch_preserves_queue_time_then_id_order(task_repository):
    from datetime import timedelta
    from app.models.task import Task, utc_now

    tasks = [task_repository.create(title=f'FIFO {i}') for i in range(3)]
    for task in tasks:
        task_repository.approve(task.id)
    now = utc_now()
    with task_repository._session_factory() as session:
        for task in tasks:
            session.get(Task, task.id).queued_at = now
        session.get(Task, tasks[2].id).queued_at = now - timedelta(seconds=1)
        session.commit()
    worker = TaskWorker(task_repository, worker_id='fifo')
    assert [worker.claim_next().id for _ in tasks] == [tasks[2].id, tasks[0].id, tasks[1].id]


def test_atomic_dispatch_skips_unqueued_rejected_cancelled_and_delegated(task_repository):
    from sqlalchemy import select
    from app.models.delegation import TaskDelegation
    from app.models.task import ApprovalStatus, Task, TaskAttempt

    tasks = [task_repository.create(title=f'Filtr {i}') for i in range(5)]
    for task in tasks:
        task_repository.approve(task.id)
    with task_repository._session_factory() as session:
        session.get(Task, tasks[0].id).queued_at = None
        session.get(Task, tasks[1].id).approval_status = ApprovalStatus.REJECTED
        session.get(Task, tasks[2].id).status = TaskStatus.CANCELLED
        # A persisted planning delegation must stay excluded even if old data
        # also marks the task approved and queued.
        session.add(TaskDelegation(task_id=tasks[3].id, department_id=1,
            manager_id=1, worker_id=2, reviewer_id=3, execution_brief='Fixture',
            completion_criterion='Fixture', policy={}))
        session.commit()
    worker = TaskWorker(task_repository, worker_id='filters')
    assert worker.claim_next().id == tasks[4].id
    assert worker.claim_next() is None
    with task_repository._session_factory() as session:
        assert list(session.scalars(select(TaskAttempt.task_id))) == [tasks[4].id]


@pytest.mark.parametrize('explicit_task', [False, True])
def test_claim_failure_rolls_back_status_attempt_audit_and_releases_lock(
    task_repository, explicit_task,
):
    from sqlalchemy import event, select
    from sqlalchemy.exc import OperationalError
    from app.models.audit import AuditEvent
    from app.models.task import TaskAttempt

    task = task_repository.create(title='Atomowy zapis')
    task_repository.approve(task.id)

    def reject_attempt_insert(connection, cursor, statement, parameters, context, many):
        if statement.startswith('INSERT INTO task_attempts'):
            raise OperationalError('fixture', {}, Exception('simulated write failure'))

    event.listen(task_repository._engine, 'before_cursor_execute', reject_attempt_insert)
    try:
        with pytest.raises(OperationalError):
            if explicit_task:
                task_repository.claim(task.id, worker_id='failed')
            else:
                task_repository.claim_next(worker_id='failed')
    finally:
        event.remove(task_repository._engine, 'before_cursor_execute', reject_attempt_insert)
    assert task_repository.get_required(task.id).status is TaskStatus.PENDING
    with task_repository._session_factory() as session:
        assert list(session.scalars(select(TaskAttempt))) == []
        assert list(session.scalars(select(AuditEvent).where(
            AuditEvent.event_type == 'task_execution',
        ))) == []
    recovered = task_repository.claim_next(worker_id='recovered')
    assert recovered.id == task.id
    assert recovered.status is TaskStatus.IN_PROGRESS


def test_waiting_worker_selects_after_first_claim_commits(task_repository, tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from sqlalchemy import event

    first = task_repository.create(title='Pierwszy wybór')
    second = task_repository.create(title='Kolejny wybór')
    task_repository.approve(first.id)
    task_repository.approve(second.id)
    other = TaskRepository(f"sqlite:///{tmp_path / 'tasks_test.sqlite3'}", initialize=False)
    first_select = Event()
    second_begin = Event()

    def hold_first_selection(connection, cursor, statement, parameters, context, many):
        if statement.startswith('SELECT tasks.id') and 'LIMIT' in statement:
            first_select.set()
            assert second_begin.wait(timeout=5), 'Second caller did not request its transaction'

    def observe_second_begin(connection, cursor, statement, parameters, context, many):
        if statement == 'BEGIN IMMEDIATE':
            assert first_select.wait(timeout=5)
            second_begin.set()

    event.listen(task_repository._engine, 'before_cursor_execute', hold_first_selection)
    event.listen(other._engine, 'before_cursor_execute', observe_second_begin)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            initial = pool.submit(task_repository.claim_next, worker_id='first')
            assert first_select.wait(timeout=5)
            waiting = pool.submit(other.claim_next, worker_id='waiting')
            assert initial.result(timeout=10).id == first.id
            assert waiting.result(timeout=10).id == second.id
    finally:
        event.remove(task_repository._engine, 'before_cursor_execute', hold_first_selection)
        event.remove(other._engine, 'before_cursor_execute', observe_second_begin)
        other.close()
