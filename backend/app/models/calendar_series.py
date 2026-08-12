from datetime import date, datetime, time, timezone
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CalendarSeries(Base):
    __tablename__ = "calendar_series"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('commitment', 'event', 'availability')",
            name="ck_calendar_series_kind",
        ),
        CheckConstraint(
            "length(trim(title)) > 0",
            name="ck_calendar_series_title_not_blank",
        ),
        CheckConstraint(
            "length(trim(timezone_name)) > 0",
            name="ck_calendar_series_timezone_not_blank",
        ),
        CheckConstraint(
            "frequency IN ('daily', 'weekly')",
            name="ck_calendar_series_frequency",
        ),
        CheckConstraint(
            "interval_value > 0",
            name="ck_calendar_series_interval_positive",
        ),
        CheckConstraint(
            "duration_minutes > 0",
            name="ck_calendar_series_duration_positive",
        ),
        CheckConstraint(
            "weekday_mask >= 0 AND weekday_mask <= 127",
            name="ck_calendar_series_weekday_mask_range",
        ),
        CheckConstraint(
            "("
            "frequency = 'daily' AND weekday_mask = 0"
            ") OR ("
            "frequency = 'weekly' "
            "AND weekday_mask >= 1 "
            "AND weekday_mask <= 127"
            ")",
            name="ck_calendar_series_weekday_shape",
        ),
        CheckConstraint(
            "end_date IS NULL OR end_date >= anchor_date",
            name="ck_calendar_series_end_date",
        ),
        Index("ix_calendar_series_space_id", "space_id"),
        Index("ix_calendar_series_member_id", "member_id"),
        Index(
            "ix_calendar_series_space_anchor_date",
            "space_id",
            "anchor_date",
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
            name="fk_calendar_series_space_id",
        ),
        nullable=False,
    )
    member_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "members.id",
            ondelete="SET NULL",
            name="fk_calendar_series_member_id",
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
    frequency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )
    interval_value: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    weekday_mask: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    anchor_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    local_start_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )
    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
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
