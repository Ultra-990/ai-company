from __future__ import annotations

from app.models.task import Task
from app.services.llm_client import LLMClient


class LLMTaskOperation:
    """Operacja wykonująca zadanie za pomocą providera LLM."""

    def __init__(self, client: LLMClient) -> None:
        self._client = client

    def __call__(self, task: Task) -> str:
        agent = (task.assigned_agent or "").strip()
        if not agent:
            raise RuntimeError(
                "Nie można wykonać zadania bez przypisanego agenta"
            )

        user_prompt = (task.description or "").strip()
        if not user_prompt:
            raise RuntimeError(
                "Nie można wykonać zadania bez opisu"
            )

        system_prompt = (
            "Jesteś agentem systemu AI Company. "
            f"Twoja nazwa lub rola to: {agent}. "
            "Wykonaj zadanie dokładnie i zwróć wyłącznie użyteczny rezultat."
        )

        result = self._client.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        if not isinstance(result, str):
            raise RuntimeError(
                "LLM zwrócił wynik, który nie jest tekstem"
            )

        result = result.strip()
        if not result:
            raise RuntimeError(
                "LLM zwrócił pusty wynik"
            )

        return result
