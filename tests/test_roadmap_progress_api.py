from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.progress import get_project_progress_service
from app.core.database import create_database_engine
from app.db.migrations import migrate_roadmap_item_state_schema
from app.main import app
from app.models.roadmap import RoadmapItemState, RoadmapItemStatus
from app.services.roadmap_progress import ProjectProgressService


def test_project_progress_uses_yaml_defaults_and_database_overrides(
    tmp_path: Path,
) -> None:
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
    weight: 75
    items:
      - id: first.default_completed
        name: Domyślnie ukończony
        status: completed
      - id: first.overridden
        name: Nadpisany przez SQLite
        status: planned
  - id: second
    name: Druga faza
    weight: 25
    items:
      - id: second.planned
        name: Zaplanowany
        status: planned
""",
        encoding="utf-8",
    )

    database_url = f"sqlite:///{tmp_path / 'roadmap.sqlite3'}"
    engine = create_database_engine(database_url)
    migrate_roadmap_item_state_schema(engine)

    try:
        with Session(engine) as session:
            session.add(
                RoadmapItemState(
                    item_id="first.overridden",
                    status=RoadmapItemStatus.COMPLETED,
                    evidence="tests/test_roadmap_progress_api.py",
                    note="Stan nadpisany z SQLite.",
                )
            )
            session.commit()
    finally:
        engine.dispose()

    service = ProjectProgressService(
        database_url,
        roadmap_path=roadmap_path,
    )

    app.dependency_overrides[get_project_progress_service] = (
        lambda: service
    )

    try:
        with TestClient(app) as client:
            response = client.get("/api/project-progress")

        assert response.status_code == 200

        data = response.json()

        assert data["project"]["id"] == "test-project"
        assert data["project"]["name"] == "Test Project"
        assert data["total_progress"] == 75

        first_phase = next(
            phase for phase in data["phases"] if phase["id"] == "first"
        )
        assert first_phase["progress"] == 100
        assert first_phase["status"] == "completed"

        overridden_item = next(
            item
            for item in first_phase["items"]
            if item["id"] == "first.overridden"
        )
        assert overridden_item["status"] == "completed"
        assert overridden_item["progress"] == 100
        assert overridden_item["evidence"] == (
            "tests/test_roadmap_progress_api.py"
        )
        assert overridden_item["note"] == "Stan nadpisany z SQLite."

        second_phase = next(
            phase for phase in data["phases"] if phase["id"] == "second"
        )
        assert second_phase["progress"] == 0
        assert second_phase["status"] == "planned"
    finally:
        app.dependency_overrides.pop(
            get_project_progress_service,
            None,
        )
