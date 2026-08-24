from __future__ import annotations

from dataclasses import replace

import pytest

from app.core.config import ConfigurationError, load_settings
from app.services.agent_factory import get_agent_client
from app.services.mock_agent_client import MockAgentClient


def test_factory_returns_mock_client() -> None:
    settings = load_settings()

    client = get_agent_client(settings)

    assert isinstance(client, MockAgentClient)


def test_factory_accepts_provider_case_insensitively() -> None:
    settings = load_settings()
    settings = replace(
        settings,
        agents=replace(settings.agents, provider=" MOCK "),
    )

    client = get_agent_client(settings)

    assert isinstance(client, MockAgentClient)


def test_factory_rejects_unknown_provider() -> None:
    settings = load_settings()
    settings = replace(
        settings,
        agents=replace(settings.agents, provider="unknown"),
    )

    with pytest.raises(ConfigurationError, match="Nieobsługiwany provider"):
        get_agent_client(settings)
