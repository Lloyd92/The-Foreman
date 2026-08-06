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


class Member(Base):
    __tablename__ = "members"
    __table_args__ = (
        CheckConstraint(
            "length(role) > 0 "
            "AND role = lower(trim(role)) "
            "AND role NOT GLOB '*[^a-z0-9 -]*' "
            "AND role NOT LIKE '%  %' "
            "AND role NOT LIKE '%--%' "
            "AND role NOT LIKE '% -%' "
            "AND role NOT LIKE '%- %' "
            "AND substr(role, 1, 1) GLOB '[a-z0-9]' "
            "AND substr(role, -1, 1) GLOB '[a-z0-9]'",
            name="ck_members_role_normalized",
        ),
        UniqueConstraint(
            "space_id",
            "person_id",
            name="uq_members_space_person",
        ),
        Index("ix_members_space_id", "space_id"),
        Index("ix_members_person_id", "person_id"),
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
            name="fk_members_space_id",
        ),
        nullable=False,
    )
    person_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "people.id",
            ondelete="RESTRICT",
            name="fk_members_person_id",
        ),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(80, collation="NOCASE"),
        nullable=False,
    )
    responsibilities: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        server_default="",
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
