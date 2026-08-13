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


class MoneyTransaction(Base):
    __tablename__ = "money_transactions"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('income', 'expense')",
            name="ck_money_transactions_kind",
        ),
        CheckConstraint(
            "amount_minor > 0",
            name="ck_money_transactions_amount_positive",
        ),
        CheckConstraint(
            "length(currency_code) = 3 "
            "AND currency_code = upper(currency_code) "
            "AND currency_code NOT GLOB '*[^A-Z]*'",
            name="ck_money_transactions_currency_code",
        ),
        CheckConstraint(
            "length(trim(description)) > 0",
            name="ck_money_transactions_description_not_blank",
        ),
        Index("ix_money_transactions_space_id", "space_id"),
        Index(
            "ix_money_transactions_space_occurred_on",
            "space_id",
            "occurred_on",
        ),
        Index(
            "ix_money_transactions_space_account",
            "space_id",
            "account_id",
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
            name="fk_money_transactions_space_id",
        ),
        nullable=False,
    )
    account_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "money_accounts.id",
            ondelete="RESTRICT",
            name="fk_money_transactions_account_id",
        ),
        nullable=False,
    )
    category_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "money_categories.id",
            ondelete="SET NULL",
            name="fk_money_transactions_category_id",
        ),
        nullable=True,
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_code: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="USD",
    )
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    counterparty: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
        default="",
    )
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
