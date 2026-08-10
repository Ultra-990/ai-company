from __future__ import annotations

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import (
    Base,
    create_database_engine,
    create_session_factory,
)
from app.models.audit import AuditEvent


class AuditRepository:
    """Warstwa trwałego zapisu i odczytu bezpiecznych zdarzeń audytowych."""

    def __init__(
        self,
        database_url: str,
        *,
        initialize: bool = True,
    ) -> None:
        self._engine: Engine = create_database_engine(database_url)
        self._session_factory: sessionmaker[Session] = (
            create_session_factory(self._engine)
        )

        if initialize:
            Base.metadata.create_all(self._engine)

    def record(
        self,
        *,
        event_type: str,
        operation: str,
        decision: str,
        allowed: bool,
        reason: str,
    ) -> AuditEvent:
        event = AuditEvent(
            event_type=event_type,
            operation=operation,
            decision=decision,
            allowed=allowed,
            reason=reason,
        )

        with self._session_factory() as session:
            session.add(event)
            session.commit()
            session.refresh(event)
            session.expunge(event)

        return event

    def list_recent(self, *, limit: int = 50) -> list[AuditEvent]:
        if not 1 <= limit <= 100:
            raise ValueError("limit musi mieścić się w zakresie 1–100")

        statement = (
            select(AuditEvent)
            .order_by(
                AuditEvent.created_at.desc(),
                AuditEvent.id.desc(),
            )
            .limit(limit)
        )

        with self._session_factory() as session:
            events = list(session.scalars(statement).all())

            for event in events:
                session.expunge(event)

        return events

    def close(self) -> None:
        self._engine.dispose()
