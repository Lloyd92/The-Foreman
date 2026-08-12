from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CalendarEntry(Base):
    __tablename__ = "calendar_entries"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('commitment', 'event', 'availability')",
            name="ck_calendar_entries_kind",
        ),
        CheckConstraint(
            "length(trim(title)) > 0",
            name="ck_calendar_entries_title_not_blank",
        ),
        CheckConstraint(
            "length(trim(timezone_name)) > 0",
            name="ck_calendar_entries_timezone_not_blank",
        ),
        CheckConstraint(
            "("
            "all_day = 1 "
            "AND start_date IS NOT NULL "
            "AND end_date IS NOT NULL "
            "AND end_date > start_date "
            "AND start_at IS NULL "
            "AND end_at IS NULL"
            ") OR ("
            "all_day = 0 "
            "AND start_date IS NULL "
            "AND end_date IS NULL "
            "AND start_at IS NOT NULL "
            "AND end_at IS NOT NULL "
            "AND end_at > start_at"
            ")",
            name="ck_calendar_entries_time_shape",
        ),
        Index("ix_calendar_entries_space_id", "space_id"),
        Index("ix_calendar_entries_member_id", "member_id"),
        Index(
            "ix_calendar_entries_space_start_at",
            "space_id",
            "start_at",
        ),
        Index(
            "ix_calendar_entries_space_start_date",
            "space_id",
            "start_date",
        ),
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
            name="fk_calendar_entries_space_id",
        ),
        nullable=False,
    )
    member_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "members.id",
            ondelete="SET NULL",
            name="fk_calendar_entries_member_id",
        ),
        nullable=True,
    )
    kind: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
    )
    all_day: Mapped[bool] = mapped_column(
        Boolean(create_constraint=False),
        nullable=False,
        default=False,
    )
    start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    start_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    timezone_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    location: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        default="",
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
