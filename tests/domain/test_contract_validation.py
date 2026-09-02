import pytest

from app.domain import (
    ApprovalRequestContract,
    ApprovalStatus,
    ContractError,
    TaskContract,
    TaskStatus,
)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"id": "", "title": "Build"},
        {"id": "t1", "title": ""},
        {"id": "t1", "title": "Build", "retry_count": -1},
        {"id": "t1", "title": "Build", "max_retries": -1},
        {"id": "t1", "title": "Build", "retry_count": 2, "max_retries": 1},
    ],
)
def test_task_rejects_invalid_constructor_values(kwargs):
    with pytest.raises(ContractError):
        TaskContract(**kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"id": "", "subject": "Deploy", "requested_by": "owner"},
        {"id": "a1", "subject": "", "requested_by": "owner"},
        {"id": "a1", "subject": "Deploy", "requested_by": ""},
    ],
)
def test_approval_rejects_invalid_constructor_values(kwargs):
    with pytest.raises(ContractError):
        ApprovalRequestContract(**kwargs)


def test_task_cannot_retry_before_failure():
    task = TaskContract("t1", "Build", max_retries=1)

    with pytest.raises(ContractError):
        task.retry()


def test_task_cannot_retry_after_retry_budget_is_exhausted():
    task = TaskContract("t1", "Build", max_retries=1)
    task.transition(TaskStatus.READY)
    task.transition(TaskStatus.RUNNING)
    task.transition(TaskStatus.FAILED)
    task.retry()
    task.transition(TaskStatus.RUNNING)
    task.transition(TaskStatus.FAILED)

    with pytest.raises(ContractError):
        task.retry()


def test_approved_request_can_expire_but_not_be_rejected():
    approval = ApprovalRequestContract("a1", "Deploy", "owner")
    approval.transition(ApprovalStatus.APPROVED)
    approval.transition(ApprovalStatus.EXPIRED)

    with pytest.raises(ContractError):
        approval.transition(ApprovalStatus.REJECTED)


def test_transition_requires_enum_value():
    task = TaskContract("t1", "Build")

    with pytest.raises(ContractError):
        task.transition("ready")  # type: ignore[arg-type]
