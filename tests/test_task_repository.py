from pathlib import Path

import pytest

from app.models.task import (
    TaskPriority,
    TaskStatus,
    TaskTransitionError,
)
from app.services.tasks import (
    TaskNotFoundError,
    TaskRepository,
)


@pytest.fixture
def task_repository(tmp_path: Path):
    database_path = tmp_path / "tasks_test.sqlite3"
    repository = TaskRepository(
        f"sqlite:///{database_path}",
    )

    try:
        yield repository
    finally:
        repository.close()


def test_create_and_read_task(
    task_repository: TaskRepository,
) -> None:
    created = task_repository.create(
        title="  Przygotuj raport  ",
        description="Raport tygodniowy",
        priority=TaskPriority.HIGH,
        assigned_agent=" analyst ",
    )

    loaded = task_repository.get(created.id)

    assert loaded is not None
    assert loaded.title == "Przygotuj raport"
    assert loaded.description == "Raport tygodniowy"
    assert loaded.status is TaskStatus.PENDING
    assert loaded.priority is TaskPriority.HIGH
    assert loaded.assigned_agent == "analyst"
    assert loaded.created_at is not None
    assert loaded.updated_at is not None


def test_empty_title_is_rejected(
    task_repository: TaskRepository,
) -> None:
    with pytest.raises(ValueError, match="nie może być pusty"):
        task_repository.create(title="   ")


def test_transition_is_persisted(
    task_repository: TaskRepository,
) -> None:
    created = task_repository.create(title="Wykonaj analizę")

    started = task_repository.transition(
        created.id,
        TaskStatus.IN_PROGRESS,
    )
    loaded = task_repository.get_required(created.id)

    assert started.status is TaskStatus.IN_PROGRESS
    assert loaded.status is TaskStatus.IN_PROGRESS


def test_invalid_transition_does_not_change_database(
    task_repository: TaskRepository,
) -> None:
    created = task_repository.create(title="Wykonaj analizę")

    with pytest.raises(TaskTransitionError):
        task_repository.transition(
            created.id,
            TaskStatus.COMPLETED,
        )

    loaded = task_repository.get_required(created.id)
    assert loaded.status is TaskStatus.PENDING


def test_missing_task_raises_domain_error(
    task_repository: TaskRepository,
) -> None:
    with pytest.raises(TaskNotFoundError):
        task_repository.transition(
            999999,
            TaskStatus.IN_PROGRESS,
        )


def test_list_recent_respects_limit(
    task_repository: TaskRepository,
) -> None:
    first = task_repository.create(title="Pierwsze zadanie")
    second = task_repository.create(title="Drugie zadanie")

    tasks = task_repository.list_recent(limit=1)

    assert len(tasks) == 1
    assert tasks[0].id == second.id
    assert tasks[0].id != first.id


@pytest.mark.parametrize("limit", [0, 101])
def test_list_recent_rejects_invalid_limit(
    task_repository: TaskRepository,
    limit: int,
) -> None:
    with pytest.raises(ValueError):
        task_repository.list_recent(limit=limit)
