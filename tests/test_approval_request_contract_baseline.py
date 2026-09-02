import pytest

from app.models.approval import ApprovalRequest, ApprovalRequestStatus


def test_approval_request_has_expected_fields():
    approval = ApprovalRequest(
        task_id=1,
        operation_type="tool_call",
        description="Test approval",
    )

    assert approval.task_id == 1
    assert approval.operation_type == "tool_call"
    assert approval.description == "Test approval"
    assert approval.status == ApprovalRequestStatus.PENDING


def test_approval_request_status_is_pending_by_default():
    approval = ApprovalRequest(
        task_id=1,
        operation_type="tool_call",
        description="Test approval",
    )

    assert approval.status == ApprovalRequestStatus.PENDING


@pytest.mark.parametrize(
    "status",
    [
        ApprovalRequestStatus.PENDING,
        ApprovalRequestStatus.APPROVED,
        ApprovalRequestStatus.REJECTED,
    ],
)
def test_approval_request_accepts_supported_statuses(status):
    approval = ApprovalRequest(
        task_id=1,
        operation_type="tool_call",
        description="Test approval",
        status=status,
    )

    assert approval.status == status
