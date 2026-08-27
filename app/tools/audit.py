from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_AUDIT_PATH = Path(
    os.getenv("AI_COMPANY_TOOL_AUDIT", "data/tool_audit.jsonl")
)


def audit_tool_call(
    tool_name: str,
    *,
    status: str,
    arguments: dict[str, Any] | None = None,
    error: str | None = None,
    audit_path: Path | None = None,
) -> None:
    path = audit_path or DEFAULT_AUDIT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool": tool_name,
        "status": status,
        "arguments": arguments or {},
    }

    if error is not None:
        event["error"] = error

    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=False) + "\n")
