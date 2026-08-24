import pytest

from app.models.task import Task
from app.services.agent_task_operation import AgentTaskOperation


class RecordingClient:
    def __init__(self, result: str = " odpowiedź agenta ") -> None:
        self.result = result
        self.calls = []

    def run(self, *, agent: str, prompt: str) -> str:
        self.calls.append({"agent": agent, "prompt": prompt})
        return self.result


def make_task(
    *,
    description: str | None = "  Wykonaj analizę  ",
    assigned_agent: str | None = "  analyst  ",
) -> Task:
    return Task(
        title="Test task",
        description=description,
        assigned_agent=assigned_agent,
    )


def test_operation_delegates_task_to_agent() -> None:
    client = RecordingClient()
    operation = AgentTaskOperation(client)

    result = operation(make_task())

    assert result == "odpowiedź agenta"
    assert client.calls == [
        {
            "agent": "analyst",
            "prompt": "Wykonaj analizę",
        }
    ]


@pytest.mark.parametrize(
    "assigned_agent",
    [None, "", "   "],
)
def test_operation_rejects_missing_agent(
    assigned_agent: str | None,
) -> None:
    client = RecordingClient()
    operation = AgentTaskOperation(client)

    with pytest.raises(RuntimeError, match="agenta"):
        operation(make_task(assigned_agent=assigned_agent))

    assert client.calls == []


@pytest.mark.parametrize(
    "description",
    [None, "", "   "],
)
def test_operation_rejects_empty_prompt(
    description: str | None,
) -> None:
    client = RecordingClient()
    operation = AgentTaskOperation(client)

    with pytest.raises(RuntimeError, match="opisu"):
        operation(make_task(description=description))

    assert client.calls == []


def test_operation_rejects_empty_agent_response() -> None:
    client = RecordingClient(result="   ")
    operation = AgentTaskOperation(client)

    with pytest.raises(RuntimeError, match="pusty"):
        operation(make_task())


def test_operation_rejects_non_string_agent_response() -> None:
    client = RecordingClient(result=None)  # type: ignore[arg-type]
    operation = AgentTaskOperation(client)

    with pytest.raises(RuntimeError, match="tekstem"):
        operation(make_task())


def test_operation_propagates_client_exception() -> None:
    class FailingClient:
        def run(self, *, agent: str, prompt: str) -> str:
            raise RuntimeError("provider unavailable")

    operation = AgentTaskOperation(FailingClient())

    with pytest.raises(RuntimeError, match="provider unavailable"):
        operation(make_task())
