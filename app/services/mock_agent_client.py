from __future__ import annotations


class MockAgentClient:
    """Deterministyczny klient agenta do testów i developmentu."""

    def __init__(
        self,
        response: str = "Mockowa odpowiedź agenta",
    ) -> None:
        self._response = response
        self.calls: list[dict[str, str]] = []

    def run(self, *, agent: str, prompt: str) -> str:
        self.calls.append(
            {
                "agent": agent,
                "prompt": prompt,
            }
        )
        return self._response
