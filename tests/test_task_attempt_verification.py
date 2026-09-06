from hashlib import sha256

import pytest
from sqlalchemy import select

from app.models.audit import AuditEvent
from app.models.task import TaskAttempt, TaskStatus, TaskTransitionError
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


def _completed_task(
    task_repository: TaskRepository,
    result_content: str = "Końcowy, trwały rezultat zadania.",
) -> int:
    task_id = _claimed_task(task_repository)
    task_repository.complete(
        task_id,
        reason="Wykonanie zakończone",
        result_content=result_content,
    )
    return task_id


def test_complete_requires_explicit_result_content(
    task_repository: TaskRepository,
) -> None:
    task_id = _claimed_task(task_repository)

    with pytest.raises(ValueError, match="Wynik wykonania jest wymagany"):
        task_repository.complete(task_id, reason="Wykonanie zakończone")

    task = task_repository.get_required(task_id)
    attempt = _attempt_for_task(task_repository, task_id)

    assert task.status is TaskStatus.IN_PROGRESS
    assert attempt.status == "started"
    assert attempt.result_content is None
    assert attempt.result_checksum is None
    assert attempt.verification_status == "pending"
    assert attempt.verified_at is None


@pytest.mark.parametrize("result_content", ["", "   ", "\n\t"])
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

    assert task_repository.get_required(task_id).status is TaskStatus.IN_PROGRESS


def test_complete_persists_pending_result_and_checksum(
    task_repository: TaskRepository,
) -> None:
    task_id = _completed_task(task_repository)
    result_content = "Końcowy, trwały rezultat zadania."
    attempt = _attempt_for_task(task_repository, task_id)

    assert attempt.status == "completed"
    assert attempt.finished_at is not None
    assert attempt.result_content == result_content
    assert attempt.result_checksum == sha256(
        result_content.encode("utf-8")
    ).hexdigest()
    assert attempt.verification_status == "pending"
    assert attempt.verification_reason is None
    assert attempt.verified_at is None


def test_verify_attempt_accepts_matching_result_and_records_audit(
    task_repository: TaskRepository,
) -> None:
    result_content = "Końcowy, trwały rezultat zadania."
    task_id = _completed_task(task_repository, result_content)

    attempt = task_repository.verify_attempt(
        task_id,
        result_content=result_content,
        verifier_id="owner-1",
        reason="Kontrola integralności zakończona powodzeniem",
    )

    assert attempt.verification_status == "verified"
    assert attempt.verification_reason == (
        "Kontrola integralności zakończona powodzeniem"
    )
    assert attempt.verified_at is not None

    with task_repository._session_factory() as session:
        event = session.scalar(
            select(AuditEvent)
            .where(AuditEvent.event_type == "task_verification")
            .order_by(AuditEvent.id.desc())
            .limit(1)
        )
        assert event is not None
        assert event.operation == "verify"
        assert event.decision == "verified"
        assert event.allowed is True
        assert "verifier_id=owner-1" in event.reason


def test_verify_attempt_rejects_mismatched_result(
    task_repository: TaskRepository,
) -> None:
    task_id = _completed_task(task_repository)

    attempt = task_repository.verify_attempt(
        task_id,
        result_content="Treść zmieniona po wykonaniu zadania",
        verifier_id="owner-1",
        reason="Kontrola integralności",
    )

    assert attempt.verification_status == "rejected"
    assert "nie odpowiada" in (attempt.verification_reason or "")
    assert attempt.verified_at is not None
    assert task_repository.get_required(task_id).status is TaskStatus.COMPLETED


def test_verify_attempt_cannot_be_repeated(
    task_repository: TaskRepository,
) -> None:
    result_content = "Końcowy, trwały rezultat zadania."
    task_id = _completed_task(task_repository, result_content)

    task_repository.verify_attempt(
        task_id,
        result_content=result_content,
        verifier_id="owner-1",
    )

    with pytest.raises(TaskTransitionError, match="została już zweryfikowana"):
        task_repository.verify_attempt(
            task_id,
            result_content=result_content,
            verifier_id="owner-2",
        )


def test_verify_attempt_requires_completed_attempt(
    task_repository: TaskRepository,
) -> None:
    task_id = _claimed_task(task_repository)

    with pytest.raises(TaskTransitionError, match="ukończonej próby"):
        task_repository.verify_attempt(
            task_id,
            result_content="Wynik",
            verifier_id="owner-1",
        )


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
    assert attempt.result_content is None
    assert attempt.result_checksum is None
    assert attempt.verification_status == "pending"
    assert attempt.verification_reason is None
    assert attempt.verified_at is None
