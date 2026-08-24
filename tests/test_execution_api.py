import pytest
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



def test_default_task_executor_is_fail_safe() -> None:
    executor = get_task_executor()

    with pytest.raises(RuntimeError, match="Brak skonfigurowanego wykonawcy"):
        executor.execute(type("TaskStub", (), {"id": 999})())


def test_enabled_mock_provider_returns_production_executor(monkeypatch):
    from app.api import execution
    from app.core.config import load_settings
    from app.services.production_executor import ProductionTaskExecutor

    settings = load_settings()
    enabled_agents = settings.agents.__class__(
        enabled=True,
        default_autonomy_level=settings.agents.default_autonomy_level,
        maximum_autonomy_level=settings.agents.maximum_autonomy_level,
        allow_agent_creation=settings.agents.allow_agent_creation,
        require_owner_approval=settings.agents.require_owner_approval,
        maximum_task_depth=settings.agents.maximum_task_depth,
        provider="mock",
        model=settings.agents.model,
        base_url=settings.agents.base_url,
        timeout_seconds=settings.agents.timeout_seconds,
    )

    enabled_settings = settings.__class__(
        system=settings.system,
        server=settings.server,
        agents=enabled_agents,
        safety=settings.safety,
        finance=settings.finance,
        database=settings.database,
        memory=settings.memory,
        logging=settings.logging,
    )

    monkeypatch.setattr(
        execution,
        "load_settings",
        lambda: enabled_settings,
    )

    executor = execution.get_task_executor()

    assert isinstance(executor, ProductionTaskExecutor)
