from __future__ import annotations

import pytest

from app.models.approval import ApprovalRequestStatus
from app.services.approved_tool_execution import (
    ApprovedToolExecutionService,
    PendingToolExecutionStore,
)
from app.services.approvals import (
    ApprovalExecutionDeniedError,
    ApprovalRepository,
)


@pytest.fixture
def repositories(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'approved-execution.sqlite3'}"
    approval_repository = ApprovalRepository(database_url)
    pending_store = PendingToolExecutionStore(database_url)

    try:
        yield approval_repository, pending_store
    finally:
        pending_store.close()
        approval_repository.close()


def create_approved_request(repository: ApprovalRepository):
    request = repository.create_tool_request(
        task_id=1,
        tool_name="write_project_file",
        arguments={
            "path": "reports/approved.txt",
            "content": "zatwierdzona treść",
        },
    )
    return repository.approve(request.id)


def test_execution_reads_arguments_only_from_persistent_store(
    repositories,
    tmp_path,
    monkeypatch,
):
    repository, pending_store = repositories
    monkeypatch.setattr(
        "app.tools.filesystem.permissions.project_root",
        lambda: tmp_path,
    )
    request = create_approved_request(repository)
    service = ApprovedToolExecutionService(repository, pending_store)
    (tmp_path / "reports").mkdir()

    service.execute(request.id)

    assert (tmp_path / "reports" / "approved.txt").read_text(
        encoding="utf-8"
    ) == "zatwierdzona treść"

    persisted = repository.get_required(request.id)
    assert persisted.status is ApprovalRequestStatus.EXECUTED
    assert persisted.executed_at is not None

    with pytest.raises(ApprovalExecutionDeniedError):
        pending_store.get_arguments(request.id)


def test_handler_failure_is_not_marked_as_executed(
    repositories,
    monkeypatch,
):
    repository, pending_store = repositories
    request = create_approved_request(repository)
    service = ApprovedToolExecutionService(repository, pending_store)

    def fail_write(**kwargs):
        raise OSError("sekretny szczegół awarii")

    monkeypatch.setattr(
        "app.services.approved_tool_execution.get_tool",
        lambda name: type(
            "FailingTool",
            (),
            {
                "requires_approval": True,
                "execute": staticmethod(fail_write),
            },
        )(),
    )

    with pytest.raises(OSError):
        service.execute(request.id)

    persisted = repository.get_required(request.id)
    assert persisted.status is ApprovalRequestStatus.EXECUTION_FAILED
    assert persisted.executed_at is None
    assert "sekretny szczegół" not in (persisted.reason or "")

    with pytest.raises(ApprovalExecutionDeniedError):
        pending_store.get_arguments(request.id)


def test_pending_request_cannot_be_executed(repositories):
    repository, pending_store = repositories
    request = repository.create_tool_request(
        task_id=1,
        tool_name="write_project_file",
        arguments={"path": "never.txt", "content": "nie wykonuj"},
    )
    service = ApprovedToolExecutionService(repository, pending_store)

    with pytest.raises(ApprovalExecutionDeniedError):
        service.execute(request.id)

    assert repository.get_required(request.id).status is (
        ApprovalRequestStatus.PENDING
    )


def test_second_execution_is_rejected(repositories, tmp_path, monkeypatch):
    repository, pending_store = repositories
    monkeypatch.setattr(
        "app.tools.filesystem.permissions.project_root",
        lambda: tmp_path,
    )
    request = create_approved_request(repository)
    service = ApprovedToolExecutionService(repository, pending_store)
    (tmp_path / "reports").mkdir()

    service.execute(request.id)

    with pytest.raises(ApprovalExecutionDeniedError):
        service.execute(request.id)

    assert repository.get_required(request.id).status is (
        ApprovalRequestStatus.EXECUTED
    )
