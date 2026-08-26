from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    """Kontrakt klienta komunikującego się z providerem LLM."""

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Zwraca tekstową odpowiedź modelu LLM."""
        ...
