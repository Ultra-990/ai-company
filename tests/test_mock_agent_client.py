from app.services.mock_agent_client import MockAgentClient


def test_mock_agent_client_returns_configured_response() -> None:
    client = MockAgentClient(response=" wynik ")

    result = client.run(
        agent="analyst",
        prompt="Przeanalizuj dane",
    )

    assert result == " wynik "
    assert client.calls == [
        {
            "agent": "analyst",
            "prompt": "Przeanalizuj dane",
        }
    ]
