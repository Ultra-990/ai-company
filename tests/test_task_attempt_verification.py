from hashlib import sha256

import pytest
from sqlalchemy import select

from app.models.task import TaskAttempt, TaskStatus
from app.services.tasks import TaskRepository


def _attempt_for_task(
    task_repository: TaskRepository,
    task_id: int,
) -> TaskAttempt:
    with task_repository._session_factory() as session:
        attempt = session.scalar(
            select(TaskAttempt)
            .where(TaskAttempt.task_id == task_id)
            .order_by(TaskAttempt.id.desc())
            .limit(1)
        )

        assert attempt is not None
        session.expunge(attempt)

    return attempt


def _claimed_task(task_repository: TaskRepository) -> int:
    task = task_repository.create(title="Zadanie z weryfikowanym wynikiem")
    task_repository.approve(task.id)
    task_repository.claim(task.id, worker_id="verification-worker")
    return task.id


def test_complete_requires_explicit_result_content(
    task_repository: TaskRepository,
) -> None:
    task_id = _claimed_task(task_repository)

    with pytest.raises(ValueError, match="Wynik wykonania jest wymagany"):
        task_repository.complete(
            task_id,
            reason="Wykonanie zakończone",
        )

    task = task_repository.get_required(task_id)
    attempt = _attempt_for_task(task_repository, task_id)

    assert task.status is TaskStatus.IN_PROGRESS
    assert attempt.status == "started"
    assert attempt.finished_at is None
    assert attempt.result_content is None
    assert attempt.result_checksum is None
    assert attempt.verification_status == "pending"
    assert attempt.verified_at is None


@pytest.mark.parametrize(
    "result_content",
    [
        "",
        "   ",
        "\n\t",
    ],
)
def test_complete_rejects_empty_result_content(
    task_repository: TaskRepository,
    result_content: str,
) -> None:
    task_id = _claimed_task(task_repository)

    with pytest.raises(ValueError, match="Wynik wykonania jest wymagany"):
        task_repository.complete(
            task_id,
            reason="Wykonanie zakończone",
            result_content=result_content,
        )

    assert (
        task_repository.get_required(task_id).status
        is TaskStatus.IN_PROGRESS
    )


def test_complete_persists_verified_result_and_checksum(
    task_repository: TaskRepository,
) -> None:
    task_id = _claimed_task(task_repository)
    reason = "Wynik sprawdzony i zaakceptowany przez wykonawcę"
    result_content = "Końcowy, trwały rezultat zadania."

    completed = task_repository.complete(
        task_id,
        reason=reason,
        result_content=result_content,
    )

    attempt = _attempt_for_task(task_repository, task_id)

    assert completed.status is TaskStatus.COMPLETED
    assert attempt.status == "completed"
    assert attempt.finished_at is not None
    assert attempt.error_summary is None

    assert attempt.result_content == result_content
    assert attempt.result_checksum == sha256(
        result_content.encode("utf-8")
    ).hexdigest()

    assert attempt.verification_status == "verified"
    assert attempt.verification_reason == reason
    assert attempt.verified_at is not None


def test_block_does_not_require_or_persist_result_content(
    task_repository: TaskRepository,
) -> None:
    task_id = _claimed_task(task_repository)

    blocked = task_repository.block(
        task_id,
        reason="Zewnętrzna usługa wykonawcza jest niedostępna",
    )

    attempt = _attempt_for_task(task_repository, task_id)

    assert blocked.status is TaskStatus.BLOCKED
    assert attempt.status == "blocked"
    assert attempt.error_summary == (
        "Zewnętrzna usługa wykonawcza jest niedostępna"
    )
    assert attempt.result_content is None
    assert attempt.result_checksum is None
    assert attempt.verification_status == "pending"
    assert attempt.verification_reason is None
    assert attempt.verified_at is None
