from __future__ import annotations

from pathlib import Path

import pytest

from app.models.approval import ApprovalRequestStatus
from app.services.approvals import (
    ApprovalRepository,
    ApprovalRequestNotFoundError,
    ApprovalStateConflictError,
)
from app.services.audit import AuditRepository


@pytest.fixture
def approval_repositories(
    tmp_path: Path,
) -> tuple[ApprovalRepository, AuditRepository]:
    database_url = f"sqlite:///{tmp_path / 'approvals.sqlite3'}"

    approval_repository = ApprovalRepository(database_url)
    audit_repository = AuditRepository(database_url)

    try:
        yield approval_repository, audit_repository
    finally:
        audit_repository.close()
        approval_repository.close()


def test_create_and_get_pending_request(approval_repositories) -> None:
    repository, _ = approval_repositories

    request = repository.create(
        task_id=7,
        operation_type="send_email",
        description="Wysyłka raportu do właściciela",
    )

    assert request.id > 0
    assert request.task_id == 7
    assert request.operation_type == "send_email"
    assert request.description == "Wysyłka raportu do właściciela"
    assert request.status is ApprovalRequestStatus.PENDING
    assert request.resolved_at is None
    assert request.reason is None

    loaded = repository.get_required(request.id)

    assert loaded.id == request.id
    assert loaded.status is ApprovalRequestStatus.PENDING


def test_create_normalizes_text_and_lists_pending_requests(
    approval_repositories,
) -> None:
    repository, _ = approval_repositories

    first = repository.create(
        task_id=1,
        operation_type="  file_write  ",
        description="  Zapis pliku  ",
    )
    second = repository.create(
        task_id=2,
        operation_type="network_call",
        description="Wywołanie sieciowe",
    )

    pending = repository.list_pending()

    assert [request.id for request in pending] == [first.id, second.id]
    assert pending[0].operation_type == "file_write"
    assert pending[0].description == "Zapis pliku"


def test_approve_persists_resolution_and_audit_event(
    approval_repositories,
) -> None:
    repository, audit_repository = approval_repositories
    secret_description = "TAJNY_PAYLOAD_NIE_WOLNO_LOGOWAĆ"

    request = repository.create(
        task_id=10,
        operation_type="external_action",
        description=secret_description,
    )

    resolved = repository.approve(
        request.id,
        reason="Zatwierdzono po weryfikacji właściciela",
    )

    assert resolved.status is ApprovalRequestStatus.APPROVED
    assert resolved.resolved_at is not None
    assert resolved.reason == "Zatwierdzono po weryfikacji właściciela"
    assert repository.list_pending() == []

    events = audit_repository.list_recent(limit=10)

    assert len(events) == 1
    event = events[0]
    assert event.event_type == "approval_request"
    assert event.operation == "approved"
    assert event.decision == "approved"
    assert event.allowed is True
    assert f"approval_request_id={request.id}" in event.reason
    assert secret_description not in event.reason


@pytest.mark.parametrize(
    ("method_name", "expected_status"),
    [
        ("reject", ApprovalRequestStatus.REJECTED),
        ("expire", ApprovalRequestStatus.EXPIRED),
    ],
)
def test_reject_and_expire_persist_terminal_status(
    approval_repositories,
    method_name: str,
    expected_status: ApprovalRequestStatus,
) -> None:
    repository, audit_repository = approval_repositories

    request = repository.create(
        task_id=20,
        operation_type="restricted_action",
        description="Operacja wymagająca decyzji",
    )

    resolved = getattr(repository, method_name)(
        request.id,
        reason=f"Testowe rozstrzygnięcie: {method_name}",
    )

    assert resolved.status is expected_status
    assert resolved.resolved_at is not None
    assert resolved.reason == f"Testowe rozstrzygnięcie: {method_name}"

    events = audit_repository.list_recent(limit=10)
    assert events[0].operation == expected_status.value
    assert events[0].decision == expected_status.value
    assert events[0].allowed is False


def test_second_resolution_is_rejected_atomically(
    approval_repositories,
) -> None:
    repository, _ = approval_repositories

    request = repository.create(
        task_id=30,
        operation_type="delete_file",
        description="Usunięcie pliku",
    )

    repository.approve(request.id, reason="Pierwsza decyzja")

    with pytest.raises(ApprovalStateConflictError):
        repository.reject(request.id, reason="Druga decyzja")

    persisted = repository.get_required(request.id)
    assert persisted.status is ApprovalRequestStatus.APPROVED
    assert persisted.reason == "Pierwsza decyzja"


def test_missing_request_raises_not_found_error(
    approval_repositories,
) -> None:
    repository, _ = approval_repositories

    assert repository.get(99999) is None

    with pytest.raises(ApprovalRequestNotFoundError):
        repository.get_required(99999)

    with pytest.raises(ApprovalRequestNotFoundError):
        repository.approve(99999, reason="Brak wniosku")


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "task_id": 0,
            "operation_type": "operation",
            "description": "Opis",
        },
        {
            "task_id": 1,
            "operation_type": "   ",
            "description": "Opis",
        },
        {
            "task_id": 1,
            "operation_type": "operation",
            "description": "   ",
        },
        {
            "task_id": 1,
            "operation_type": "x" * 65,
            "description": "Opis",
        },
    ],
)
def test_create_validates_input(approval_repositories, kwargs) -> None:
    repository, _ = approval_repositories

    with pytest.raises(ValueError):
        repository.create(**kwargs)


def test_resolution_validates_reason(approval_repositories) -> None:
    repository, _ = approval_repositories

    request = repository.create(
        task_id=40,
        operation_type="operation",
        description="Opis",
    )

    with pytest.raises(ValueError):
        repository.approve(request.id, reason="   ")

    with pytest.raises(ValueError):
        repository.approve(request.id, reason="x" * 501)

    assert repository.get_required(request.id).status is (
        ApprovalRequestStatus.PENDING
    )


@pytest.mark.parametrize("limit", [0, 101])
def test_list_pending_validates_limit(approval_repositories, limit: int) -> None:
    repository, _ = approval_repositories

    with pytest.raises(ValueError):
        repository.list_pending(limit=limit)
