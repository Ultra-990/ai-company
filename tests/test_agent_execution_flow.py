from app.services.agent_task_operation import AgentTaskOperation
from app.services.mock_agent_client import MockAgentClient
from app.services.production_executor import ProductionTaskExecutor


def test_mock_agent_execution_flow() -> None:
    client = MockAgentClient()
    operation = AgentTaskOperation(client)
    executor = ProductionTaskExecutor(operation)

    task = type(
        "TaskStub",
        (),
        {
            "id": 1,
            "title": "Test zadania",
            "description": "Wykonaj testowe zadanie",
            "assigned_agent": "agent-1",
        },
    )()

    result = executor.execute(task)

    assert result.success is True
    assert result.reason == "Mockowa odpowiedź agenta"
