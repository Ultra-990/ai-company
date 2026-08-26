from __future__ import annotations

from app.core.config import ConfigurationError, Settings
from app.services.agent_client import AgentClient
from app.services.http_agent_client import HttpAgentClient
from app.services.mock_agent_client import MockAgentClient


def get_agent_client(settings: Settings) -> AgentClient:
    """Zwraca klienta agenta zgodnie z konfiguracją aplikacji."""

    provider = settings.agents.provider.strip().lower()

    if provider == "mock":
        return MockAgentClient()

    if provider == "http":
        if not settings.agents.base_url:
            raise ConfigurationError(
                "Provider http wymaga ustawienia base_url"
            )

        try:
            return HttpAgentClient(
                base_url=settings.agents.base_url,
                model=settings.agents.model,
                timeout_seconds=settings.agents.timeout_seconds,
                max_retries=settings.agents.max_retries,
            )
        except ValueError as exc:
            raise ConfigurationError(str(exc)) from exc

    raise ConfigurationError(
        f"Nieobsługiwany provider agenta: {settings.agents.provider}"
    )


from app.services.llm_client import LLMClient
from app.services.openai_compatible_llm_client import (
    OpenAICompatibleLLMClient,
)


def get_llm_client(settings: Settings) -> LLMClient | None:
    """Tworzy klienta LLM zgodnie z konfiguracją."""

    if not settings.llm.enabled:
        return None

    if settings.llm.provider.strip().lower() != "openai-compatible":
        raise ConfigurationError(
            f"Nieobsługiwany provider LLM: {settings.llm.provider}"
        )

    try:
        return OpenAICompatibleLLMClient(
            base_url=settings.llm.base_url,
            api_key=settings.llm.api_key,
            model=settings.llm.model,
            timeout_seconds=settings.llm.timeout_seconds,
            max_retries=settings.llm.max_retries,
            retry_backoff_seconds=settings.llm.retry_backoff_seconds,
        )
    except ValueError as exc:
        raise ConfigurationError(str(exc)) from exc
