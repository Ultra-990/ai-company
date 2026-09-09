from fastapi.testclient import TestClient

from app.main import app


def test_progress_page_uses_project_roadmap_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/progress")

    assert response.status_code == 200

    page = response.text

    assert 'fetch("/api/project-progress"' in page
    assert 'fetch("/api/progress"' not in page
    assert "location.reload" not in page
    assert 'setInterval(refreshProgressFromApi, 10000)' in page
