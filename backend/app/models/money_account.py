from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Boolean,
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


class MoneyAccount(Base):
    __tablename__ = "money_accounts"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('cash', 'checking', 'savings', 'credit', 'loan', 'other')",
            name="ck_money_accounts_kind",
        ),
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_money_accounts_name_not_blank",
        ),
        CheckConstraint(
            "length(currency_code) = 3 "
            "AND currency_code = upper(currency_code) "
            "AND currency_code NOT GLOB '*[^A-Z]*'",
            name="ck_money_accounts_currency_code",
        ),
        Index("ix_money_accounts_space_id", "space_id"),
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
            name="fk_money_accounts_space_id",
        ),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    currency_code: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="USD",
    )
    opening_balance_minor: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean(create_constraint=False),
        nullable=False,
        default=True,
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
