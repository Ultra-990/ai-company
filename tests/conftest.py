import os
os.environ.setdefault("OWNER_API_TOKEN", "test-owner-token")

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.system import get_audit_repository
from app.api.tasks import get_repository
from app.main import app
from app.services.audit import AuditRepository
from app.services.tasks import TaskRepository


@pytest.fixture(autouse=True)
def isolate_database(
    tmp_path: Path,
) -> Generator[TaskRepository, None, None]:
    """Zapewnia osobną bazę i wspólne repozytorium dla każdego testu."""

    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    task_repository = TaskRepository(database_url)
    audit_repository = AuditRepository(database_url)

    def override_task_repository() -> TaskRepository:
        return task_repository

    def override_audit_repository() -> AuditRepository:
        return audit_repository

    get_audit_repository.cache_clear()

    previous_task_override = app.dependency_overrides.get(get_repository)
    previous_audit_override = app.dependency_overrides.get(
        get_audit_repository
    )

    app.dependency_overrides[get_repository] = override_task_repository
    app.dependency_overrides[get_audit_repository] = (
        override_audit_repository
    )

    try:
        yield task_repository
    finally:
        if previous_task_override is None:
            app.dependency_overrides.pop(get_repository, None)
        else:
            app.dependency_overrides[get_repository] = (
                previous_task_override
            )

        if previous_audit_override is None:
            app.dependency_overrides.pop(get_audit_repository, None)
        else:
            app.dependency_overrides[get_audit_repository] = (
                previous_audit_override
            )

        get_audit_repository.cache_clear()
        audit_repository.close()
        task_repository.close()


@pytest.fixture
def task_repository(
    isolate_database: TaskRepository,
) -> TaskRepository:
    """Repozytorium używane jednocześnie przez test i endpoint."""

    return isolate_database


@pytest.fixture
def approved_task(task_repository: TaskRepository):
    """Tworzy zadanie gotowe do pobrania przez wykonawcę."""

    task = task_repository.create(
        title="Zadanie testowe do wykonania",
        description="Zadanie utworzone przez fixture approved_task",
    )

    return task_repository.approve(
        task.id,
        reason="Zatwierdzono zadanie do testowego wykonania",
    )


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Klient dla testów korzystających z fixture client."""

    with TestClient(app) as test_client:
        yield test_client
