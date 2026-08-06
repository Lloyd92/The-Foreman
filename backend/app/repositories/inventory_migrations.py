from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inventory_migration import InventoryMigration

SOURCE = "browser-local"


def get_browser_migration(
    session: Session,
    source_record_id: str,
) -> InventoryMigration | None:
    statement = select(InventoryMigration).where(
        InventoryMigration.source == SOURCE,
        InventoryMigration.source_record_id == source_record_id,
    )
    return session.scalar(statement)


def add_browser_migration(
    session: Session,
    *,
    space_id: str,
    source_record_id: str,
    inventory_item_id: str,
) -> InventoryMigration:
    migration = InventoryMigration(
        space_id=space_id,
        source=SOURCE,
        source_record_id=source_record_id,
        inventory_item_id=inventory_item_id,
    )
    session.add(migration)
    session.flush()
    return migration
