from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TaskMigration(Base):
    __tablename__ = "task_migrations"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "source_record_id",
            name="uq_task_migration_source_record",
        ),
        Index("ix_task_migrations_space_id", "space_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    space_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "spaces.id",
            ondelete="RESTRICT",
            name="fk_task_migrations_space_id",
        ),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    source_record_id: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )
    task_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    migrated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
