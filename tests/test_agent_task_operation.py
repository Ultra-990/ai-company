from types import SimpleNamespace

import pytest

from app.services.agent_task_operation import AgentTaskOperation


class StubAgentClient:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def run(self, *, agent: str, prompt: str):
        self.calls.append({"agent": agent, "prompt": prompt})
        return self.result


def make_task(*, assigned_agent=None, description=None):
    return SimpleNamespace(
        assigned_agent=assigned_agent,
        description=description,
    )


def test_operation_rejects_missing_assigned_agent():
    client = StubAgentClient("wynik")
    operation = AgentTaskOperation(client)

    with pytest.raises(
        RuntimeError,
        match="bez przypisanego agenta",
    ):
        operation(make_task(description="Opis zadania"))

    assert client.calls == []


def test_operation_rejects_empty_description():
    client = StubAgentClient("wynik")
    operation = AgentTaskOperation(client)

    with pytest.raises(
        RuntimeError,
        match="bez opisu",
    ):
        operation(make_task(assigned_agent="agent-1", description="  "))

    assert client.calls == []


def test_operation_rejects_empty_client_result():
    client = StubAgentClient("   ")
    operation = AgentTaskOperation(client)

    with pytest.raises(
        RuntimeError,
        match="pusty wynik",
    ):
        operation(
            make_task(
                assigned_agent="agent-1",
                description="Opis zadania",
            )
        )

    assert client.calls == [
        {
            "agent": "agent-1",
            "prompt": "Opis zadania",
        }
    ]


def test_operation_rejects_non_text_client_result():
    client = StubAgentClient({"result": "nie tekst"})
    operation = AgentTaskOperation(client)

    with pytest.raises(
        RuntimeError,
        match="nie jest tekstem",
    ):
        operation(
            make_task(
                assigned_agent="agent-1",
                description="Opis zadania",
            )
        )


def test_operation_strips_input_and_output():
    client = StubAgentClient("  Gotowe  ")
    operation = AgentTaskOperation(client)

    result = operation(
        make_task(
            assigned_agent="  agent-1  ",
            description="  Opis zadania  ",
        )
    )

    assert result == "Gotowe"
    assert client.calls == [
        {
            "agent": "agent-1",
            "prompt": "Opis zadania",
        }
    ]
