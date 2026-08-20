from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass
class AuditEntry:
    timestamp: str
    event_type: str
    message: str
    payload: Dict[str, Any]


class AuditLogger:
    def __init__(self):
        self.entries: List[AuditEntry] = []

    def log(self, event_type: str, message: str, payload: Dict[str, Any] | None = None) -> AuditEntry:
        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            message=message,
            payload=payload or {},
        )
        self.entries.append(entry)
        return entry

    def export(self) -> List[Dict[str, Any]]:
        return [asdict(entry) for entry in self.entries]
