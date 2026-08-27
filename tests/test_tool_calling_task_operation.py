import pytest

from app.models.task import Task
from app.services.tool_calling_task_operation import (
    ToolCallingLLMTaskOperation,
)


class StubClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = iter(responses)
        self.calls: list[tuple[str, str]] = []

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        self.calls.append((system_prompt, user_prompt))
        return next(self.responses)


def make_task() -> Task:
    return Task(
        id=1,
        title="Test",
        description="Przeczytaj plik",
        assigned_agent="agent-test",
    )


def test_tool_calling_operation_returns_final_response() -> None:
    client = StubClient(
        [
            '{"type":"final","content":"Gotowe"}',
        ]
    )

    operation = ToolCallingLLMTaskOperation(client)

    result = operation(make_task())

    assert result == "Gotowe"
    assert len(client.calls) == 1


def test_tool_calling_operation_executes_read_only_tool() -> None:
    client = StubClient(
        [
            '{"type":"tool_call","name":"list_project_files","arguments":{}}',
            '{"type":"final","content":"Lista gotowa"}',
        ]
    )

    operation = ToolCallingLLMTaskOperation(client)

    result = operation(make_task())

    assert result == "Lista gotowa"
    assert len(client.calls) == 2


def test_tool_calling_operation_rejects_invalid_json() -> None:
    client = StubClient(
        [
            "niepoprawna odpowiedź",
        ]
    )

    operation = ToolCallingLLMTaskOperation(client)

    with pytest.raises(RuntimeError, match="tool-calling"):
        operation(make_task())
