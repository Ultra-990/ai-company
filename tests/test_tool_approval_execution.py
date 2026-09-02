from __future__ import annotations

import pytest

from app.models.approval import ApprovalRequestStatus
from app.services.approvals import (
    ApprovalArgumentsMismatchError,
    ApprovalExecutionDeniedError,
    ApprovalRepository,
    canonical_arguments_digest,
)
from app.tools.registry import execute_tool


@pytest.fixture
def repository(tmp_path):
    repo = ApprovalRepository(f"sqlite:///{tmp_path / 'approvals.db'}")
    try:
        yield repo
    finally:
        repo.close()


def approved_write_request(repository: ApprovalRepository, **arguments):
    request = repository.create_tool_request(
        task_id=1,
        tool_name="write_project_file",
        arguments=arguments,
        description="Testowy zapis pliku",
    )
    return repository.approve(request.id)


def test_digest_is_stable_for_key_order():
    assert canonical_arguments_digest(
        {"path": "a.txt", "content": "tekst"}
    ) == canonical_arguments_digest(
        {"content": "tekst", "path": "a.txt"}
    )


def test_consumption_is_single_use(repository):
    request = approved_write_request(
        repository,
        path="a.txt",
        content="tekst",
    )

    consumed = repository.consume_approved_request(
        request.id,
        tool_name="write_project_file",
        arguments_digest=canonical_arguments_digest(
            {"path": "a.txt", "content": "tekst"}
        ),
    )

    assert consumed.status is ApprovalRequestStatus.EXECUTED
    assert consumed.executed_at is not None

    with pytest.raises(ApprovalExecutionDeniedError):
        repository.consume_approved_request(
            request.id,
            tool_name="write_project_file",
            arguments_digest=canonical_arguments_digest(
                {"path": "a.txt", "content": "tekst"}
            ),
        )


def test_consumption_rejects_modified_arguments(repository):
    request = approved_write_request(
        repository,
        path="a.txt",
        content="zatwierdzone",
    )

    with pytest.raises(ApprovalArgumentsMismatchError):
        repository.consume_approved_request(
            request.id,
            tool_name="write_project_file",
            arguments_digest=canonical_arguments_digest(
                {"path": "a.txt", "content": "zmienione"}
            ),
        )


def test_write_requires_request_id():
    with pytest.raises(PermissionError):
        execute_tool(
            "write_project_file",
            path="phase1-never-created.txt",
            content="nie wolno",
        )


def test_old_approved_flag_does_not_bypass_approval():
    with pytest.raises(PermissionError):
        execute_tool(
            "write_project_file",
            approved=True,
            path="phase1-never-created.txt",
            content="nie wolno",
        )
