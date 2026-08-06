from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InventoryItem(Base):
    __tablename__ = "inventory_items"
    __table_args__ = (
        Index("ix_inventory_items_space_id", "space_id"),
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
            name="fk_inventory_items_space_id",
        ),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        index=True,
    )
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    minimum: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    location: Mapped[str] = mapped_column(String(100), nullable=False)
    cost: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    supplier: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
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
