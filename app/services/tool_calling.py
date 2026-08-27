from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any

from app.tools.registry import execute_tool


ALLOWED_TOOLS = frozenset({
    "read_project_file",
    "list_project_files",
})

MAX_TOOL_CALLS = 3


class ToolCallingError(ValueError):
    """Błąd niepoprawnej odpowiedzi modelu lub niedozwolonego wywołania."""


def parse_model_response(response: str | Mapping[str, Any]) -> dict[str, Any]:
    """Parsuje odpowiedź modelu w formacie JSON."""

    if isinstance(response, Mapping):
        payload = dict(response)
    elif isinstance(response, str):
        try:
            payload = json.loads(response)
        except json.JSONDecodeError as exc:
            raise ToolCallingError(
                "Odpowiedź modelu nie zawiera poprawnego JSON."
            ) from exc
    else:
        raise ToolCallingError("Odpowiedź modelu musi być tekstem lub obiektem mapującym.")

    if not isinstance(payload, dict):
        raise ToolCallingError("Odpowiedź modelu musi być obiektem JSON.")

    response_type = payload.get("type")
    if response_type not in {"tool_call", "final"}:
        raise ToolCallingError(
            "Dozwolone typy odpowiedzi to wyłącznie 'tool_call' i 'final'."
        )

    return payload


def execute_model_tool_call(payload: Mapping[str, Any]) -> Any:
    """Wykonuje pojedyncze, bezpieczne wywołanie narzędzia."""

    if payload.get("type") != "tool_call":
        raise ToolCallingError("Oczekiwano odpowiedzi typu 'tool_call'.")

    name = payload.get("name")
    arguments = payload.get("arguments", {})

    if not isinstance(name, str) or not name:
        raise ToolCallingError("Wywołanie musi zawierać nazwę narzędzia.")

    if name not in ALLOWED_TOOLS:
        raise ToolCallingError(f"Narzędzie '{name}' nie jest dozwolone.")

    if not isinstance(arguments, dict):
        raise ToolCallingError("Pole 'arguments' musi być obiektem JSON.")

    # Registry egzekwuje dodatkowo wymagania uprawnień i przekazuje
    # walidację ścieżek oraz limitów do właściwego handlera.
    return execute_tool(name, **arguments)


def run_tool_loop(
    initial_response: str | Mapping[str, Any],
    model: Callable[[str], str | Mapping[str, Any]],
    *,
    max_tool_calls: int = MAX_TOOL_CALLS,
) -> str:
    """
    Realizuje przepływ model → tool → model.

    `model` otrzymuje tekstowy kontekst zawierający wynik poprzedniego
    wywołania i zwraca kolejną odpowiedź JSON.
    """

    if max_tool_calls < 0 or max_tool_calls > MAX_TOOL_CALLS:
        raise ToolCallingError(
            f"Limit wywołań musi mieścić się w zakresie 0-{MAX_TOOL_CALLS}."
        )

    response = initial_response
    tool_calls = 0

    while True:
        payload = parse_model_response(response)
        response_type = payload["type"]

        if response_type == "final":
            content = payload.get("content")
            if not isinstance(content, str):
                raise ToolCallingError(
                    "Odpowiedź typu 'final' musi zawierać tekstowe pole 'content'."
                )
            return content

        if tool_calls >= max_tool_calls:
            raise ToolCallingError(
                f"Przekroczono limit {max_tool_calls} wywołań narzędzi."
            )

        result = execute_model_tool_call(payload)
        tool_calls += 1

        context = {
            "type": "tool_result",
            "tool": payload["name"],
            "result": result,
            "tool_calls": tool_calls,
        }
        response = model(json.dumps(context, ensure_ascii=False, default=str))
