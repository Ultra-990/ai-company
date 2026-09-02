import os

OWNER_HEADERS = {
    "Authorization": (
        "Bearer "
        + os.environ.get("OWNER_API_TOKEN", "test-owner-token")
    )
}

import os
from fastapi.testclient import TestClient

from app.main import app
from app.models.task import ApprovalStatus
from app.services.tasks import TaskRepository


client = TestClient(app)


def test_pending_approvals_returns_only_pending_tasks(monkeypatch):
    expected = []

    def fake_list_recent(self, *, approval_status=None, **kwargs):
        assert approval_status == "pending"
        return expected

    monkeypatch.setattr(TaskRepository, "list_recent", fake_list_recent)

    response = client.get("/api/owner/pending-approvals", headers=OWNER_HEADERS)

    assert response.status_code == 200
    assert response.json() == []


def test_approve_task_returns_404_for_missing_task(monkeypatch):
    monkeypatch.setattr(
        TaskRepository,
        "approve",
        lambda self, task_id: None,
    )

    response = client.post("/api/owner/tasks/999999/approve", headers=OWNER_HEADERS)

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


def test_reject_task_returns_404_for_missing_task(monkeypatch):
    monkeypatch.setattr(
        TaskRepository,
        "reject",
        lambda self, task_id: None,
    )

    response = client.post("/api/owner/tasks/999999/reject", headers=OWNER_HEADERS)

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}
