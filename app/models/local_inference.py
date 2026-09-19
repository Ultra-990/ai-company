"""Real inference provenance, separate from rehearsal and task acceptance."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.task import utc_now


class LocalInference(Base):
    __tablename__ = 'local_inference_runs'
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36), unique=True)
    task_id: Mapped[int] = mapped_column(ForeignKey('tasks.id'), index=True)
    packet_id: Mapped[int] = mapped_column(ForeignKey('artifacts.id'), unique=True)
    packet_checksum: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(32), default='queued', index=True)
    model: Mapped[str] = mapped_column(String(120))
    model_digest: Mapped[str] = mapped_column(String(64))
    limits: Mapped[dict] = mapped_column(JSON)
    result_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    attempt_id: Mapped[int | None] = mapped_column(ForeignKey('task_attempts.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
