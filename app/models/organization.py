from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OrganizationUnit(Base):
    """
    Jednostka organizacyjna firmy.

    Jednostki mogą tworzyć hierarchię za pomocą pola parent_id:
    np. firma → dział → zespół.
    """

    __tablename__ = "organization_units"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )

    unit_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("organization_units.id"),
        nullable=True,
        index=True,
    )

    manager_agent: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    parent: Mapped[OrganizationUnit | None] = relationship(
        "OrganizationUnit",
        remote_side="OrganizationUnit.id",
        back_populates="children",
    )

    children: Mapped[list[OrganizationUnit]] = relationship(
        "OrganizationUnit",
        back_populates="parent",
    )
