from fastapi.testclient import TestClient


OWNER_HEADERS = {"Authorization": "Bearer test-owner-token"}
WORKER_HEADERS = {"Authorization": "Bearer test-worker-token"}


def test_public_task_list_does_not_require_token(client: TestClient) -> None:
    response = client.get("/api/tasks")

    assert response.status_code == 200


def test_task_creation_without_token_returns_401(client: TestClient) -> None:
    response = client.post(
        "/api/tasks",
        json={"title": "Zadanie bez tokenu"},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_worker_cannot_create_task(client: TestClient) -> None:
    response = client.post(
        "/api/tasks",
        headers=WORKER_HEADERS,
        json={"title": "Zadanie workera"},
    )

    assert response.status_code == 403


def test_owner_can_create_task(client: TestClient) -> None:
    response = client.post(
        "/api/tasks",
        headers=OWNER_HEADERS,
        json={"title": "Zadanie właściciela"},
    )

    assert response.status_code == 201


def test_execute_next_without_token_returns_401(client: TestClient) -> None:
    response = client.post("/api/tasks/execute-next")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_owner_cannot_execute_next(client: TestClient) -> None:
    response = client.post(
        "/api/tasks/execute-next",
        headers=OWNER_HEADERS,
    )

    assert response.status_code == 403


def test_worker_can_execute_next(client: TestClient) -> None:
    response = client.post(
        "/api/tasks/execute-next",
        headers=WORKER_HEADERS,
    )

    assert response.status_code == 204


def test_brain_mutation_requires_owner(client: TestClient) -> None:
    response = client.post(
        "/api/brain/tasks",
        json={"title": "Zadanie brain bez tokenu"},
    )

    assert response.status_code == 401


def test_worker_cannot_run_brain_safety_check(client: TestClient) -> None:
    response = client.post(
        "/api/brain/safety-check",
        headers=WORKER_HEADERS,
        json={
            "action_type": "deploy",
            "requires_approval": True,
        },
    )

    assert response.status_code == 403


def test_missing_token_is_saved_without_authorization_value(
    client: TestClient,
) -> None:
    secret = "super-secret-owner-token"

    response = client.post(
        "/api/tasks",
        headers={"Authorization": f"Bearer {secret}"},
        json={"title": "Niedozwolone zadanie"},
    )

    assert response.status_code == 401

    events = client.get("/api/audit/events").json()

    assert len(events) == 1
    assert events[0]["event_type"] == "api_authorization"
    assert events[0]["operation"] == "owner"
    assert events[0]["decision"] == "denied"
    assert events[0]["allowed"] is False
    assert events[0]["reason"] == "invalid_token"

    serialized_events = str(events)
    assert secret not in serialized_events
    assert "Authorization" not in serialized_events
    assert "Bearer " not in serialized_events


def test_wrong_role_is_saved_as_forbidden_without_token(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/tasks",
        headers=WORKER_HEADERS,
        json={"title": "Zadanie niedozwolone dla workera"},
    )

    assert response.status_code == 403

    events = client.get("/api/audit/events").json()

    assert len(events) == 1
    assert events[0]["event_type"] == "api_authorization"
    assert events[0]["operation"] == "owner"
    assert events[0]["decision"] == "denied"
    assert events[0]["allowed"] is False
    assert events[0]["reason"] == "insufficient_role"

    serialized_events = str(events)
    assert "test-worker-token" not in serialized_events
    assert "Authorization" not in serialized_events
    assert "Bearer " not in serialized_events


def test_successful_owner_mutation_is_audited_after_completion(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/tasks",
        headers=OWNER_HEADERS,
        json={"title": "Zadanie do audytu"},
    )

    assert response.status_code == 201

    events = client.get("/api/audit/events").json()

    assert len(events) == 1
    assert events[0]["event_type"] == "api_mutation"
    assert events[0]["operation"] == "POST /api/tasks"
    assert events[0]["decision"] == "completed"
    assert events[0]["allowed"] is True
    assert events[0]["reason"] == "owner"

    serialized_events = str(events)
    assert "test-owner-token" not in serialized_events
    assert "Authorization" not in serialized_events
    assert "Bearer " not in serialized_events


def test_failed_authorized_mutation_is_not_recorded_as_completed(
    client: TestClient,
) -> None:
    response = client.patch(
        "/api/tasks/999999/status",
        headers=OWNER_HEADERS,
        json={"status": "in_progress"},
    )

    assert response.status_code == 404
    assert client.get("/api/audit/events").json() == []
