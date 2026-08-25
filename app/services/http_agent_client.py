from __future__ import annotations

import time
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
        max_retries: int = 0,
        retry_backoff_seconds: float = 0.1,
    ) -> None:
        normalized_base_url = base_url.strip().rstrip("/")

        if not normalized_base_url:
            raise ValueError("Adres klienta agenta nie może być pusty")

        if not model.strip():
            raise ValueError("Model agenta nie może być pusty")

        if timeout_seconds <= 0:
            raise ValueError("Timeout klienta agenta musi być większy od zera")

        if not 0 <= max_retries <= 10:
            raise ValueError(
                "Liczba ponowień klienta agenta musi mieścić się w zakresie 0–10"
            )

        if retry_backoff_seconds < 0:
            raise ValueError("Opóźnienie ponowień nie może być ujemne")

        self._base_url = normalized_base_url
        self._model = model.strip()
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._retry_backoff_seconds = retry_backoff_seconds

    def run(self, *, agent: str, prompt: str) -> str:
        request = {
            "agent": agent,
            "prompt": prompt,
            "model": self._model,
        }

        for attempt in range(self._max_retries + 1):
            try:
                response = httpx.post(
                    f"{self._base_url}/run",
                    json=request,
                    timeout=self._timeout_seconds,
                )
                response.raise_for_status()
                return self._parse_response(response)

            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt >= self._max_retries:
                    raise

                if self._retry_backoff_seconds:
                    time.sleep(self._retry_backoff_seconds * (2**attempt))

    @staticmethod
    def _parse_response(response: httpx.Response) -> str:
        try:
            payload: Any = response.json()
        except ValueError as exc:
            raise RuntimeError("Agent zwrócił niepoprawny JSON") from exc

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
