"""Persisted rehearsal queue. It never grants Task execution authorization."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.task import utc_now


class LocalModelJob(Base):
    __tablename__ = 'local_model_jobs'

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36), unique=True)
    task_id: Mapped[int] = mapped_column(ForeignKey('tasks.id'), index=True)
    packet_id: Mapped[int] = mapped_column(ForeignKey('artifacts.id'), unique=True)
    packet_checksum: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(32), default='queued', index=True)
    mode: Mapped[str] = mapped_column(String(32), default='simulation')
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    result_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
