"""Planning assignments, deliberately separate from execution authorization."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.project import utc_now
from app.models.organization_os import Agent  # register agents table for standalone repositories


class TaskDelegation(Base):
    __tablename__ = "task_delegations"

    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("organization_units.id"), nullable=False)
    manager_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), nullable=False)
    worker_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), nullable=False)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), nullable=False)
    predecessor_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    execution_brief: Mapped[str] = mapped_column(Text, nullable=False)
    completion_criterion: Mapped[str] = mapped_column(Text, nullable=False)
    policy: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_by: Mapped[str] = mapped_column(String(32), default="owner", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
