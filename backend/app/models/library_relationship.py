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


class LibraryRelationship(Base):
    __tablename__ = "library_relationships"
    __table_args__ = (
        CheckConstraint(
            "target_type IN ("
            "'task', 'project', "
            "'tool', 'inventory', 'care_plan', 'tool_maintenance_record', "
            "'calendar_entry', 'calendar_series', "
            "'money_account', 'money_category', 'money_transaction', "
            "'money_budget', 'money_obligation', "
            "'person', 'organization'"
            ")",
            name="ck_library_relationships_target_type",
        ),
        UniqueConstraint(
            "space_id",
            "library_record_id",
            "target_type",
            "target_id",
            name="uq_library_relationships_relationship",
        ),
        Index("ix_library_relationships_space_id", "space_id"),
        Index(
            "ix_library_relationships_record",
            "space_id",
            "library_record_id",
        ),
        Index(
            "ix_library_relationships_target",
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
            name="fk_library_relationships_space_id",
        ),
        nullable=False,
    )
    library_record_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "library_records.id",
            ondelete="CASCADE",
            name="fk_library_relationships_library_record_id",
        ),
        nullable=False,
    )
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
