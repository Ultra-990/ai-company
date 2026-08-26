from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app


class StubLLMClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
            }
        )
        return "Wynik wygenerowany przez testowego klienta LLM"


def test_execute_next_uses_llm_when_enabled(monkeypatch):
    import app.api.execution as execution

    llm_client = StubLLMClient()

    settings = SimpleNamespace(
        llm=SimpleNamespace(enabled=True),
        agents=SimpleNamespace(enabled=True),
    )

    monkeypatch.setattr(execution, "load_settings", lambda: settings)
    monkeypatch.setattr(
        execution,
        "get_llm_client",
        lambda current_settings: llm_client,
    )

    api_client = TestClient(app)

    create_response = api_client.post(
        "/api/tasks",
        json={
            "title": "Zadanie testowe LLM",
            "description": "Wykonaj zadanie integracyjne",
            "assigned_agent": "test-agent",
        },
    )

    assert create_response.status_code in {200, 201}, (
        create_response.status_code,
        create_response.text,
    )

    task_id = create_response.json()["id"]

    approve_response = api_client.post(
        f"/api/owner/tasks/{task_id}/approve"
    )

    assert approve_response.status_code == 200, (
        approve_response.status_code,
        approve_response.text,
    )

    execute_response = api_client.post(
        "/api/tasks/execute-next",
        params={"worker_id": "llm-integration-worker"},
    )

    assert execute_response.status_code == 200, (
        execute_response.status_code,
        execute_response.text,
    )

    assert llm_client.calls
    assert llm_client.calls[0]["system_prompt"]
    assert llm_client.calls[0]["user_prompt"]
    assert "Wykonaj zadanie integracyjne" in (
        llm_client.calls[0]["user_prompt"]
    )
