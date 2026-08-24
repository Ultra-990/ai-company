from typing import Protocol


class AgentClient(Protocol):
    """Kontrakt klienta komunikującego się z agentem."""

    def run(self, *, agent: str, prompt: str) -> str:
        """Wykonuje prompt za pomocą wskazanego agenta."""
        ...
