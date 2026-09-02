from pathlib import Path

import pytest

from app.tools.filesystem import list_project_files, read_project_file
from app.tools.permissions import ToolSecurityError


def test_read_project_file_reads_existing_project_file() -> None:
    content = read_project_file("app/tools/filesystem.py")
    assert "read_project_file" in content


def test_list_project_files_returns_directory_contents() -> None:
    files = list_project_files("app/tools")
    assert "filesystem.py" in files


def test_list_project_files_recursive_returns_relative_paths() -> None:
    files = list_project_files("app/tools", recursive=True)
    assert any(item.endswith("filesystem.py") for item in files)


def test_read_project_file_rejects_directory_traversal() -> None:
    with pytest.raises(ToolSecurityError):
        read_project_file("../../etc/passwd")


def test_read_project_file_rejects_absolute_path() -> None:
    with pytest.raises(ToolSecurityError):
        read_project_file("/etc/passwd")


def test_read_project_file_rejects_directory() -> None:
    with pytest.raises(ToolSecurityError):
        read_project_file("app")


def test_read_project_file_rejects_sensitive_file_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    secret = root / ".env"
    secret.write_text("SECRET=1", encoding="utf-8")

    monkeypatch.setattr("app.tools.permissions.project_root", lambda: root)

    with pytest.raises(ToolSecurityError):
        read_project_file(".env")


def test_read_project_file_enforces_size_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    big_file = root / "big.txt"
    big_file.write_text("x" * (1024 * 1024 + 1), encoding="utf-8")

    monkeypatch.setattr("app.tools.permissions.project_root", lambda: root)

    with pytest.raises(ToolSecurityError):
        read_project_file("big.txt")


def test_read_project_file_accepts_file_inside_project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    ok_file = root / "note.txt"
    ok_file.write_text("hello", encoding="utf-8")

    monkeypatch.setattr("app.tools.permissions.project_root", lambda: root)

    assert read_project_file("note.txt") == "hello"


def test_write_project_file_writes_allowed_text_file(tmp_path, monkeypatch):
    from app.tools.filesystem import write_project_file

    root = tmp_path / "project"
    root.mkdir()
    monkeypatch.setattr("app.tools.permissions.project_root", lambda: root)

    result = write_project_file("notes.txt", "hello")

    assert (root / "notes.txt").read_text(encoding="utf-8") == "hello"
    assert result["bytes_written"] == 5


def test_write_project_file_rejects_path_traversal(tmp_path, monkeypatch):
    from app.tools.filesystem import write_project_file

    root = tmp_path / "project"
    root.mkdir()
    monkeypatch.setattr("app.tools.permissions.project_root", lambda: root)

    with pytest.raises(ToolSecurityError):
        write_project_file("../outside.txt", "blocked")


@pytest.mark.parametrize(
    "path",
    [
        ".env",
        "credentials.txt",
        "id_rsa",
        "config.py",
        "settings.json",
    ],
)
def test_write_project_file_rejects_sensitive_or_protected_files(
    tmp_path,
    monkeypatch,
    path,
):
    from app.tools.filesystem import write_project_file

    root = tmp_path / "project"
    root.mkdir()
    monkeypatch.setattr("app.tools.permissions.project_root", lambda: root)

    with pytest.raises(ToolSecurityError):
        write_project_file(path, "blocked")


def test_write_project_file_rejects_oversized_content(tmp_path, monkeypatch):
    from app.tools.filesystem import MAX_WRITE_SIZE, write_project_file

    root = tmp_path / "project"
    root.mkdir()
    monkeypatch.setattr("app.tools.permissions.project_root", lambda: root)

    with pytest.raises(ToolSecurityError):
        write_project_file("large.txt", "x" * (MAX_WRITE_SIZE + 1))


def test_registry_requires_approval_for_write_tool():
    from app.tools.registry import get_tool

    tool = get_tool("write_project_file")

    assert tool.risk_level == "high"
    assert tool.requires_approval is True
