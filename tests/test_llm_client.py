from __future__ import annotations

import httpx
import pytest

from app.services.llm_client import LLMClient
from app.services.openai_compatible_llm_client import (
    OpenAICompatibleLLMClient,
)


def test_openai_compatible_client_implements_llm_contract() -> None:
    client = OpenAICompatibleLLMClient(
        base_url="https://llm.example/v1",
        api_key="secret",
        model="test-model",
        timeout_seconds=10,
    )

    assert isinstance(client, LLMClient)


def test_client_sends_chat_completion_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    response = httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "  Gotowa odpowiedź  ",
                    }
                }
            ]
        },
        request=httpx.Request(
            "POST",
            "https://llm.example/v1/chat/completions",
        ),
    )

    def fake_post(
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, object],
        timeout: float,
    ) -> httpx.Response:
        captured.update(
            url=url,
            headers=headers,
            json=json,
            timeout=timeout,
        )
        return response

    monkeypatch.setattr(httpx, "post", fake_post)

    client = OpenAICompatibleLLMClient(
        base_url=" https://llm.example/v1/ ",
        api_key=" secret ",
        model=" test-model ",
        timeout_seconds=12,
    )

    result = client.complete(
        system_prompt="Jesteś analitykiem.",
        user_prompt="Przeanalizuj dane.",
    )

    assert result == "Gotowa odpowiedź"
    assert captured == {
        "url": "https://llm.example/v1/chat/completions",
        "headers": {
            "Authorization": "Bearer secret",
            "Content-Type": "application/json",
        },
        "json": {
            "model": "test-model",
            "messages": [
                {
                    "role": "system",
                    "content": "Jesteś analitykiem.",
                },
                {
                    "role": "user",
                    "content": "Przeanalizuj dane.",
                },
            ],
        },
        "timeout": 12,
    }


def test_client_rejects_empty_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "  ",
                    }
                }
            ]
        },
        request=httpx.Request(
            "POST",
            "https://llm.example/v1/chat/completions",
        ),
    )

    monkeypatch.setattr(
        httpx,
        "post",
        lambda *args, **kwargs: response,
    )

    client = OpenAICompatibleLLMClient(
        base_url="https://llm.example/v1",
        api_key="secret",
        model="test-model",
        timeout_seconds=10,
    )

    with pytest.raises(RuntimeError, match="pustą odpowiedź"):
        client.complete(
            system_prompt="System",
            user_prompt="Prompt",
        )


def test_client_retries_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    response = httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "content": "Sukces",
                    }
                }
            ]
        },
        request=httpx.Request(
            "POST",
            "https://llm.example/v1/chat/completions",
        ),
    )

    def fake_post(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.TimeoutException("timeout")
        return response

    monkeypatch.setattr(httpx, "post", fake_post)

    client = OpenAICompatibleLLMClient(
        base_url="https://llm.example/v1",
        api_key="secret",
        model="test-model",
        timeout_seconds=10,
        max_retries=1,
        retry_backoff_seconds=0,
    )

    assert client.complete(
        system_prompt="System",
        user_prompt="Prompt",
    ) == "Sukces"
    assert calls == 2
