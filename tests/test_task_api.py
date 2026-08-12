from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_task_queue_full_lifecycle() -> None:
    create_response = client.post(
        "/api/tasks",
        json={
            "title": "  Przetwórz raport miesięczny  ",
            "description": "Analiza danych sprzedażowych",
            "priority": "high",
            "resource_class": "cpu_heavy",
            "risk_level": "high",
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()

    assert created["title"] == "Przetwórz raport miesięczny"
    assert created["status"] == "pending"
    assert created["priority"] == "high"
    assert created["resource_class"] == "cpu_heavy"
    assert created["risk_level"] == "high"
    assert created["assigned_agent"] is None
    assert created["queued_at"] is not None
    assert created["started_at"] is None
    assert created["completed_at"] is None
    assert created["created_at"] is not None
    assert created["updated_at"] is not None

    task_id = created["id"]

    get_response = client.get(f"/api/tasks/{task_id}")

    assert get_response.status_code == 200
    assert get_response.json()["id"] == task_id

    assignment_response = client.patch(
        f"/api/tasks/{task_id}/assignment",
        json={"assigned_agent": " analyst "},
    )

    assert assignment_response.status_code == 200
    assert assignment_response.json()["assigned_agent"] == "analyst"

    started_response = client.patch(
        f"/api/tasks/{task_id}/status",
        json={"status": "in_progress"},
    )

    assert started_response.status_code == 200
    assert started_response.json()["status"] == "in_progress"
    assert started_response.json()["started_at"] is not None

    completed_response = client.patch(
        f"/api/tasks/{task_id}/status",
        json={"status": "completed"},
    )

    assert completed_response.status_code == 200
    completed = completed_response.json()

    assert completed["status"] == "completed"
    assert completed["completed_at"] is not None


def test_list_tasks_filters_by_resource_class_and_risk_level() -> None:
    matching_response = client.post(
        "/api/tasks",
        json={
            "title": "Zadanie wymagające CPU",
            "resource_class": "cpu_heavy",
            "risk_level": "high",
        },
    )
    assert matching_response.status_code == 201

    other_response = client.post(
        "/api/tasks",
        json={
            "title": "Lekkie zadanie",
            "resource_class": "light",
            "risk_level": "low",
        },
    )
    assert other_response.status_code == 201

    response = client.get(
        "/api/tasks",
        params={
            "resource_class": "cpu_heavy",
            "risk_level": "high",
        },
    )

    assert response.status_code == 200
    tasks = response.json()

    assert len(tasks) == 1
    assert tasks[0]["id"] == matching_response.json()["id"]


def test_get_missing_task_returns_404() -> None:
    response = client.get("/api/tasks/999999")

    assert response.status_code == 404
    assert "Nie znaleziono zadania" in response.json()["detail"]
