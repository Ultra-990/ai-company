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


class ApprovalStatus(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"



class TaskTransitionError(ValueError):
    """Niedozwolona zmiana statusu zadania."""




class TaskPriority(str, PyEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class ResourceClass(str, PyEnum):
    LIGHT = "light"
    CPU = "cpu"
    CPU_HEAVY = "cpu_heavy"
    GPU_LIGHT = "gpu_light"
    GPU_HEAVY = "gpu_heavy"
    NETWORK = "network"
    RESTRICTED = "restricted"


class RiskLevel(str, PyEnum):
    LOW = "low"
    MEDIUM = "medium"
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

    approval_status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus),
        default=ApprovalStatus.PENDING,
        nullable=False,
        index=True,
    )

    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority),
        default=TaskPriority.NORMAL,
        nullable=False,
        index=True,
    )

    resource_class: Mapped[ResourceClass] = mapped_column(
        Enum(ResourceClass),
        default=ResourceClass.LIGHT,
        nullable=False,
        index=True,
    )

    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel),
        default=RiskLevel.LOW,
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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if self.stages is None:
            self.stages = []

    def validate_stages(self) -> None:
        """Waliduje strukturę etapów zadania."""

        if not isinstance(self.stages, list):
            raise ValueError("Etapy zadania muszą być listą.")

        allowed_statuses = {"planned", "in_progress", "completed"}

        for index, stage in enumerate(self.stages):
            if not isinstance(stage, dict):
                raise ValueError(
                    f"Etap nr {index} musi być słownikiem."
                )

            required_fields = {"id", "name", "status", "progress", "items"}
            missing_fields = required_fields - stage.keys()

            if missing_fields:
                raise ValueError(
                    f"Etap nr {index} nie zawiera pól: "
                    f"{', '.join(sorted(missing_fields))}."
                )

            if not isinstance(stage["id"], str) or not stage["id"].strip():
                raise ValueError(
                    f"Etap nr {index} ma niepoprawne id."
                )

            if not isinstance(stage["name"], str) or not stage["name"].strip():
                raise ValueError(
                    f"Etap nr {index} ma niepoprawną nazwę."
                )

            if stage["status"] not in allowed_statuses:
                raise ValueError(
                    f"Etap {stage['id']} ma niepoprawny status."
                )

            progress = stage["progress"]

            if isinstance(progress, bool) or not isinstance(progress, int):
                raise ValueError(
                    f"Etap {stage['id']} musi mieć całkowity postęp."
                )

            if not 0 <= progress <= 100:
                raise ValueError(
                    f"Etap {stage['id']} musi mieć postęp od 0 do 100."
                )

            if not isinstance(stage["items"], list):
                raise ValueError(
                    f"Elementy etapu {stage['id']} muszą być listą."
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

    queued_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def transition_to(self, new_status: TaskStatus) -> None:
        """Zmienia status tylko zgodnie z dozwolonym cyklem życia."""

        allowed_transitions: dict[TaskStatus, set[TaskStatus]] = {
            TaskStatus.PENDING: {
                TaskStatus.IN_PROGRESS,
                TaskStatus.BLOCKED,
                TaskStatus.CANCELLED,
            },
            TaskStatus.IN_PROGRESS: {
                TaskStatus.COMPLETED,
                TaskStatus.BLOCKED,
                TaskStatus.CANCELLED,
            },
            TaskStatus.BLOCKED: {
                TaskStatus.IN_PROGRESS,
                TaskStatus.CANCELLED,
            },
            TaskStatus.COMPLETED: set(),
            TaskStatus.CANCELLED: set(),
        }

        if new_status not in allowed_transitions[self.status]:
            raise TaskTransitionError(
                f"Niedozwolona zmiana statusu: "
                f"{self.status.value} → {new_status.value}"
            )

        self.status = new_status
        now = utc_now()

        if new_status is TaskStatus.IN_PROGRESS and self.started_at is None:
            self.started_at = now

        if new_status is TaskStatus.COMPLETED:
            self.progress = 100
            self.completed_at = now

        self.updated_at = now




    def update_progress(self, progress: int) -> None:
        """
        Aktualizuje postęp zadania i automatycznie zmienia jego status.
        """

        if not 0 <= progress <= 100:
            raise ValueError(
                "Postęp musi mieścić się w zakresie 0–100"
            )

        now = utc_now()

        self.progress = progress
        self.updated_at = now

        if progress == 100:
            self.status = TaskStatus.COMPLETED

            if self.started_at is None:
                self.started_at = now

            self.completed_at = now

        elif progress > 0 and self.status == TaskStatus.PENDING:
            self.status = TaskStatus.IN_PROGRESS

            if self.started_at is None:
                self.started_at = now

        elif progress == 0 and self.status == TaskStatus.IN_PROGRESS:
            self.status = TaskStatus.PENDING
