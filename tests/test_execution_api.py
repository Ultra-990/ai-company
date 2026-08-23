from dataclasses import dataclass

from fastapi.testclient import TestClient

from app.api.execution import get_task_executor, get_orchestrator
from app.main import app
from app.services.executor import ExecutionResult
from app.models.task import TaskStatus



@dataclass
class SuccessfulExecutor:
    def execute(self, task):
        return ExecutionResult(
            success=True,
            reason=f"Wykonano zadanie {task.id}",
        )


@dataclass
class FailingExecutor:
    def execute(self, task):
        return ExecutionResult(
            success=False,
            reason="Wykonanie zakończyło się błędem",
        )


def test_execute_next_returns_204_for_empty_queue():
    app.dependency_overrides[get_task_executor] = (
        lambda: SuccessfulExecutor()
    )

    try:
        client = TestClient(app)
        response = client.post("/api/tasks/execute-next")

        assert response.status_code == 204
        assert response.content == b""
    finally:
        app.dependency_overrides.clear()


def test_execute_next_completes_task(
    task_repository,
    approved_task,
):
    app.dependency_overrides[get_task_executor] = (
        lambda: SuccessfulExecutor()
    )

    try:
        client = TestClient(app)
        response = client.post(
            "/api/tasks/execute-next",
            params={"worker_id": "api-worker"},
        )

        assert response.status_code == 200

        body = response.json()
        assert body["success"] is True
        assert body["task_id"] == approved_task.id
        assert body["task_status"] == "completed"
    finally:
        app.dependency_overrides.clear()


def test_execute_next_blocks_failed_task(
    task_repository,
    approved_task,
):
    app.dependency_overrides[get_task_executor] = (
        lambda: FailingExecutor()
    )

    try:
        client = TestClient(app)
        response = client.post(
            "/api/tasks/execute-next",
            params={"worker_id": "api-worker"},
        )

        assert response.status_code == 200

        body = response.json()
        assert body["success"] is False
        assert body["task_id"] == approved_task.id
        assert body["task_status"] == "blocked"
    finally:
        app.dependency_overrides.clear()


def test_execution_endpoint_is_registered():
    from app.main import app

    schema = app.openapi()

    assert "/api/tasks/execute-next" in schema["paths"]
    assert "post" in schema["paths"]["/api/tasks/execute-next"]

def test_execute_next_returns_500_when_executor_is_not_configured(
    task_repository,
    approved_task,
):
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/api/tasks/execute-next",
        params={"worker_id": "api-worker"},
    )

    assert response.status_code == 500

    refreshed_task = task_repository.get(approved_task.id)
    assert refreshed_task.status == TaskStatus.BLOCKED

