import pytest

from app.models.task import Task


def test_task_stages_default_to_empty_list():
    task = Task(title="Task with stages")

    assert task.stages == []


def test_task_stages_accept_structured_stage_data():
    task = Task(
        title="Task with stages",
        stages=[
            {
                "id": "analysis",
                "name": "Analiza",
                "status": "planned",
                "progress": 0,
                "items": [],
            }
        ],
    )

    assert task.stages[0]["id"] == "analysis"
    assert task.stages[0]["status"] == "planned"


@pytest.mark.parametrize("invalid_progress", [-1, 101])
def test_task_stage_progress_must_be_between_zero_and_one_hundred(
    invalid_progress: int,
):
    task = Task(
        title="Invalid stage",
        stages=[
            {
                "id": "analysis",
                "name": "Analiza",
                "status": "planned",
                "progress": invalid_progress,
                "items": [],
            }
        ],
    )

    with pytest.raises(ValueError):
        task.validate_stages()


def test_invalid_task_stages_are_rejected_before_insert(tmp_path):
    from sqlalchemy.exc import StatementError

    from app.services.tasks import TaskRepository

    database_path = tmp_path / "tasks.db"
    repository = TaskRepository(f"sqlite:///{database_path}")

    try:
        task = Task(
            title="Invalid persisted task",
            stages=[
                {
                    "id": "analysis",
                    "name": "Analiza",
                    "status": "planned",
                    "progress": 101,
                    "items": [],
                }
            ],
        )

        with repository._session_factory() as session:
            session.add(task)

            with pytest.raises((ValueError, StatementError)):
                session.commit()

            session.rollback()
    finally:
        repository.close()


def test_valid_task_stages_can_be_persisted(tmp_path):
    from app.services.tasks import TaskRepository

    database_path = tmp_path / "valid-tasks.db"
    repository = TaskRepository(f"sqlite:///{database_path}")

    try:
        task = Task(
            title="Valid persisted task",
            stages=[
                {
                    "id": "analysis",
                    "name": "Analiza",
                    "status": "planned",
                    "progress": 0,
                    "items": [],
                }
            ],
        )

        with repository._session_factory() as session:
            session.add(task)
            session.commit()

        assert repository.get_required(task.id).stages[0]["id"] == "analysis"
    finally:
        repository.close()
