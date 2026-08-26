from __future__ import annotations

import time
from typing import Any

import httpx


class OpenAICompatibleLLMClient:
    """Klient HTTP dla providerów zgodnych z API OpenAI Chat Completions."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float,
        max_retries: int = 0,
        retry_backoff_seconds: float = 0.1,
    ) -> None:
        normalized_base_url = base_url.strip().rstrip("/")
        normalized_api_key = api_key.strip()
        normalized_model = model.strip()

        if not normalized_base_url:
            raise ValueError("Adres providera LLM nie może być pusty")

        if not normalized_api_key:
            raise ValueError("Klucz API providera LLM nie może być pusty")

        if not normalized_model:
            raise ValueError("Model LLM nie może być pusty")

        if timeout_seconds <= 0:
            raise ValueError(
                "Timeout klienta LLM musi być większy od zera"
            )

        if not 0 <= max_retries <= 10:
            raise ValueError(
                "Liczba ponowień klienta LLM musi mieścić się w zakresie 0–10"
            )

        if retry_backoff_seconds < 0:
            raise ValueError(
                "Opóźnienie ponowień klienta LLM nie może być ujemne"
            )

        self._base_url = normalized_base_url
        self._api_key = normalized_api_key
        self._model = normalized_model
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._retry_backoff_seconds = retry_backoff_seconds

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        system_prompt = system_prompt.strip()
        user_prompt = user_prompt.strip()

        if not system_prompt:
            raise ValueError("Prompt systemowy LLM nie może być pusty")

        if not user_prompt:
            raise ValueError("Prompt użytkownika LLM nie może być pusty")

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        for attempt in range(self._max_retries + 1):
            try:
                response = httpx.post(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=self._timeout_seconds,
                )
                response.raise_for_status()
                return self._parse_response(response)

            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt >= self._max_retries:
                    raise

                if self._retry_backoff_seconds:
                    time.sleep(
                        self._retry_backoff_seconds * (2**attempt)
                    )

        raise RuntimeError("Nie udało się uzyskać odpowiedzi LLM")

    @staticmethod
    def _parse_response(response: httpx.Response) -> str:
        try:
            payload: Any = response.json()
        except ValueError as exc:
            raise RuntimeError(
                "Provider LLM zwrócił niepoprawny JSON"
            ) from exc

        if not isinstance(payload, dict):
            raise RuntimeError(
                "Provider LLM zwrócił odpowiedź w nieprawidłowym formacie"
            )

        choices = payload.get("choices")

        if not isinstance(choices, list) or not choices:
            raise RuntimeError(
                "Provider LLM zwrócił odpowiedź bez choices"
            )

        first_choice = choices[0]

        if not isinstance(first_choice, dict):
            raise RuntimeError(
                "Provider LLM zwrócił nieprawidłowy wybór odpowiedzi"
            )

        message = first_choice.get("message")

        if not isinstance(message, dict):
            raise RuntimeError(
                "Provider LLM zwrócił odpowiedź bez message"
            )

        content = message.get("content")

        if not isinstance(content, str):
            raise RuntimeError(
                "Provider LLM zwrócił treść, która nie jest tekstem"
            )

        content = content.strip()

        if not content:
            raise RuntimeError(
                "Provider LLM zwrócił pustą odpowiedź"
            )

        return content
