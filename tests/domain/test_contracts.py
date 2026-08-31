import pytest

from app.domain import (
    ApprovalRequestContract,
    ApprovalStatus,
    ContractError,
    TaskContract,
    TaskStatus,
)


def test_task_valid_transition_and_retry():
    task = TaskContract("t1", "Build", max_retries=1)
    task.transition(TaskStatus.READY)
    task.transition(TaskStatus.RUNNING)
    task.transition(TaskStatus.FAILED)
    task.retry()
    assert task.status == TaskStatus.READY
    assert task.retry_count == 1


def test_invalid_task_transition_is_blocked():
    task = TaskContract("t1", "Build")
    with pytest.raises(ContractError):
        task.transition(TaskStatus.SUCCEEDED)


def test_approval_transition():
    approval = ApprovalRequestContract("a1", "Deploy", "owner")
    approval.transition(ApprovalStatus.APPROVED)
    assert approval.status == ApprovalStatus.APPROVED
