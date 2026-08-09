from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ToolMaintenanceRecord(Base):
    __tablename__ = "tool_maintenance_records"
    __table_args__ = (
        Index("ix_tool_maintenance_records_space_id", "space_id"),
        Index(
            "ix_tool_maintenance_records_tool_performed",
            "tool_id",
            "performed_at",
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
            name="fk_tool_maintenance_records_space_id",
        ),
        nullable=False,
    )
    tool_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "tools.id",
            ondelete="RESTRICT",
            name="fk_tool_maintenance_records_tool_id",
        ),
        nullable=False,
    )
    maintenance_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )
    performed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    notes: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
