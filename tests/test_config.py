

def test_agent_provider_settings_are_loaded() -> None:
    from app.core.config import load_settings

    settings = load_settings()

    assert settings.agents.enabled is False
    assert settings.agents.provider == "mock"
    assert settings.agents.model == "test"
    assert settings.agents.base_url is None
    assert settings.agents.timeout_seconds == 30
