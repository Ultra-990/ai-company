from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_AUDIT_PATH = Path(
    os.getenv("AI_COMPANY_TOOL_AUDIT", "data/tool_audit.jsonl")
)

REDACTED = "[REDACTED]"
TRUNCATED = "[TRUNCATED]"
MAX_STRING_LENGTH = 500

SENSITIVE_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "apikey",
        "authorization",
        "client_secret",
        "cookie",
        "credentials",
        "password",
        "passwd",
        "private_key",
        "refresh_token",
        "secret",
        "secret_key",
        "session",
        "session_id",
        "token",
    }
)


def _normalize_key(key: object) -> str:
    """Normalizuje nazwę pola na potrzeby wykrywania sekretów."""
    return str(key).strip().lower().replace("-", "_").replace(" ", "_")


def _is_sensitive_key(key: object) -> bool:
    normalized = _normalize_key(key)

    if normalized in SENSITIVE_KEYS:
        return True

    sensitive_suffixes = (
        "_api_key",
        "_password",
        "_secret",
        "_token",
        "_private_key",
    )
    return normalized.endswith(sensitive_suffixes)


def redact_value(value: Any, *, key: object | None = None) -> Any:
    """Rekurencyjnie maskuje sekrety bez modyfikowania wejściowego obiektu."""
    if key is not None and _is_sensitive_key(key):
        return REDACTED

    if isinstance(value, str):
        if len(value) > MAX_STRING_LENGTH:
            return value[:MAX_STRING_LENGTH] + TRUNCATED
        return value

    if isinstance(value, dict):
        return {
            item_key: redact_value(item_value, key=item_key)
            for item_key, item_value in value.items()
        }

    if isinstance(value, list):
        return [redact_value(item) for item in value]

    if isinstance(value, tuple):
        return tuple(redact_value(item) for item in value)

    if isinstance(value, set):
        # Zbiór zamieniamy na listę, aby wynik był bezpieczny dla JSON.
        return [redact_value(item) for item in value]

    return value


def audit_tool_call(
    tool_name: str,
    *,
    status: str,
    arguments: dict[str, Any] | None = None,
    error: str | None = None,
    audit_path: Path | None = None,
) -> None:
    """Zapisuje pojedyncze zdarzenie audytowe, maskując poufne argumenty."""
    path = audit_path or DEFAULT_AUDIT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    event: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool": tool_name,
        "status": status,
        "arguments": redact_value(arguments or {}),
    }

    if error is not None:
        event["error"] = redact_value(error)

    with path.open("a", encoding="utf-8") as file:
        file.write(
            json.dumps(event, ensure_ascii=False, default=str) + "\n"
        )
