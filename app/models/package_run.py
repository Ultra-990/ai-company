"""Immutable package identity and observed isolated execution history."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.task import utc_now


class PackageRun(Base):
    __tablename__='package_runs'
    id:Mapped[int]=mapped_column(primary_key=True)
    request_id:Mapped[str]=mapped_column(String(36),unique=True)
    task_id:Mapped[int]=mapped_column(ForeignKey('tasks.id'),index=True)
    package_id:Mapped[int]=mapped_column(ForeignKey('artifacts.id'),index=True)
    package_checksum:Mapped[str]=mapped_column(String(64))
    container_name:Mapped[str]=mapped_column(String(64),unique=True)
    state:Mapped[str]=mapped_column(String(32),index=True)
    profile:Mapped[dict]=mapped_column(JSON)
    result:Mapped[dict]=mapped_column(JSON,default=dict)
    report_id:Mapped[int|None]=mapped_column(ForeignKey('artifacts.id'),nullable=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utc_now)
    finished_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
