from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PendingToolExecution(Base):
    """
    Trwały, serwerowy magazyn argumentów oczekującego wykonania narzędzia.

    arguments_json nie może być zwracane przez API ani zapisywane do
    dziennika audytowego. Rekord jest usuwany po zakończeniu próby
    wykonania — zarówno po sukcesie, jak i po błędzie handlera.
    """

    __tablename__ = "pending_tool_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    approval_request_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        unique=True,
        index=True,
    )
    tool_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    arguments_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    arguments_digest: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
