import os

# Testy zawsze działają na izolowanych, sztucznych tokenach.
# Nie mogą zależeć od OWNER_API_TOKEN / WORKER_API_TOKEN powłoki lub .env.
os.environ["OWNER_API_TOKEN"] = "test-owner-token"
os.environ["WORKER_API_TOKEN"] = "test-worker-token"

OWNER_HEADERS = {
    "Authorization": "Bearer " + os.environ["OWNER_API_TOKEN"]
}
WORKER_HEADERS = {
    "Authorization": "Bearer " + os.environ["WORKER_API_TOKEN"]
}

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.organization_os import get_organization_session
from app.api.system import get_audit_repository
from app.api.tasks import get_repository
from app.core.database import create_database_engine, create_session_factory
from app.db.migrations import (
    migrate_legacy_organization_os_taxonomy,
    migrate_organization_os_schema,
    seed_organization_os,
)
from app.main import app
from app.services.audit import AuditRepository
from app.services.tasks import TaskRepository


@pytest.fixture(autouse=True)
def isolate_database(
    tmp_path: Path,
    monkeypatch,
) -> Generator[TaskRepository, None, None]:
    """Zapewnia osobną bazę i wspólne repozytorium dla każdego testu."""

    monkeypatch.setattr("app.services.documentation.STATUS_FILE", tmp_path / "STATUS.md")

    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    task_repository = TaskRepository(database_url)
    audit_repository = AuditRepository(database_url)
    organization_engine = create_database_engine(database_url)
    # TestClient lifespan must migrate/seed only this fixture, never the live DB.
    monkeypatch.setattr('app.main.engine', organization_engine)
    migrate_organization_os_schema(organization_engine)
    migrate_legacy_organization_os_taxonomy(organization_engine)
    seed_organization_os(organization_engine)
    organization_session_factory = create_session_factory(
        organization_engine
    )

    def override_task_repository() -> TaskRepository:
        return task_repository

    def override_audit_repository() -> AuditRepository:
        return audit_repository

    def override_organization_session() -> Generator:
        with organization_session_factory() as session:
            yield session

    get_audit_repository.cache_clear()

    previous_task_override = app.dependency_overrides.get(get_repository)
    previous_audit_override = app.dependency_overrides.get(
        get_audit_repository
    )
    previous_organization_override = app.dependency_overrides.get(
        get_organization_session
    )

    app.dependency_overrides[get_repository] = override_task_repository
    app.dependency_overrides[get_audit_repository] = (
        override_audit_repository
    )
    app.dependency_overrides[get_organization_session] = (
        override_organization_session
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

        if previous_organization_override is None:
            app.dependency_overrides.pop(get_organization_session, None)
        else:
            app.dependency_overrides[get_organization_session] = (
                previous_organization_override
            )

        get_audit_repository.cache_clear()
        audit_repository.close()
        task_repository.close()
        organization_engine.dispose()


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
