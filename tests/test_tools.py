from pathlib import Path

import pytest

from app.tools.audit import audit_tool_call
from app.tools.filesystem import list_project_files, read_project_file
from app.tools.permissions import ToolSecurityError


def test_read_project_file_reads_existing_project_file():
    content = read_project_file("app/tools/base.py")
    assert "class Tool" in content


def test_read_project_file_rejects_directory_traversal():
    with pytest.raises(ToolSecurityError):
        read_project_file("../../etc/passwd")


def test_read_project_file_rejects_absolute_path():
    with pytest.raises(ToolSecurityError):
        read_project_file("/etc/passwd")


def test_read_project_file_rejects_directory():
    with pytest.raises(ToolSecurityError):
        read_project_file("app")


def test_read_project_file_enforces_size_limit():
    with pytest.raises(ToolSecurityError):
        read_project_file("app/tools/base.py", max_bytes=1)


def test_list_project_files_returns_relative_paths():
    files = list_project_files("app/tools", recursive=True)

    assert "app/tools/base.py" in files
    assert all(not Path(item).is_absolute() for item in files)
    assert all("__pycache__" not in item for item in files)


def test_audit_log_is_written(tmp_path):
    audit_path = tmp_path / "audit.jsonl"

    audit_tool_call(
        "test_tool",
        status="success",
        arguments={"value": 1},
        audit_path=audit_path,
    )

    content = audit_path.read_text(encoding="utf-8")
    assert '"tool": "test_tool"' in content
    assert '"status": "success"' in content
