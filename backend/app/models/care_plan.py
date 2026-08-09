from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CarePlan(Base):
    __tablename__ = "care_plans"
    __table_args__ = (
        CheckConstraint(
            "("
            "frequency_value IS NULL AND frequency_unit IS NULL"
            ") OR ("
            "frequency_value IS NOT NULL "
            "AND frequency_value > 0 "
            "AND frequency_unit IS NOT NULL"
            ")",
            name="ck_care_plans_frequency_pair",
        ),
        Index("ix_care_plans_space_id", "space_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    space_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "spaces.id",
            ondelete="RESTRICT",
            name="fk_care_plans_space_id",
        ),
        nullable=False,
    )
    tool_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "tools.id",
            ondelete="SET NULL",
            name="fk_care_plans_tool_id",
        ),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    care_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    frequency_value: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    frequency_unit: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )
    notes: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
