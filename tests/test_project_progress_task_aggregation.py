from pathlib import Path

from app.core.database import Base, create_database_engine
from app.models.roadmap import RoadmapItemState, RoadmapItemStatus
from app.models.task import Task, TaskStatus
from app.services.roadmap_progress import ProjectProgressService
from app.services.tasks import TaskRepository


def create_service(tmp_path: Path) -> ProjectProgressService:
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
  - id: delivery
    name: Dostarczanie
    weight: 100
    items:
      - id: delivery.automatic
        name: Automatycznie z zadań
        status: planned
      - id: delivery.manual
        name: Ręczny override
        status: planned
      - id: delivery.yaml
        name: Tylko YAML
        status: ready
""",
        encoding="utf-8",
    )

    database_url = f"sqlite:///{tmp_path / 'progress.sqlite3'}"
    engine = create_database_engine(database_url)

    try:
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()

    return ProjectProgressService(
        database_url,
        roadmap_path=roadmap_path,
    )


def test_tasks_automatically_define_roadmap_item_progress(
    tmp_path: Path,
) -> None:
    service = create_service(tmp_path)
    repository = TaskRepository(service._database_url)

    try:
        completed = repository.create(
            title="Ukończone zadanie",
            roadmap_item_id="delivery.automatic",
        )
        in_progress = repository.create(
            title="Trwające zadanie",
            roadmap_item_id="delivery.automatic",
        )

        with repository._session_factory() as session:
            completed_task = session.get(Task, completed.id)
            in_progress_task = session.get(Task, in_progress.id)

            assert completed_task is not None
            assert in_progress_task is not None

            completed_task.status = TaskStatus.COMPLETED
            completed_task.progress = 100
            in_progress_task.status = TaskStatus.IN_PROGRESS
            in_progress_task.progress = 50
            session.commit()

        progress = service.get_progress()
        items = progress["phases"][0]["items"]
        automatic = next(
            item for item in items if item["id"] == "delivery.automatic"
        )

        assert automatic["status"] == "in_progress"
        assert automatic["progress"] == 75
        assert automatic["status_source"] == "tasks"
        assert automatic["task_summary"] == {
            "total": 2,
            "completed": 1,
            "by_status": {
                "completed": 1,
                "in_progress": 1,
            },
        }
        assert "1/2 ukończonych" in automatic["evidence"]
    finally:
        repository.close()
        service.close()


def test_manual_override_has_priority_over_assigned_tasks(
    tmp_path: Path,
) -> None:
    service = create_service(tmp_path)
    repository = TaskRepository(service._database_url)

    try:
        task = repository.create(
            title="Zablokowane zadanie",
            roadmap_item_id="delivery.manual",
        )

        with repository._session_factory() as session:
            persisted_task = session.get(Task, task.id)
            assert persisted_task is not None
            persisted_task.status = TaskStatus.BLOCKED
            persisted_task.progress = 0
            session.add(
                RoadmapItemState(
                    item_id="delivery.manual",
                    status=RoadmapItemStatus.COMPLETED,
                    evidence="Ręcznie potwierdzone.",
                )
            )
            session.commit()

        progress = service.get_progress()
        items = progress["phases"][0]["items"]
        manual = next(
            item for item in items if item["id"] == "delivery.manual"
        )

        assert manual["status"] == "completed"
        assert manual["progress"] == 100
        assert manual["status_source"] == "manual"
        assert manual["task_summary"] is None
        assert manual["evidence"] == "Ręcznie potwierdzone."
    finally:
        repository.close()
        service.close()
