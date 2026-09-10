from pathlib import Path

from fastapi.testclient import TestClient

from app.api.progress import get_project_progress_service
from app.core.database import create_database_engine
from app.db.migrations import migrate_roadmap_item_state_schema
from app.main import app
from app.services.roadmap_progress import ProjectProgressService


def create_test_service(tmp_path: Path) -> ProjectProgressService:
    roadmap_path = tmp_path / "roadmap.yaml"
    roadmap_path.write_text(
        """
version: 1
project:
  id: test-project
  name: Test Project
  progress_method: weighted_checklist
  source_of_truth: transition_in_progress
phases:
  - id: first
    name: Pierwsza faza
    weight: 100
    items:
      - id: first.item
        name: Pierwszy punkt
        status: planned
""",
        encoding="utf-8",
    )

    database_url = f"sqlite:///{tmp_path / 'roadmap.sqlite3'}"
    engine = create_database_engine(database_url)

    try:
        migrate_roadmap_item_state_schema(engine)
    finally:
        engine.dispose()

    return ProjectProgressService(
        database_url,
        roadmap_path=roadmap_path,
    )


def test_patch_creates_override_and_changes_project_progress(
    tmp_path: Path,
) -> None:
    service = create_test_service(tmp_path)
    app.dependency_overrides[get_project_progress_service] = lambda: service

    try:
        with TestClient(app) as client:
            update_response = client.patch(
                "/api/roadmap-items/first.item",
                json={
                    "status": "completed",
                    "evidence": "tests/test_roadmap_item_state_api.py",
                    "note": "Punkt ukończony.",
                },
            )
            progress_response = client.get("/api/project-progress")

        assert update_response.status_code == 200
        assert update_response.json() == {
            "item_id": "first.item",
            "status": "completed",
            "evidence": "tests/test_roadmap_item_state_api.py",
            "note": "Punkt ukończony.",
        }

        assert progress_response.status_code == 200
        payload = progress_response.json()
        assert payload["total_progress"] == 100
        assert payload["phases"][0]["items"][0]["status"] == "completed"
    finally:
        app.dependency_overrides.pop(
            get_project_progress_service,
            None,
        )
        service.close()


def test_patch_updates_only_sent_fields(tmp_path: Path) -> None:
    service = create_test_service(tmp_path)
    app.dependency_overrides[get_project_progress_service] = lambda: service

    try:
        with TestClient(app) as client:
            first_response = client.patch(
                "/api/roadmap-items/first.item",
                json={
                    "status": "in_progress",
                    "evidence": "pierwotny-dowod",
                },
            )
            second_response = client.patch(
                "/api/roadmap-items/first.item",
                json={"note": "Dodana notatka."},
            )

        assert first_response.status_code == 200
        assert second_response.status_code == 200
        assert second_response.json() == {
            "item_id": "first.item",
            "status": "in_progress",
            "evidence": "pierwotny-dowod",
            "note": "Dodana notatka.",
        }
    finally:
        app.dependency_overrides.pop(
            get_project_progress_service,
            None,
        )
        service.close()


def test_patch_returns_404_for_unknown_roadmap_item(
    tmp_path: Path,
) -> None:
    service = create_test_service(tmp_path)
    app.dependency_overrides[get_project_progress_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.patch(
                "/api/roadmap-items/does.not.exist",
                json={"status": "completed"},
            )

        assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(
            get_project_progress_service,
            None,
        )
        service.close()


def test_patch_rejects_empty_payload(tmp_path: Path) -> None:
    service = create_test_service(tmp_path)
    app.dependency_overrides[get_project_progress_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.patch(
                "/api/roadmap-items/first.item",
                json={},
            )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(
            get_project_progress_service,
            None,
        )
        service.close()


def test_patch_rejects_invalid_status(tmp_path: Path) -> None:
    service = create_test_service(tmp_path)
    app.dependency_overrides[get_project_progress_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.patch(
                "/api/roadmap-items/first.item",
                json={"status": "done"},
            )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(
            get_project_progress_service,
            None,
        )
        service.close()
