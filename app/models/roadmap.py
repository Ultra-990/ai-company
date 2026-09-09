from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utc_now() -> datetime:
    """Zwraca aktualny czas w UTC."""
    return datetime.now(timezone.utc)


class RoadmapItemStatus(str, PyEnum):
    """Dozwolone statusy trwałego stanu punktu roadmapy."""

    PLANNED = "planned"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RoadmapItemState(Base):
    """
    Trwały stan pojedynczego punktu z docs/roadmap.yaml.

    item_id odpowiada identyfikatorowi z phases[].items[].id, np.
    ``roadmap_automation.api``. Definicja struktury pozostaje w YAML,
    natomiast bieżący stan, dowody i notatki są przechowywane w SQLite.
    """

    __tablename__ = "roadmap_item_states"

    item_id: Mapped[str] = mapped_column(
        String(200),
        primary_key=True,
    )

    status: Mapped[RoadmapItemStatus] = mapped_column(
        Enum(RoadmapItemStatus),
        nullable=False,
        default=RoadmapItemStatus.PLANNED,
        index=True,
    )

    evidence: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
        index=True,
    )
