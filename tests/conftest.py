from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from app.api.system import get_audit_repository
from app.api.tasks import get_repository
from app.main import app
from app.services.audit import AuditRepository
from app.services.tasks import TaskRepository


@pytest.fixture(autouse=True)
def isolated_databases(
    tmp_path: Path,
) -> Iterator[None]:
    audit_database_path = tmp_path / "audit_test.sqlite3"
    task_database_path = tmp_path / "tasks_test.sqlite3"

    audit_repository = AuditRepository(
        f"sqlite:///{audit_database_path}",
    )
    task_repository = TaskRepository(
        f"sqlite:///{task_database_path}",
    )

    app.dependency_overrides[get_audit_repository] = (
        lambda: audit_repository
    )
    app.dependency_overrides[get_repository] = lambda: task_repository

    try:
        yield
    finally:
        app.dependency_overrides.pop(get_audit_repository, None)
        app.dependency_overrides.pop(get_repository, None)
        audit_repository.close()
        task_repository.close()
