from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_safety_decision_is_saved_in_audit() -> None:
    check_response = client.get("/api/safety/check/read_only")

    assert check_response.status_code == 200

    audit_response = client.get("/api/audit/events")

    assert audit_response.status_code == 200

    events = audit_response.json()

    assert len(events) == 1
    assert events[0]["event_type"] == "safety_check"
    assert events[0]["operation"] == "read_only"
    assert events[0]["decision"] == "allowed"
    assert events[0]["allowed"] is True
    assert events[0]["reason"]


def test_blocked_decision_is_saved_in_audit() -> None:
    check_response = client.get("/api/safety/check/external_action")

    assert check_response.status_code == 200

    events = client.get("/api/audit/events").json()

    assert len(events) == 1
    assert events[0]["operation"] == "external_action"
    assert events[0]["decision"] == "blocked"
    assert events[0]["allowed"] is False


def test_unknown_operation_is_saved_as_rejected() -> None:
    check_response = client.get("/api/safety/check/not_valid")

    assert check_response.status_code == 400

    events = client.get("/api/audit/events").json()

    assert len(events) == 1
    assert events[0]["operation"] == "not_valid"
    assert events[0]["decision"] == "rejected"
    assert events[0]["allowed"] is False


def test_audit_limit_is_enforced() -> None:
    client.get("/api/safety/check/read_only")
    client.get("/api/safety/check/internal_write")
    client.get("/api/safety/check/external_action")

    response = client.get("/api/audit/events?limit=2")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_audit_limit_rejects_invalid_values() -> None:
    too_small = client.get("/api/audit/events?limit=0")
    too_large = client.get("/api/audit/events?limit=101")

    assert too_small.status_code == 422
    assert too_large.status_code == 422


def test_each_test_receives_an_empty_database() -> None:
    response = client.get("/api/audit/events")

    assert response.status_code == 200
    assert response.json() == []
