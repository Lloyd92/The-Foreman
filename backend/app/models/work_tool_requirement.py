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


class WorkToolRequirement(Base):
    __tablename__ = "work_tool_requirements"
    __table_args__ = (
        CheckConstraint(
            "work_type IN ('task', 'project')",
            name="ck_work_tool_requirements_work_type",
        ),
        UniqueConstraint(
            "space_id",
            "work_type",
            "work_id",
            "tool_id",
            name="uq_work_tool_requirements_relationship",
        ),
        Index(
            "ix_work_tool_requirements_space_id",
            "space_id",
        ),
        Index(
            "ix_work_tool_requirements_work",
            "space_id",
            "work_type",
            "work_id",
        ),
        Index(
            "ix_work_tool_requirements_tool",
            "space_id",
            "tool_id",
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
            name="fk_work_tool_requirements_space_id",
        ),
        nullable=False,
    )
    work_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    work_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )
    tool_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )
    note: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
