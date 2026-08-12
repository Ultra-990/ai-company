from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_progress_api_includes_project_progress() -> None:
    response = client.get("/api/progress")

    assert response.status_code == 200

    data = response.json()
    assert "project_progress" in data

    project_progress = data["project_progress"]

    assert project_progress["project"] == "Virtual Company"
    assert project_progress["total_progress"] == 53

    organization = next(
        stage
        for stage in project_progress["stages"]
        if stage["id"] == "organization"
    )

    assert organization["progress"] == 100
    assert organization["status"] == "completed"
