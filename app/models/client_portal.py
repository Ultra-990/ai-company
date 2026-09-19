"""Explicitly published client snapshots, separate from internal project data."""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ClientShare(Base):
    __tablename__ = "client_portal_shares"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    token_digest: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    public_content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ClientPublicationRevision(Base):
    __tablename__ = "client_publication_revisions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    share_id: Mapped[int] = mapped_column(ForeignKey("client_portal_shares.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    public_content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


class ClientActivity(Base):
    __tablename__ = "client_portal_activity"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    share_id: Mapped[int] = mapped_column(ForeignKey("client_portal_shares.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    stage_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    publication_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


class ClientFeedback(Base):
    """Explicit decision by bearer of a client code; never an internal task review."""
    __tablename__ = "client_stage_feedback"
    __table_args__ = (
        UniqueConstraint("share_id", "request_id", name="uq_client_feedback_request"),
        UniqueConstraint("share_id", "publication_checksum", "stage_index", name="uq_client_feedback_version_stage"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    share_id: Mapped[int] = mapped_column(ForeignKey("client_portal_shares.id"), index=True)
    request_id: Mapped[str] = mapped_column(String(36))
    publication_checksum: Mapped[str] = mapped_column(String(64), index=True)
    stage_index: Mapped[int] = mapped_column(Integer)
    stage_title: Mapped[str] = mapped_column(String(200))
    stage_snapshot: Mapped[str] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(String(30))
    comment: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    owner_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
