from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.brain import get_orchestrator
from app.api.system import get_audit_repository
from app.api.tasks import get_repository
from app.main import app
from app.services.audit import AuditRepository
from app.services.tasks import TaskRepository


@pytest.fixture(autouse=True)
def isolate_database(tmp_path: Path) -> Generator[None, None, None]:
    """Zapewnia osobną bazę SQLite dla każdego testu."""

    database_url = f"sqlite:///{tmp_path / 'test.db'}"

    def override_task_repository() -> Generator[
        TaskRepository,
        None,
        None,
    ]:
        repository = TaskRepository(database_url)

        try:
            yield repository
        finally:
            repository.close()

    def override_audit_repository() -> Generator[
        AuditRepository,
        None,
        None,
    ]:
        repository = AuditRepository(database_url)

        try:
            yield repository
        finally:
            repository.close()

    get_audit_repository.cache_clear()

    app.dependency_overrides[get_repository] = override_task_repository
    app.dependency_overrides[get_audit_repository] = (
        override_audit_repository
    )

    try:
        yield
    finally:
        app.dependency_overrides.pop(get_repository, None)
        app.dependency_overrides.pop(get_audit_repository, None)
        get_audit_repository.cache_clear()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Klient dla testów korzystających z fixture `client`."""

    with TestClient(app) as test_client:
        yield test_client
