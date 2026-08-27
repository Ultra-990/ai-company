from __future__ import annotations

from app.models.task import Task
from app.services.llm_client import LLMClient
from app.services.tool_calling import ToolCallingError, run_tool_loop


class ToolCallingLLMTaskOperation:
    """Operacja LLM obsługująca przepływ model → narzędzie → model."""

    def __init__(self, client: LLMClient) -> None:
        self._client = client

    def __call__(self, task: Task) -> str:
        agent = (task.assigned_agent or "").strip()
        if not agent:
            raise RuntimeError(
                "Nie można wykonać zadania bez przypisanego agenta"
            )

        task_description = (task.description or "").strip()
        if not task_description:
            raise RuntimeError(
                "Nie można wykonać zadania bez opisu"
            )

        system_prompt = (
            "Jesteś agentem systemu AI Company. "
            f"Twoja rola to: {agent}. "
            "Odpowiadaj wyłącznie poprawnym obiektem JSON. "
            "Możesz używać wyłącznie narzędzi read-only. "
            "Wywołanie narzędzia ma format: "
            '{"type":"tool_call","name":"...","arguments":{}}. '
            "Odpowiedź końcowa ma format: "
            '{"type":"final","content":"..."}'
        )

        first_response = self._client.complete(
            system_prompt=system_prompt,
            user_prompt=task_description,
        )

        def continue_model(tool_result: str) -> str:
            return self._client.complete(
                system_prompt=system_prompt,
                user_prompt=(
                    f"Zadanie:\n{task_description}\n\n"
                    f"Wynik narzędzia:\n{tool_result}\n\n"
                    "Kontynuuj wykonanie zadania. "
                    "Zwróć wyłącznie poprawny obiekt JSON."
                ),
            )

        try:
            result = run_tool_loop(
                first_response,
                continue_model,
            )
        except ToolCallingError as exc:
            raise RuntimeError(
                f"Niepoprawny przepływ tool-calling: {exc}"
            ) from exc

        if not isinstance(result, str) or not result.strip():
            raise RuntimeError("LLM zwrócił pusty wynik")

        return result.strip()
