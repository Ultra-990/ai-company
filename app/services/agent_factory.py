from __future__ import annotations

from app.core.config import ConfigurationError, Settings
from app.services.agent_client import AgentClient
from app.services.mock_agent_client import MockAgentClient


def get_agent_client(settings: Settings) -> AgentClient:
    """Zwraca klienta agenta zgodnie z konfiguracją aplikacji."""

    provider = settings.agents.provider.strip().lower()

    if provider == "mock":
        return MockAgentClient()

    raise ConfigurationError(
        f"Nieobsługiwany provider agenta: {settings.agents.provider}"
    )
