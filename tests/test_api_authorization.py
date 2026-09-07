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
