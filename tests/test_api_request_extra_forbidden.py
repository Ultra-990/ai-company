from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.owner import require_owner
from app.main import app


@pytest.fixture
def approval_validation_client(client: TestClient):
    """
    Izoluje wyłącznie autoryzację właściciela.

    Testy celowo wysyłają niepoprawne body, dlatego nie powinny wykonywać
    operacji repozytorium ani zmieniać stanu zatwierdzeń.
    """
    sentinel = object()
    previous_override = app.dependency_overrides.get(require_owner, sentinel)
    app.dependency_overrides[require_owner] = lambda: None

    try:
        yield client
    finally:
        if previous_override is sentinel:
            app.dependency_overrides.pop(require_owner, None)
        else:
            app.dependency_overrides[require_owner] = previous_override


@pytest.mark.parametrize(
    ("method", "path", "payload", "uses_approval_client"),
    [
        (
            "post",
            "/api/approvals/1/approve",
            {"reason": "Zatwierdzono", "nieznane_pole": True},
            True,
        ),
        (
            "post",
            "/api/approvals/1/reject",
            {"reason": "Odrzucono", "nieznane_pole": True},
            True,
        ),
        (
            "post",
            "/api/tasks",
            {"title": "Zadanie kontraktowe", "nieznane_pole": True},
            False,
        ),
        (
            "patch",
            "/api/tasks/1/status",
            {"status": "pending", "nieznane_pole": True},
            False,
        ),
        (
            "patch",
            "/api/tasks/1/assignment",
            {"assigned_agent": "worker", "nieznane_pole": True},
            False,
        ),
        (
            "post",
            "/api/tasks/1/verify",
            {
                "result_content": "Wynik",
                "verifier_id": "verifier",
                "nieznane_pole": True,
            },
            False,
        ),
        (
            "post",
            "/api/brain/tasks",
            {"title": "Zadanie brain", "nieznane_pole": True},
            False,
        ),
        (
            "post",
            "/api/brain/safety-check",
            {
                "action_type": "deploy",
                "requires_approval": True,
                "nieznane_pole": True,
            },
            False,
        ),
    ],
)
def test_json_endpoints_reject_unknown_request_fields(
    client: TestClient,
    approval_validation_client: TestClient,
    method: str,
    path: str,
    payload: dict,
    uses_approval_client: bool,
) -> None:
    test_client = approval_validation_client if uses_approval_client else client

    response = getattr(test_client, method)(path, json=payload)

    assert response.status_code == 422

    errors = response.json()["detail"]
    assert any(
        error["type"] == "extra_forbidden"
        and error["loc"][-1] == "nieznane_pole"
        for error in errors
    )
