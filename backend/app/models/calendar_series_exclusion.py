from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CalendarSeriesExclusion(Base):
    __tablename__ = "calendar_series_exclusions"
    __table_args__ = (
        UniqueConstraint(
            "space_id",
            "series_id",
            "excluded_date",
            name="uq_calendar_series_exclusions_occurrence",
        ),
        Index(
            "ix_calendar_series_exclusions_space_id",
            "space_id",
        ),
        Index(
            "ix_calendar_series_exclusions_series",
            "space_id",
            "series_id",
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
            name="fk_calendar_series_exclusions_space_id",
        ),
        nullable=False,
    )
    series_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "calendar_series.id",
            ondelete="CASCADE",
            name="fk_calendar_series_exclusions_series_id",
        ),
        nullable=False,
    )
    excluded_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
