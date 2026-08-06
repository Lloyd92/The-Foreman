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


class ProjectMigration(Base):
    __tablename__ = "project_migrations"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "source_record_id",
            name="uq_project_migration_source_record",
        ),
        Index("ix_project_migrations_space_id", "space_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    space_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "spaces.id",
            ondelete="RESTRICT",
            name="fk_project_migrations_space_id",
        ),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    source_record_id: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )
    project_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    payload_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    migrated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
