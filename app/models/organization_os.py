from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.organization_os.constants import (
    AgentKind,
    AlertSeverity,
    AlertStatus,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Agent(Base):
    """
    Trwała tożsamość podmiotu działającego w Organization OS.

    Agent może reprezentować właściciela, Brain Core, człowieka,
    wyspecjalizowanego agenta AI lub podmiot zewnętrzny.
    """

    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    agent_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )

    kind: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=AgentKind.AI.value,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    capabilities: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        index=True,
    )


class OrganizationUnitDependency(Base):
    """Jawna zależność pomiędzy dwoma węzłami struktury firmy."""

    __tablename__ = "organization_unit_dependencies"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    source_unit_id: Mapped[int] = mapped_column(
        ForeignKey("organization_units.id"),
        nullable=False,
        index=True,
    )

    target_unit_id: Mapped[int] = mapped_column(
        ForeignKey("organization_units.id"),
        nullable=False,
        index=True,
    )

    relation_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="depends_on",
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class Alert(Base):
    """
    Operacyjny alert Organization OS.

    Alert może wskazywać dział, projekt, zadanie albo agenta. Wszystkie
    powiązania są opcjonalne, ponieważ alert może mieć charakter globalny.
    """

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    organization_unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("organization_units.id"),
        nullable=True,
        index=True,
    )

    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id"),
        nullable=True,
        index=True,
    )

    task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id"),
        nullable=True,
        index=True,
    )

    agent_id: Mapped[int | None] = mapped_column(
        ForeignKey("agents.id"),
        nullable=True,
        index=True,
    )

    severity: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=AlertSeverity.INFO.value,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=AlertStatus.OPEN.value,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    source: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    resolution_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
    )

    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )


class WorkspacePreference(Base):
    """
    Preferencje interfejsu Organization OS.

    Rekord jest przypisany do stabilnego klucza workspace, dzięki czemu
    później może obsłużyć użytkownika, zespół lub osobny widok systemu.
    """

    __tablename__ = "workspace_preferences"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    workspace_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )

    theme: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="arctic-light",
    )

    scene_preferences: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    window_state: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        index=True,
    )
