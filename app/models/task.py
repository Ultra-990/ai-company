from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


ALLOWED_STATUS_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.PENDING: frozenset({
        TaskStatus.IN_PROGRESS,
        TaskStatus.CANCELLED,
    }),
    TaskStatus.IN_PROGRESS: frozenset({
        TaskStatus.BLOCKED,
        TaskStatus.COMPLETED,
        TaskStatus.CANCELLED,
    }),
    TaskStatus.BLOCKED: frozenset({
        TaskStatus.IN_PROGRESS,
        TaskStatus.CANCELLED,
    }),
    TaskStatus.COMPLETED: frozenset(),
    TaskStatus.CANCELLED: frozenset(),
}


class TaskTransitionError(ValueError):
    """Niedozwolona zmiana statusu zadania."""


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[TaskStatus] = mapped_column(
        SqlEnum(
            TaskStatus,
            values_callable=lambda enum_class: [
                item.value for item in enum_class
            ],
            native_enum=False,
            validate_strings=True,
            length=32,
        ),
        default=TaskStatus.PENDING,
        nullable=False,
        index=True,
    )
    priority: Mapped[TaskPriority] = mapped_column(
        SqlEnum(
            TaskPriority,
            values_callable=lambda enum_class: [
                item.value for item in enum_class
            ],
            native_enum=False,
            validate_strings=True,
            length=16,
        ),
        default=TaskPriority.NORMAL,
        nullable=False,
        index=True,
    )
    assigned_agent: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
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

    def can_transition_to(self, new_status: TaskStatus) -> bool:
        return new_status in ALLOWED_STATUS_TRANSITIONS[self.status]

    def transition_to(self, new_status: TaskStatus) -> None:
        if not self.can_transition_to(new_status):
            raise TaskTransitionError(
                f"Niedozwolone przejście statusu: "
                f"{self.status.value} -> {new_status.value}"
            )

        self.status = new_status
        self.updated_at = utc_now()
