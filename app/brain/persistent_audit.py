from __future__ import annotations

from typing import Any

from app.brain.audit_logger import AuditLogger
from app.services.audit import AuditRepository


class PersistentAuditLogger:
    """Łączy audyt in-memory z trwałym repozytorium audytu."""

    def __init__(
        self,
        repository: AuditRepository,
        fallback: AuditLogger | None = None,
    ) -> None:
        self.repository = repository
        self.fallback = fallback or AuditLogger()

    def log(
        self,
        event_type: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ):
        payload = payload or {}

        # Zachowujemy dotychczasowy audyt in-memory.
        entry = self.fallback.log(
            event_type=event_type,
            message=message,
            payload=payload,
        )

        # Obecny AuditEvent nie ma kolumny payload/message.
        self.repository.record(
            event_type=event_type,
            operation=event_type,
            decision="record",
            allowed=True,
            reason=message,
        )

        return entry

    def export(self) -> list[dict[str, Any]]:
        return self.fallback.export()
