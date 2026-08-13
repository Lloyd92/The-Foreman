from datetime import date, datetime, timezone
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
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MoneyObligation(Base):
    __tablename__ = "money_obligations"
    __table_args__ = (
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_money_obligations_name_not_blank",
        ),
        CheckConstraint(
            "amount_minor > 0",
            name="ck_money_obligations_amount_positive",
        ),
        CheckConstraint(
            "frequency IN ('once', 'weekly', 'monthly', 'yearly')",
            name="ck_money_obligations_frequency",
        ),
        CheckConstraint(
            "interval_value > 0",
            name="ck_money_obligations_interval_positive",
        ),
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_money_obligations_date_range",
        ),
        CheckConstraint(
            "length(currency_code) = 3 "
            "AND currency_code = upper(currency_code) "
            "AND currency_code NOT GLOB '*[^A-Z]*'",
            name="ck_money_obligations_currency_code",
        ),
        Index("ix_money_obligations_space_id", "space_id"),
        Index(
            "ix_money_obligations_space_start_date",
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
            name="fk_money_obligations_space_id",
        ),
        nullable=False,
    )
    account_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "money_accounts.id",
            ondelete="SET NULL",
            name="fk_money_obligations_account_id",
        ),
        nullable=True,
    )
    category_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "money_categories.id",
            ondelete="SET NULL",
            name="fk_money_obligations_category_id",
        ),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_code: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="USD",
    )
    frequency: Mapped[str] = mapped_column(String(20), nullable=False)
    interval_value: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
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
