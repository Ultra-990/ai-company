from app.models.task import (
    ApprovalStatus,
    RiskLevel,
    Task,
    TaskPriority,
    TaskStatus,
)


def make_task() -> Task:
    return Task(
        title="Baseline task",
        description="Contract baseline",
        status=TaskStatus.PENDING,
        approval_status=ApprovalStatus.PENDING,
        priority=TaskPriority.NORMAL,
        risk_level=RiskLevel.LOW,
        progress=0,
        stages=[],
    )


def test_task_has_typed_status_fields():
    task = make_task()

    assert task.status is TaskStatus.PENDING
    assert task.approval_status is ApprovalStatus.PENDING
    assert task.risk_level is RiskLevel.LOW


def test_task_can_transition_to_in_progress():
    task = make_task()

    task.transition_to(TaskStatus.IN_PROGRESS)

    assert task.status is TaskStatus.IN_PROGRESS
    assert task.started_at is not None


def test_task_completion_sets_progress_and_timestamp():
    task = make_task()
    task.transition_to(TaskStatus.IN_PROGRESS)
    task.transition_to(TaskStatus.COMPLETED)

    assert task.status is TaskStatus.COMPLETED
    assert task.progress == 100
    assert task.completed_at is not None
