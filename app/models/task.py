from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utc_now() -> datetime:
    """Zwraca aktualny czas w UTC."""
    return datetime.now(timezone.utc)


class TaskStatus(str, PyEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TaskPriority(str, PyEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus),
        default=TaskStatus.PENDING,
        nullable=False,
        index=True,
    )

    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority),
        default=TaskPriority.NORMAL,
        nullable=False,
        index=True,
    )

    assigned_agent: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    progress: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    stages: Mapped[list[dict]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    def update_progress(self, progress: int) -> None:
        """
        Aktualizuje postęp zadania i automatycznie zmienia jego status.
        """

        if not 0 <= progress <= 100:
            raise ValueError(
                "Postęp musi mieścić się w zakresie 0–100"
            )

        self.progress = progress
        self.updated_at = utc_now()

        if progress == 100:
            self.status = TaskStatus.COMPLETED

        elif progress > 0 and self.status == TaskStatus.PENDING:
            self.status = TaskStatus.IN_PROGRESS

        elif progress == 0 and self.status == TaskStatus.IN_PROGRESS:
            self.status = TaskStatus.PENDING
