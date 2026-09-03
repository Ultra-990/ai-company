from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.tools.filesystem import read_project_file, write_project_file
from app.tools.permissions import ToolSecurityError


def test_read_blocks_symlink_pointing_outside_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()

    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")

    link = root / "outside-link.txt"
    os.symlink(outside, link)

    monkeypatch.setattr("app.tools.permissions.project_root", lambda: root)

    with pytest.raises(ToolSecurityError):
        read_project_file("outside-link.txt")


def test_write_blocks_symlink_pointing_outside_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()

    outside = tmp_path / "outside.txt"
    outside.write_text("original", encoding="utf-8")

    link = root / "outside-link.txt"
    os.symlink(outside, link)

    monkeypatch.setattr("app.tools.permissions.project_root", lambda: root)

    with pytest.raises(ToolSecurityError):
        write_project_file("outside-link.txt", "modified")

    assert outside.read_text(encoding="utf-8") == "original"


def test_write_allows_internal_symlink_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()

    target = root / "target.txt"
    target.write_text("original", encoding="utf-8")

    link = root / "internal-link.txt"
    os.symlink(target.name, link)

    monkeypatch.setattr("app.tools.permissions.project_root", lambda: root)

    write_project_file("internal-link.txt", "updated")

    assert target.read_text(encoding="utf-8") == "updated"
