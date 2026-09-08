from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ArtifactType(str, PyEnum):
    """Rodzaj audytowalnego rezultatu pracy."""

    REPORT = "report"
    RESEARCH = "research"
    PLAN = "plan"
    SPECIFICATION = "specification"
    SOURCE_CODE = "source_code"
    TEST_RESULT = "test_result"
    DEMO = "demo"
    SCREENSHOT = "screenshot"
    DEPLOYMENT = "deployment"
    OTHER = "other"


class Artifact(Base):
    """
    Trwały, audytowalny rezultat pracy wykonanej w systemie.

    Artefakt może być przypisany do projektu, planu, zadania i opcjonalnie
    do konkretnej próby wykonania zadania. Relacje są nullable, aby możliwe
    było rejestrowanie wyników powstałych na różnych poziomach workflow.
    """

    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id"),
        nullable=True,
        index=True,
    )

    plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("plans.id"),
        nullable=True,
        index=True,
    )

    task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id"),
        nullable=True,
        index=True,
    )

    task_attempt_id: Mapped[int | None] = mapped_column(
        ForeignKey("task_attempts.id"),
        nullable=True,
        index=True,
    )

    artifact_type: Mapped[ArtifactType] = mapped_column(
        Enum(ArtifactType),
        nullable=False,
        default=ArtifactType.OTHER,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    uri: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )

    content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    checksum: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    created_by: Mapped[str | None] = mapped_column(
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

    project: Mapped[object | None] = relationship(
        "Project",
        back_populates="artifacts",
    )

    plan: Mapped[object | None] = relationship(
        "Plan",
        back_populates="artifacts",
    )

    task: Mapped[object | None] = relationship(
        "Task",
        back_populates="artifacts",
    )

    task_attempt: Mapped[object | None] = relationship(
        "TaskAttempt",
        back_populates="artifacts",
    )
