from app.tools.audit import REDACTED, TRUNCATED, redact_value


def test_redact_simple_secret_keys() -> None:
    data = {
        "password": "abc123",
        "token": "secret-token",
        "user": "marcin",
    }

    result = redact_value(data)

    assert result["password"] == REDACTED
    assert result["token"] == REDACTED
    assert result["user"] == "marcin"


def test_redact_nested_values() -> None:
    data = {
        "request": {
            "api_key": "key-123",
            "nested": {
                "secret": "hidden",
            },
        }
    }

    result = redact_value(data)

    assert result["request"]["api_key"] == REDACTED
    assert result["request"]["nested"]["secret"] == REDACTED


def test_redact_suffix_keys() -> None:
    data = {
        "user_password": "abc123",
        "service_token": "tok-123",
        "config": {
            "private_key": "ssh-rsa AAAA",
        },
    }

    result = redact_value(data)

    assert result["user_password"] == REDACTED
    assert result["service_token"] == REDACTED
    assert result["config"]["private_key"] == REDACTED


def test_truncate_long_strings() -> None:
    long_text = "a" * 1000
    result = redact_value(long_text)

    assert result.endswith(TRUNCATED)
    assert len(result) < 530
