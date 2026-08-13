from pathlib import Path

import pytest

from app.services.project_progress import (
    ProgressConfigError,
    load_project_progress,
)


def test_load_project_progress_from_repository() -> None:
    data = load_project_progress()

    assert data["project"] == "Virtual Company"
    assert data["total_progress"] == 53
    assert len(data["stages"]) == 5


def test_organization_stage_is_completed() -> None:
    data = load_project_progress()

    organization = next(
        stage for stage in data["stages"]
        if stage["id"] == "organization"
    )

    assert organization["status"] == "completed"
    assert organization["progress"] == 100
    assert len(organization["items"]) == 5


def test_invalid_progress_is_rejected(tmp_path: Path) -> None:
    progress_file = tmp_path / "progress.yaml"
    progress_file.write_text(
        """
project: Test
stages:
  - id: example
    name: Example
    status: completed
    progress: 120
""",
        encoding="utf-8",
    )

    with pytest.raises(ProgressConfigError):
        load_project_progress(progress_file)


def test_invalid_status_is_rejected(tmp_path: Path) -> None:
    progress_file = tmp_path / "progress.yaml"
    progress_file.write_text(
        """
project: Test
stages:
  - id: example
    name: Example
    status: unknown
    progress: 0
""",
        encoding="utf-8",
    )

    with pytest.raises(ProgressConfigError):
        load_project_progress(progress_file)
