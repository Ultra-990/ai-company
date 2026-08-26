from types import SimpleNamespace

import pytest

from app.services.llm_task_operation import LLMTaskOperation


class StubLLMClient:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def complete(self, *, system_prompt: str, user_prompt: str):
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
            }
        )
        return self.result


def make_task(*, assigned_agent=None, description=None):
    return SimpleNamespace(
        assigned_agent=assigned_agent,
        description=description,
    )


def test_llm_operation_calls_client_with_agent_and_description():
    client = StubLLMClient("  Gotowe przez LLM  ")
    operation = LLMTaskOperation(client)

    result = operation(
        make_task(
            assigned_agent="  analityk  ",
            description="  Przygotuj analizę  ",
        )
    )

    assert result == "Gotowe przez LLM"
    assert len(client.calls) == 1
    assert client.calls[0]["user_prompt"] == "Przygotuj analizę"
    assert "analityk" in client.calls[0]["system_prompt"]


@pytest.mark.parametrize(
    ("task", "error"),
    [
        (
            make_task(description="Opis"),
            "bez przypisanego agenta",
        ),
        (
            make_task(assigned_agent="agent", description="  "),
            "bez opisu",
        ),
    ],
)
def test_llm_operation_validates_task(task, error):
    client = StubLLMClient("wynik")
    operation = LLMTaskOperation(client)

    with pytest.raises(RuntimeError, match=error):
        operation(task)

    assert client.calls == []


def test_llm_operation_rejects_empty_result():
    client = StubLLMClient("  ")
    operation = LLMTaskOperation(client)

    with pytest.raises(RuntimeError, match="pusty wynik"):
        operation(make_task(assigned_agent="agent", description="Opis"))
