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


class WorkDependency(Base):
    __tablename__ = "work_dependencies"
    __table_args__ = (
        CheckConstraint(
            "dependent_type IN ('task', 'project')",
            name="ck_work_dependencies_dependent_type",
        ),
        CheckConstraint(
            "prerequisite_type IN ('task', 'project')",
            name="ck_work_dependencies_prerequisite_type",
        ),
        CheckConstraint(
            "dependent_type != prerequisite_type "
            "OR dependent_id != prerequisite_id",
            name="ck_work_dependencies_not_self",
        ),
        UniqueConstraint(
            "space_id",
            "dependent_type",
            "dependent_id",
            "prerequisite_type",
            "prerequisite_id",
            name="uq_work_dependencies_relationship",
        ),
        Index(
            "ix_work_dependencies_space_id",
            "space_id",
        ),
        Index(
            "ix_work_dependencies_dependent",
            "space_id",
            "dependent_type",
            "dependent_id",
        ),
        Index(
            "ix_work_dependencies_prerequisite",
            "space_id",
            "prerequisite_type",
            "prerequisite_id",
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
            name="fk_work_dependencies_space_id",
        ),
        nullable=False,
    )
    dependent_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    dependent_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )
    prerequisite_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    prerequisite_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
