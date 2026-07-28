from sqlalchemy import asc, desc, or_, select
from sqlalchemy.orm import Session

from app.models.inventory import InventoryItem

SORT_FIELDS = {
    "name": InventoryItem.name,
    "quantity": InventoryItem.quantity,
    "category": InventoryItem.category,
}


def list_inventory(
    session: Session,
    *,
    search: str | None = None,
    category: str | None = None,
    sort_by: str = "name",
    sort_direction: str = "asc",
) -> list[InventoryItem]:
    statement = select(InventoryItem)

    if search:
        pattern = f"%{search}%"
        statement = statement.where(
            or_(
                InventoryItem.name.ilike(pattern),
                InventoryItem.category.ilike(pattern),
                InventoryItem.location.ilike(pattern),
                InventoryItem.supplier.ilike(pattern),
            )
        )

    if category:
        statement = statement.where(InventoryItem.category == category)

    sort_column = SORT_FIELDS[sort_by]
    order = desc(sort_column) if sort_direction == "desc" else asc(sort_column)
    statement = statement.order_by(order, asc(InventoryItem.name))
    return list(session.scalars(statement))


def get_inventory_item(
    session: Session,
    inventory_item_id: str,
) -> InventoryItem | None:
    return session.get(InventoryItem, inventory_item_id)


def add_inventory_item(
    session: Session,
    item: InventoryItem,
) -> InventoryItem:
    session.add(item)
    session.flush()
    session.refresh(item)
    return item


def inventory_names_by_ids(
    session: Session,
    inventory_item_ids: set[str],
) -> dict[str, str]:
    if not inventory_item_ids:
        return {}

    statement = select(
        InventoryItem.id,
        InventoryItem.name,
    ).where(InventoryItem.id.in_(inventory_item_ids))
    return {
        inventory_item_id: name
        for inventory_item_id, name in session.execute(statement)
    }
