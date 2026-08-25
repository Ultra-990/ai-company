from __future__ import annotations

import httpx
import pytest

from app.services.http_agent_client import HttpAgentClient


def test_http_client_sends_agent_prompt_and_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"result": "  Gotowe  "}

    def fake_post(
        url: str,
        *,
        json: dict[str, str],
        timeout: float,
    ) -> FakeResponse:
        captured.update(
            url=url,
            json=json,
            timeout=timeout,
        )
        return FakeResponse()

    monkeypatch.setattr(httpx, "post", fake_post)

    client = HttpAgentClient(
        base_url=" https://agent.example/ ",
        model=" test-model ",
        timeout_seconds=12,
    )

    assert client.run(agent=" analyst ", prompt=" Zbadaj dane ") == "Gotowe"
    assert captured == {
        "url": "https://agent.example/run",
        "json": {
            "agent": " analyst ",
            "prompt": " Zbadaj dane ",
            "model": "test-model",
        },
        "timeout": 12,
    }


def test_http_client_rejects_empty_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"result": "  "}

    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: FakeResponse())

    client = HttpAgentClient(
        base_url="https://agent.example",
        model="test",
        timeout_seconds=30,
    )

    with pytest.raises(RuntimeError, match="pusty wynik"):
        client.run(agent="analyst", prompt="Zbadaj dane")


def test_http_client_rejects_non_text_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"result": {"text": "niepoprawne"}}

    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: FakeResponse())

    client = HttpAgentClient(
        base_url="https://agent.example",
        model="test",
        timeout_seconds=30,
    )

    with pytest.raises(RuntimeError, match="nie jest tekstem"):
        client.run(agent="analyst", prompt="Zbadaj dane")


def test_http_client_propagates_http_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_post(*args, **kwargs) -> None:
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(httpx, "post", fake_post)

    client = HttpAgentClient(
        base_url="https://agent.example",
        model="test",
        timeout_seconds=1,
    )

    with pytest.raises(httpx.TimeoutException):
        client.run(agent="analyst", prompt="Zbadaj dane")


def test_retries_timeout_then_returns_result(monkeypatch):
    import httpx

    client = HttpAgentClient(
        base_url="https://agent.example",
        model="test-model",
        timeout_seconds=3,
        max_retries=2,
        retry_backoff_seconds=0,
    )

    calls = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"result": "success"}

    def fake_post(url, *, json, timeout):
        calls.append((url, json, timeout))
        if len(calls) < 3:
            raise httpx.TimeoutException("temporary timeout")
        return Response()

    monkeypatch.setattr("httpx.post", fake_post)

    assert client.run(agent="planner", prompt="hello") == "success"
    assert len(calls) == 3


def test_retries_network_error_until_limit(monkeypatch):
    import httpx
    import pytest

    client = HttpAgentClient(
        base_url="https://agent.example",
        model="test-model",
        timeout_seconds=3,
        max_retries=2,
        retry_backoff_seconds=0,
    )

    calls = 0

    def fake_post(url, *, json, timeout):
        nonlocal calls
        calls += 1
        raise httpx.NetworkError("connection failed")

    monkeypatch.setattr("httpx.post", fake_post)

    with pytest.raises(httpx.NetworkError):
        client.run(agent="planner", prompt="hello")

    assert calls == 3


def test_http_status_error_is_not_retried(monkeypatch):
    import httpx
    import pytest

    client = HttpAgentClient(
        base_url="https://agent.example",
        model="test-model",
        timeout_seconds=3,
        max_retries=2,
        retry_backoff_seconds=0,
    )

    calls = 0
    response = httpx.Response(
        503,
        request=httpx.Request("POST", "https://agent.example/run"),
    )

    def fake_post(url, *, json, timeout):
        nonlocal calls
        calls += 1
        return response

    monkeypatch.setattr("httpx.post", fake_post)

    with pytest.raises(httpx.HTTPStatusError):
        client.run(agent="planner", prompt="hello")

    assert calls == 1
