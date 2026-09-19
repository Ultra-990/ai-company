"""Durable owner-requested local image jobs, independent of task completion."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.task import utc_now


class MediaGeneration(Base):
    __tablename__ = 'media_generations'
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36), unique=True)
    task_id: Mapped[int] = mapped_column(ForeignKey('tasks.id'), index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey('projects.id'), nullable=True)
    plan_id: Mapped[int | None] = mapped_column(ForeignKey('plans.id'), nullable=True)
    prompt_id: Mapped[str] = mapped_column(String(36), unique=True)
    state: Mapped[str] = mapped_column(String(24), index=True)
    inputs: Mapped[dict] = mapped_column(JSON)
    context_checksum: Mapped[str] = mapped_column(String(64))
    workflow_checksum: Mapped[str] = mapped_column(String(64))
    artifact_id: Mapped[int | None] = mapped_column(ForeignKey('artifacts.id'), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    review: Mapped[str] = mapped_column(String(24), default='pending')
    review_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
