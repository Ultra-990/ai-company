from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PlanStatus(str, PyEnum):
    """Status planu realizowanego w ramach projektu."""

    DRAFT = "draft"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PlanTransitionError(ValueError):
    """Niedozwolona zmiana statusu planu."""


class Plan(Base):
    """
    Plan wykonawczy należący do jednego projektu.

    W bieżącym etapie Plan nie posiada jeszcze relacji do Task.
    Powiązanie z zadaniami zostanie dodane w kolejnym kroku.
    """

    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )

    objective: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[PlanStatus] = mapped_column(
        Enum(PlanStatus),
        default=PlanStatus.DRAFT,
        nullable=False,
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

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    project: Mapped[object] = relationship(
        "Project",
        back_populates="plans",
    )

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        if self.status is None:
            self.status = PlanStatus.DRAFT

    tasks: Mapped[list[object]] = relationship(
        "Task",
        back_populates="plan",
    )

    def transition_to(self, new_status: PlanStatus) -> None:
        """Wymusza poprawny cykl życia planu."""

        allowed_transitions: dict[PlanStatus, set[PlanStatus]] = {
            PlanStatus.DRAFT: {
                PlanStatus.READY,
                PlanStatus.CANCELLED,
            },
            PlanStatus.READY: {
                PlanStatus.IN_PROGRESS,
                PlanStatus.BLOCKED,
                PlanStatus.CANCELLED,
            },
            PlanStatus.IN_PROGRESS: {
                PlanStatus.COMPLETED,
                PlanStatus.BLOCKED,
                PlanStatus.CANCELLED,
            },
            PlanStatus.BLOCKED: {
                PlanStatus.READY,
                PlanStatus.IN_PROGRESS,
                PlanStatus.CANCELLED,
            },
            PlanStatus.COMPLETED: set(),
            PlanStatus.CANCELLED: set(),
        }

        if new_status not in allowed_transitions[self.status]:
            raise PlanTransitionError(
                "Niedozwolona zmiana statusu planu: "
                f"{self.status.value} → {new_status.value}"
            )

        now = utc_now()
        self.status = new_status
        self.updated_at = now

        if (
            new_status is PlanStatus.IN_PROGRESS
            and self.started_at is None
        ):
            self.started_at = now

        if new_status is PlanStatus.COMPLETED:
            self.completed_at = now
