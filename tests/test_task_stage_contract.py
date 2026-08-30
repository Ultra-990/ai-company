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
