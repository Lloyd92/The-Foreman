from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InventoryMigration(Base):
    __tablename__ = "inventory_migrations"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "source_record_id",
            name="uq_inventory_migration_source_record",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(120), nullable=False)
    inventory_item_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("inventory_items.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    migrated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
