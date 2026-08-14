from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
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


class LibraryRecord(Base):
    __tablename__ = "library_records"
    __table_args__ = (
        CheckConstraint(
            "kind IN "
            "('note', 'document', 'manual', 'receipt', 'photo', "
            "'decision', 'measurement', 'cad_reference')",
            name="ck_library_records_kind",
        ),
        CheckConstraint(
            "length(trim(title)) > 0",
            name="ck_library_records_title_not_blank",
        ),
        Index("ix_library_records_space_id", "space_id"),
        Index(
            "ix_library_records_space_kind",
            "space_id",
            "kind",
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
            name="fk_library_records_space_id",
        ),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reference_location: Mapped[str] = mapped_column(
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
