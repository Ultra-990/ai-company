from fastapi.testclient import TestClient

from app.main import app


def test_project_progress_api_returns_dashboard_contract() -> None:
    with TestClient(app) as client:
        response = client.get("/api/project-progress")

    assert response.status_code == 200

    payload = response.json()

    project = payload.get("project")
    assert isinstance(project, dict)
    assert isinstance(project.get("id"), str)
    assert project["id"]
    assert isinstance(project.get("name"), str)
    assert project["name"]
    assert project.get("progress_method") == "weighted_checklist"
    assert isinstance(project.get("source_of_truth"), str)

    assert isinstance(payload.get("total_progress"), (int, float))
    assert 0 <= payload["total_progress"] <= 100

    assert isinstance(payload.get("phases"), list)
    assert payload["phases"]

    for phase in payload["phases"]:
        assert isinstance(phase.get("id"), str)
        assert phase["id"]
        assert isinstance(phase.get("name"), str)
        assert phase["name"]
        assert isinstance(phase.get("weight"), (int, float))
        assert phase["weight"] > 0
        assert isinstance(phase.get("status"), str)
        assert isinstance(phase.get("progress"), (int, float))
        assert 0 <= phase["progress"] <= 100
        assert isinstance(phase.get("depends_on"), list)
        assert isinstance(phase.get("items"), list)
        assert phase["items"]

        for item in phase["items"]:
            assert isinstance(item.get("id"), str)
            assert item["id"]
            assert isinstance(item.get("name"), str)
            assert item["name"]
            assert isinstance(item.get("status"), str)
            assert isinstance(item.get("progress"), (int, float))
            assert 0 <= item["progress"] <= 100
            assert item.get("evidence") is None or isinstance(
                item["evidence"], (str, list)
            )
            assert item.get("note") is None or isinstance(item["note"], str)
            assert item.get("status_source") in {
                "roadmap",
                "manual",
                "tasks",
            }

            task_summary = item.get("task_summary")
            assert task_summary is None or isinstance(task_summary, dict)
