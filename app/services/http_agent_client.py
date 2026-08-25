from __future__ import annotations

from typing import Any

import httpx


class HttpAgentClient:
    """Klient komunikujący się z rzeczywistym API agenta."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float,
    ) -> None:
        normalized_base_url = base_url.strip().rstrip("/")

        if not normalized_base_url:
            raise ValueError("Adres klienta agenta nie może być pusty")

        if not model.strip():
            raise ValueError("Model agenta nie może być pusty")

        self._base_url = normalized_base_url
        self._model = model.strip()
        self._timeout_seconds = timeout_seconds

    def run(self, *, agent: str, prompt: str) -> str:
        response = httpx.post(
            f"{self._base_url}/run",
            json={
                "agent": agent,
                "prompt": prompt,
                "model": self._model,
            },
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()

        try:
            payload: Any = response.json()
        except ValueError as exc:
            raise RuntimeError(
                "Agent zwrócił niepoprawny JSON"
            ) from exc

        if not isinstance(payload, dict):
            raise RuntimeError(
                "Agent zwrócił odpowiedź w nieprawidłowym formacie"
            )

        result = payload.get("result")

        if not isinstance(result, str):
            raise RuntimeError(
                "Agent zwrócił wynik, który nie jest tekstem"
            )

        result = result.strip()

        if not result:
            raise RuntimeError("Agent zwrócił pusty wynik")

        return result
