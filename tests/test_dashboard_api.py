from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_dashboard_home_returns_aggregated_data():
    response = client.get("/api/dashboard")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert "project" in data
    assert "approvals" in data
    assert "tasks" in data
    assert "system" in data

    assert data["tasks"]["source"] == "task_repository"
    assert isinstance(data["approvals"]["total"], int)


def test_dashboard_summary_returns_project_progress():
    response = client.get("/api/dashboard/summary")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert isinstance(data["project"], str)
    assert isinstance(data["progress"], (int, float))
    assert "approvals" in data
    assert data["tasks"]["source"] == "task_repository"


def test_dashboard_endpoints_are_consistent():
    dashboard = client.get("/api/dashboard")
    summary = client.get("/api/dashboard/summary")

    assert dashboard.status_code == 200
    assert summary.status_code == 200

    dashboard_data = dashboard.json()
    summary_data = summary.json()

    assert summary_data["project"] == dashboard_data["project"]["name"]
    assert summary_data["progress"] == dashboard_data["project"]["total_progress"]
    assert summary_data["approvals"] == dashboard_data["approvals"]
