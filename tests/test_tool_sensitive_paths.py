from __future__ import annotations

from pathlib import Path

import pytest

from app.tools.filesystem import (
    list_project_files,
    read_project_file,
    write_project_file,
)
from app.tools.permissions import ToolSecurityError


@pytest.mark.parametrize(
    "path",
    [
        ".env.test",
        ".env.staging",
        "nested/.env.backup",
    ],
)
def test_read_project_file_rejects_all_dotenv_variants(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()

    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("SECRET=1", encoding="utf-8")

    monkeypatch.setattr("app.tools.permissions.project_root", lambda: root)

    with pytest.raises(ToolSecurityError):
        read_project_file(path)


@pytest.mark.parametrize("path", [".env.test", "nested/.env.staging"])
def test_write_project_file_rejects_all_dotenv_variants(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "nested").mkdir()

    monkeypatch.setattr("app.tools.permissions.project_root", lambda: root)

    with pytest.raises(ToolSecurityError):
        write_project_file(path, "SECRET=1")


def test_backups_directory_is_hidden_and_inaccessible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()

    backups = root / "backups"
    backups.mkdir()
    (backups / "database-copy.txt").write_text("SECRET=1", encoding="utf-8")

    monkeypatch.setattr("app.tools.permissions.project_root", lambda: root)

    assert "backups" not in list_project_files()

    with pytest.raises(ToolSecurityError):
        list_project_files("backups")

    with pytest.raises(ToolSecurityError):
        read_project_file("backups/database-copy.txt")
