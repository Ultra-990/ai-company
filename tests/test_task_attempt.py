from sqlalchemy import select

from app.models.task import TaskAttempt, TaskStatus, TaskTransitionError
from app.services.tasks import TaskRepository


def _attempts_for_task(
    task_repository: TaskRepository,
    task_id: int,
) -> list[TaskAttempt]:
    with task_repository._session_factory() as session:
        attempts = list(
            session.scalars(
                select(TaskAttempt)
                .where(TaskAttempt.task_id == task_id)
                .order_by(TaskAttempt.id.asc())
            ).all()
        )

        for attempt in attempts:
            session.expunge(attempt)

    return attempts


def test_claim_creates_started_task_attempt(
    task_repository: TaskRepository,
) -> None:
    created = task_repository.create(title="Zadanie z próbą")
    task_repository.approve(created.id)

    task_repository.claim(created.id, worker_id="worker-42")

    attempts = _attempts_for_task(task_repository, created.id)

    assert len(attempts) == 1

    attempt = attempts[0]
    assert attempt.task_id == created.id
    assert attempt.worker_id == "worker-42"
    assert attempt.status == "started"
    assert attempt.started_at is not None
    assert attempt.finished_at is None
    assert attempt.error_summary is None


def test_complete_closes_active_task_attempt(
    task_repository: TaskRepository,
) -> None:
    created = task_repository.create(title="Zadanie do ukończenia z próbą")
    task_repository.approve(created.id)
    task_repository.claim(created.id, worker_id="worker-complete")

    completed = task_repository.complete(
        created.id,
        reason="Wykonanie poprawnie zakończone",
    )
    attempts = _attempts_for_task(task_repository, created.id)

    assert completed.status is TaskStatus.COMPLETED
    assert len(attempts) == 1

    attempt = attempts[0]
    assert attempt.worker_id == "worker-complete"
    assert attempt.status == "completed"
    assert attempt.started_at is not None
    assert attempt.finished_at is not None
    assert attempt.error_summary is None


def test_block_closes_active_task_attempt_with_error_summary(
    task_repository: TaskRepository,
) -> None:
    created = task_repository.create(title="Zadanie do zablokowania z próbą")
    task_repository.approve(created.id)
    task_repository.claim(created.id, worker_id="worker-block")

    reason = "Brak wymaganych danych wejściowych"
    blocked = task_repository.block(created.id, reason=reason)
    attempts = _attempts_for_task(task_repository, created.id)

    assert blocked.status is TaskStatus.BLOCKED
    assert len(attempts) == 1

    attempt = attempts[0]
    assert attempt.worker_id == "worker-block"
    assert attempt.status == "blocked"
    assert attempt.started_at is not None
    assert attempt.finished_at is not None
    assert attempt.error_summary == reason


def test_repeated_claim_does_not_create_second_active_task_attempt(
    task_repository: TaskRepository,
) -> None:
    created = task_repository.create(title="Zadanie pobierane tylko raz")
    task_repository.approve(created.id)

    task_repository.claim(created.id, worker_id="worker-first")

    try:
        task_repository.claim(created.id, worker_id="worker-second")
    except TaskTransitionError:
        pass
    else:
        raise AssertionError("Powtórne claim() powinno zgłosić błąd")

    attempts = _attempts_for_task(task_repository, created.id)

    assert len(attempts) == 1
    assert attempts[0].worker_id == "worker-first"
    assert attempts[0].status == "started"
    assert attempts[0].finished_at is None
