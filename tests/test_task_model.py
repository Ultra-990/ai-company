import pytest

from app.models.task import (
    Task,
    TaskPriority,
    TaskStatus,
    TaskTransitionError,
)


def make_task(
    status: TaskStatus = TaskStatus.PENDING,
) -> Task:
    return Task(
        title="Zadanie testowe",
        status=status,
        priority=TaskPriority.NORMAL,
    )


def test_pending_task_can_start() -> None:
    task = make_task()

    task.transition_to(TaskStatus.IN_PROGRESS)

    assert task.status is TaskStatus.IN_PROGRESS


def test_in_progress_task_can_be_completed() -> None:
    task = make_task(TaskStatus.IN_PROGRESS)

    task.transition_to(TaskStatus.COMPLETED)

    assert task.status is TaskStatus.COMPLETED


def test_blocked_task_can_return_to_in_progress() -> None:
    task = make_task(TaskStatus.BLOCKED)

    task.transition_to(TaskStatus.IN_PROGRESS)

    assert task.status is TaskStatus.IN_PROGRESS


@pytest.mark.parametrize(
    ("current_status", "new_status"),
    [
        (TaskStatus.PENDING, TaskStatus.COMPLETED),
        (TaskStatus.BLOCKED, TaskStatus.COMPLETED),
        (TaskStatus.COMPLETED, TaskStatus.IN_PROGRESS),
        (TaskStatus.CANCELLED, TaskStatus.PENDING),
        (TaskStatus.PENDING, TaskStatus.PENDING),
    ],
)
def test_invalid_transition_is_rejected(
    current_status: TaskStatus,
    new_status: TaskStatus,
) -> None:
    task = make_task(current_status)

    with pytest.raises(TaskTransitionError):
        task.transition_to(new_status)

    assert task.status is current_status


def test_update_progress_starts_pending_task_and_sets_timestamp() -> None:
    task = make_task()

    task.update_progress(1)

    assert task.status is TaskStatus.IN_PROGRESS
    assert task.started_at is not None
    assert task.completed_at is None
    assert task.updated_at == task.started_at


def test_update_progress_completes_pending_task_with_timestamps() -> None:
    task = make_task()

    task.update_progress(100)

    assert task.status is TaskStatus.COMPLETED
    assert task.started_at is not None
    assert task.completed_at is not None
    assert task.updated_at == task.started_at
    assert task.started_at == task.completed_at
