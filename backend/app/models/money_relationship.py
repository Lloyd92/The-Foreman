from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MoneyRelationship(Base):
    __tablename__ = "money_relationships"
    __table_args__ = (
        CheckConstraint(
            "money_type IN "
            "('account', 'category', 'transaction', 'budget', 'obligation')",
            name="ck_money_relationships_money_type",
        ),
        CheckConstraint(
            "target_type IN "
            "('task', 'project', 'tool', 'inventory', 'person', 'organization')",
            name="ck_money_relationships_target_type",
        ),
        UniqueConstraint(
            "space_id",
            "money_type",
            "money_id",
            "target_type",
            "target_id",
            name="uq_money_relationships_relationship",
        ),
        Index("ix_money_relationships_space_id", "space_id"),
        Index(
            "ix_money_relationships_money",
            "space_id",
            "money_type",
            "money_id",
        ),
        Index(
            "ix_money_relationships_target",
            "space_id",
            "target_type",
            "target_id",
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
            name="fk_money_relationships_space_id",
        ),
        nullable=False,
    )
    money_type: Mapped[str] = mapped_column(String(20), nullable=False)
    money_id: Mapped[str] = mapped_column(String(36), nullable=False)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
