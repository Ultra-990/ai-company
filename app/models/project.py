from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utc_now() -> datetime:
    """Zwraca aktualny czas w UTC."""
    return datetime.now(timezone.utc)


class ProjectStatus(str, PyEnum):
    """Status nadrzędnego agregatu projektu."""

    DRAFT = "draft"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ProjectTransitionError(ValueError):
    """Niedozwolona zmiana statusu projektu."""


class Project(Base):
    """
    Nadrzędny agregat biznesowy grupujący przyszłe plany i zadania.

    W tym etapie model nie zmienia jeszcze tabeli tasks. Powiązanie z
    zadaniami zostanie dodane razem z agregatem Plan w osobnym commicie.
    """

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )

    business_goal: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus),
        default=ProjectStatus.DRAFT,
        nullable=False,
        index=True,
    )

    organization_unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("organization_units.id"),
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

    organization_unit: Mapped[object | None] = relationship(
        "OrganizationUnit",
        back_populates="projects",
    )

    plans: Mapped[list[object]] = relationship(
        "Plan",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        if self.status is None:
            self.status = ProjectStatus.DRAFT

    tasks: Mapped[list[object]] = relationship(
        "Task",
        back_populates="project",
    )

    def transition_to(self, new_status: ProjectStatus) -> None:
        """Zmienia status projektu wyłącznie zgodnie z jego cyklem życia."""

        allowed_transitions: dict[
            ProjectStatus,
            set[ProjectStatus],
        ] = {
            ProjectStatus.DRAFT: {
                ProjectStatus.PLANNED,
                ProjectStatus.CANCELLED,
            },
            ProjectStatus.PLANNED: {
                ProjectStatus.IN_PROGRESS,
                ProjectStatus.BLOCKED,
                ProjectStatus.CANCELLED,
            },
            ProjectStatus.IN_PROGRESS: {
                ProjectStatus.COMPLETED,
                ProjectStatus.BLOCKED,
                ProjectStatus.CANCELLED,
            },
            ProjectStatus.BLOCKED: {
                ProjectStatus.PLANNED,
                ProjectStatus.IN_PROGRESS,
                ProjectStatus.CANCELLED,
            },
            ProjectStatus.COMPLETED: set(),
            ProjectStatus.CANCELLED: set(),
        }

        if new_status not in allowed_transitions[self.status]:
            raise ProjectTransitionError(
                "Niedozwolona zmiana statusu projektu: "
                f"{self.status.value} → {new_status.value}"
            )

        now = utc_now()
        self.status = new_status
        self.updated_at = now

        if (
            new_status is ProjectStatus.IN_PROGRESS
            and self.started_at is None
        ):
            self.started_at = now

        if new_status is ProjectStatus.COMPLETED:
            self.completed_at = now
