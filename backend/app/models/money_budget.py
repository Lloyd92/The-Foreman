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


class MoneyBudget(Base):
    __tablename__ = "money_budgets"
    __table_args__ = (
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_money_budgets_name_not_blank",
        ),
        CheckConstraint(
            "amount_minor > 0",
            name="ck_money_budgets_amount_positive",
        ),
        CheckConstraint(
            "length(currency_code) = 3 "
            "AND currency_code = upper(currency_code) "
            "AND currency_code NOT GLOB '*[^A-Z]*'",
            name="ck_money_budgets_currency_code",
        ),
        CheckConstraint(
            "end_date >= start_date",
            name="ck_money_budgets_date_range",
        ),
        Index("ix_money_budgets_space_id", "space_id"),
        Index(
            "ix_money_budgets_space_dates",
            "space_id",
            "start_date",
            "end_date",
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
            name="fk_money_budgets_space_id",
        ),
        nullable=False,
    )
    category_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "money_categories.id",
            ondelete="SET NULL",
            name="fk_money_budgets_category_id",
        ),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_code: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="USD",
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
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
