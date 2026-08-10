from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_system_status_returns_safe_defaults() -> None:
    response = client.get("/api/system/status")

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "AI Company"
    assert data["agents_enabled"] is False
    assert data["emergency_stop"] is False
    assert data["finance_mode"] == "simulation"
    assert data["external_actions_enabled"] is False
    assert data["financial_actions_enabled"] is False
    assert data["publishing_enabled"] is False
    assert data["audit_logging_enabled"] is True


def test_read_only_operation_is_allowed() -> None:
    response = client.get("/api/safety/check/read_only")

    assert response.status_code == 200

    data = response.json()

    assert data["operation"] == "read_only"
    assert data["decision"] == "allowed"
    assert data["allowed"] is True


def test_internal_write_requires_approval() -> None:
    response = client.get("/api/safety/check/internal_write")

    assert response.status_code == 200

    data = response.json()

    assert data["operation"] == "internal_write"
    assert data["decision"] == "approval_required"
    assert data["allowed"] is False


def test_external_action_is_blocked() -> None:
    response = client.get("/api/safety/check/external_action")

    assert response.status_code == 200

    data = response.json()

    assert data["decision"] == "blocked"
    assert data["allowed"] is False


def test_financial_action_is_blocked() -> None:
    response = client.get("/api/safety/check/financial_action")

    assert response.status_code == 200

    data = response.json()

    assert data["decision"] == "blocked"
    assert data["allowed"] is False


def test_publishing_is_blocked() -> None:
    response = client.get("/api/safety/check/publishing")

    assert response.status_code == 200

    data = response.json()

    assert data["decision"] == "blocked"
    assert data["allowed"] is False


def test_system_change_requires_approval() -> None:
    response = client.get("/api/safety/check/system_change")

    assert response.status_code == 200

    data = response.json()

    assert data["decision"] == "approval_required"
    assert data["allowed"] is False


def test_permanent_memory_change_requires_approval() -> None:
    response = client.get("/api/safety/check/memory_permanent_change")

    assert response.status_code == 200

    data = response.json()

    assert data["decision"] == "approval_required"
    assert data["allowed"] is False


def test_unknown_operation_is_rejected() -> None:
    response = client.get("/api/safety/check/unknown_operation")

    assert response.status_code == 400

    data = response.json()

    assert "detail" in data
    assert "Nieznany typ operacji" in data["detail"]
