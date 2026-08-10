from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from app.api.system import get_audit_repository
from app.main import app
from app.services.audit import AuditRepository


@pytest.fixture(autouse=True)
def isolated_audit_database(
    tmp_path: Path,
) -> Iterator[AuditRepository]:
    database_path = tmp_path / "audit_test.sqlite3"
    repository = AuditRepository(
        f"sqlite:///{database_path}",
    )

    app.dependency_overrides[get_audit_repository] = lambda: repository

    try:
        yield repository
    finally:
        app.dependency_overrides.pop(get_audit_repository, None)
        repository.close()
