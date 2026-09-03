from __future__ import annotations

import pytest

from app.models.approval import ApprovalRequestStatus
from app.services.approvals import (
    ApprovalArgumentsMismatchError,
    ApprovalExecutionDeniedError,
    ApprovalRepository,
    build_tool_approval_preview,
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


def test_tool_request_uses_server_generated_preview(repository):
    secret_content = "TAJNA_TRESC_KTOREJ_NIE_WOLNO_POKAZAC"
    request = repository.create_tool_request(
        task_id=1,
        tool_name="write_project_file",
        arguments={
            "path": "reports/summary.txt",
            "content": secret_content,
        },
        description="Niewinny opis dostarczony przez agenta",
    )

    assert request.description.startswith("Zapis pliku projektu:")
    assert "reports/summary.txt" in request.description
    assert "operacja: utworzenie lub nadpisanie pliku" in request.description
    assert "rozmiar treści UTF-8:" in request.description
    assert secret_content not in request.description
    assert request.arguments_digest == canonical_arguments_digest(
        {
            "path": "reports/summary.txt",
            "content": secret_content,
        }
    )


def test_preview_is_deterministic_and_does_not_include_content():
    content = "sekret"
    preview = build_tool_approval_preview(
        "write_project_file",
        {"path": "notes.txt", "content": content},
    )

    assert preview == build_tool_approval_preview(
        " write_project_file ",
        {"content": content, "path": "notes.txt"},
    )
    assert content not in preview


def test_create_tool_request_does_not_use_generic_create(repository, monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("create_tool_request nie może wywoływać create()")

    monkeypatch.setattr(repository, "create", fail_if_called)

    request = repository.create_tool_request(
        task_id=1,
        tool_name="write_project_file",
        arguments={"path": "atomic.txt", "content": "tekst"},
        description="Opis klienta",
    )

    assert request.id > 0
    assert request.tool_name == "write_project_file"
    assert request.arguments_digest is not None


def test_unknown_tool_request_is_rejected(repository):
    with pytest.raises(ValueError):
        repository.create_tool_request(
            task_id=1,
            tool_name="unknown_high_risk_tool",
            arguments={},
            description="Opis klienta",
        )


def test_legacy_execute_tool_cannot_execute_approval_required_tool(
    repository,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        "app.tools.filesystem.permissions.project_root",
        lambda: tmp_path,
    )

    request = approved_write_request(
        repository,
        path="approved.txt",
        content="zatwierdzona treść",
    )

    with pytest.raises(
        PermissionError,
        match="wymaga zatwierdzonego serwerowego kontraktu wykonania",
    ):
        execute_tool(
            "write_project_file",
            approval_repository=repository,
            approval_request_id=request.id,
            path="approved.txt",
            content="zatwierdzona treść",
            approved=True,
        )


    assert not (tmp_path / "approved.txt").exists()
    assert repository.get_required(request.id).status is (
        ApprovalRequestStatus.APPROVED
    )
