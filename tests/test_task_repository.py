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


def test_list_recent_filters_tasks_by_status_priority_and_agent(
    task_repository: TaskRepository,
) -> None:
    matching = task_repository.create(
        title="Pasujące zadanie",
        priority=TaskPriority.HIGH,
        assigned_agent="analyst",
    )
    task_repository.transition(
        matching.id,
        TaskStatus.IN_PROGRESS,
    )

    task_repository.create(
        title="Inny status",
        priority=TaskPriority.HIGH,
        assigned_agent="analyst",
    )
    task_repository.create(
        title="Inny priorytet",
        priority=TaskPriority.LOW,
        assigned_agent="analyst",
    )
    task_repository.create(
        title="Inny agent",
        priority=TaskPriority.HIGH,
        assigned_agent="writer",
    )

    tasks = task_repository.list_recent(
        status=TaskStatus.IN_PROGRESS,
        priority=TaskPriority.HIGH,
        assigned_agent=" analyst ",
    )

    assert [task.id for task in tasks] == [matching.id]


def test_assign_sets_and_removes_agent(
    task_repository: TaskRepository,
) -> None:
    created = task_repository.create(title="Przypisz zadanie")

    assigned = task_repository.assign(created.id, " analyst ")
    assert assigned.assigned_agent == "analyst"
    assert (
        task_repository.get_required(created.id).assigned_agent
        == "analyst"
    )

    unassigned = task_repository.assign(created.id, "   ")
    assert unassigned.assigned_agent is None
    assert task_repository.get_required(created.id).assigned_agent is None


def test_assign_rejects_agent_name_longer_than_100_characters(
    task_repository: TaskRepository,
) -> None:
    created = task_repository.create(title="Przypisz zadanie")

    with pytest.raises(ValueError, match="100 znaków"):
        task_repository.assign(created.id, "a" * 101)

    assert task_repository.get_required(created.id).assigned_agent is None


def test_assign_raises_error_for_missing_task(
    task_repository: TaskRepository,
) -> None:
    with pytest.raises(TaskNotFoundError):
        task_repository.assign(999999, "analyst")


def test_list_recent_rejects_blank_agent_filter(
    task_repository: TaskRepository,
) -> None:
    with pytest.raises(ValueError, match="nie może być pusty"):
        task_repository.list_recent(assigned_agent="   ")
