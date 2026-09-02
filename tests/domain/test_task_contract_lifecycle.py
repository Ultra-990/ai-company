import pytest

from app.domain import ContractError, TaskContract, TaskStatus


def make_failed_task(*, max_retries: int = 1) -> TaskContract:
    task = TaskContract("task-1", "Build feature", max_retries=max_retries)
    task.transition(TaskStatus.READY)
    task.transition(TaskStatus.RUNNING)
    task.transition(TaskStatus.FAILED)
    return task


def test_task_follows_complete_lifecycle() -> None:
    task = TaskContract("task-1", "Build feature")

    task.transition(TaskStatus.READY)
    task.transition(TaskStatus.RUNNING)
    task.transition(TaskStatus.SUCCEEDED)

    assert task.status is TaskStatus.SUCCEEDED


@pytest.mark.parametrize(
    ("initial", "target"),
    [
        (TaskStatus.PENDING, TaskStatus.RUNNING),
        (TaskStatus.PENDING, TaskStatus.SUCCEEDED),
        (TaskStatus.READY, TaskStatus.SUCCEEDED),
        (TaskStatus.RUNNING, TaskStatus.READY),
        (TaskStatus.SUCCEEDED, TaskStatus.FAILED),
        (TaskStatus.CANCELLED, TaskStatus.READY),
    ],
)
def test_invalid_transition_is_rejected(
    initial: TaskStatus,
    target: TaskStatus,
) -> None:
    task = TaskContract("task-1", "Build feature", status=initial)

    with pytest.raises(ContractError, match="Invalid task transition"):
        task.transition(target)


def test_retry_increments_count_and_returns_task_to_ready() -> None:
    task = make_failed_task(max_retries=2)

    task.retry()

    assert task.retry_count == 1
    assert task.status is TaskStatus.READY


def test_retry_cannot_exceed_limit() -> None:
    task = make_failed_task(max_retries=1)
    task.retry()
    task.transition(TaskStatus.RUNNING)
    task.transition(TaskStatus.FAILED)

    with pytest.raises(ContractError, match="Maximum retries exceeded"):
        task.retry()

    assert task.retry_count == 1
    assert task.status is TaskStatus.FAILED


@pytest.mark.parametrize(
    "status",
    [
        TaskStatus.PENDING,
        TaskStatus.READY,
        TaskStatus.RUNNING,
        TaskStatus.BLOCKED,
        TaskStatus.SUCCEEDED,
        TaskStatus.CANCELLED,
    ],
)
def test_only_failed_tasks_can_be_retried(status: TaskStatus) -> None:
    task = TaskContract("task-1", "Build feature", status=status, max_retries=1)

    with pytest.raises(ContractError, match="Only failed tasks can be retried"):
        task.retry()
