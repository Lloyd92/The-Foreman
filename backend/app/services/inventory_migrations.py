from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models.inventory import InventoryItem
from app.repositories.inventory import add_inventory_item, get_inventory_item
from app.repositories.inventory_migrations import (
    add_browser_migration,
    get_browser_migration,
)
from app.schemas.inventory_migration import (
    BrowserInventoryRecord,
    InventoryMigrationError,
    InventoryMigrationResponse,
)


def get_source_record_id(raw_record: dict[str, Any]) -> str | None:
    value = raw_record.get("id")
    return value if isinstance(value, str) and value.strip() else None


def migrate_browser_inventory(
    session: Session,
    raw_records: list[dict[str, Any]],
) -> InventoryMigrationResponse:
    migrated = 0
    already_migrated = 0
    duplicates = 0
    malformed = 0
    confirmed_source_ids: list[str] = []
    errors: list[InventoryMigrationError] = []

    try:
        for index, raw_record in enumerate(raw_records):
            source_record_id = get_source_record_id(raw_record)

            try:
                record = BrowserInventoryRecord.model_validate(raw_record)
            except ValidationError as error:
                malformed += 1
                errors.append(
                    InventoryMigrationError(
                        index=index,
                        source_record_id=source_record_id,
                        reason=str(error),
                    )
                )
                continue

            migration = get_browser_migration(session, record.id)

            if migration is not None:
                already_migrated += 1
                confirmed_source_ids.append(record.id)
                continue

            if get_inventory_item(session, record.id) is not None:
                duplicates += 1
                errors.append(
                    InventoryMigrationError(
                        index=index,
                        source_record_id=record.id,
                        reason=(
                            "A backend inventory item already uses this ID. "
                            "The existing item was not overwritten."
                        ),
                    )
                )
                continue

            item_data = record.model_dump(
                exclude={"id", "created_at", "updated_at"}
            )
            item = InventoryItem(
                id=record.id,
                created_at=record.created_at,
                updated_at=record.updated_at or record.created_at,
                **item_data,
            )
            add_inventory_item(session, item)
            add_browser_migration(
                session,
                source_record_id=record.id,
                inventory_item_id=item.id,
            )
            migrated += 1
            confirmed_source_ids.append(record.id)

        session.commit()
    except Exception:
        session.rollback()
        raise

    if errors and not (migrated or already_migrated):
        migration_status = "failed"
    elif errors:
        migration_status = "partial"
    else:
        migration_status = "success"

    return InventoryMigrationResponse(
        status=migration_status,
        migrated=migrated,
        already_migrated=already_migrated,
        duplicates=duplicates,
        malformed=malformed,
        confirmed_source_ids=confirmed_source_ids,
        errors=errors,
        browser_data_retained=True,
    )
