from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
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


class MoneyCategory(Base):
    __tablename__ = "money_categories"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('income', 'expense')",
            name="ck_money_categories_kind",
        ),
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_money_categories_name_not_blank",
        ),
        UniqueConstraint(
            "space_id",
            "kind",
            "name",
            name="uq_money_categories_space_kind_name",
        ),
        Index("ix_money_categories_space_id", "space_id"),
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
            name="fk_money_categories_space_id",
        ),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
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
