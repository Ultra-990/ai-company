from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ApprovalRequestStatus(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalRequest(Base):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if self.status is None:
            self.status = ApprovalRequestStatus.PENDING

    __tablename__ = "approval_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    operation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ApprovalRequestStatus] = mapped_column(
        Enum(ApprovalRequestStatus),
        default=ApprovalRequestStatus.PENDING,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
