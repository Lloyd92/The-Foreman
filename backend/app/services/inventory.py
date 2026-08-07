from sqlalchemy.orm import Session

from app.models.inventory import InventoryItem
from app.models.space import Space
from app.repositories import inventory as inventory_repository
from app.schemas.inventory import (
    InventoryCreate,
    InventoryRead,
    InventoryStatus,
    InventoryUpdate,
)


def evaluate_stock(
    quantity: float,
    minimum: float,
) -> tuple[bool, bool, InventoryStatus, str]:
    is_out_of_stock = quantity == 0
    is_low = quantity <= minimum

    if is_out_of_stock:
        return (
            True,
            True,
            "out-of-stock",
            f"Quantity is 0; the low-stock threshold is {minimum:g}.",
        )

    if is_low:
        return (
            True,
            False,
            "low-stock",
            (
                f"Quantity {quantity:g} is at or below the "
                f"low-stock threshold of {minimum:g}."
            ),
        )

    return (
        False,
        False,
        "in-stock",
        (
            f"Quantity {quantity:g} is above the "
            f"low-stock threshold of {minimum:g}."
        ),
    )


def serialize_inventory_item(item: InventoryItem) -> InventoryRead:
    is_low, is_out_of_stock, status, explanation = evaluate_stock(
        item.quantity,
        item.minimum,
    )
    return InventoryRead(
        id=item.id,
        name=item.name,
        category=item.category,
        quantity=item.quantity,
        unit=item.unit,
        minimum=item.minimum,
        location=item.location,
        cost=item.cost,
        supplier=item.supplier,
        notes=item.notes,
        created_at=item.created_at,
        updated_at=item.updated_at,
        is_low=is_low,
        is_out_of_stock=is_out_of_stock,
        status=status,
        explanation=explanation,
    )


def list_inventory(
    session: Session,
    active_space: Space,
    *,
    search: str | None = None,
    category: str | None = None,
    stock: str = "all",
    sort_by: str = "name",
    sort_direction: str = "asc",
) -> list[InventoryRead]:
    items = inventory_repository.list_inventory(
        session,
        active_space.id,
        search=search,
        category=category,
        sort_by="name" if sort_by == "stock" else sort_by,
        sort_direction=sort_direction,
    )
    serialized = [serialize_inventory_item(item) for item in items]

    if stock == "low":
        serialized = [item for item in serialized if item.is_low]
    elif stock == "available":
        serialized = [item for item in serialized if not item.is_low]

    if sort_by == "stock":
        serialized.sort(
            key=lambda item: (
                not item.is_low,
                item.name.casefold(),
            )
        )

    return serialized


def require_inventory_model(
    session: Session,
    active_space: Space,
    inventory_item_id: str,
) -> InventoryItem:
    item = inventory_repository.get_inventory_item(
        session,
        active_space.id,
        inventory_item_id,
    )

    if item is None:
        raise LookupError("Inventory item not found.")

    return item


def require_inventory_item(
    session: Session,
    active_space: Space,
    inventory_item_id: str,
) -> InventoryRead:
    return serialize_inventory_item(
        require_inventory_model(
            session,
            active_space,
            inventory_item_id,
        )
    )


def create_inventory_item(
    session: Session,
    active_space: Space,
    data: InventoryCreate,
) -> InventoryRead:
    item = InventoryItem(
        space_id=active_space.id,
        **data.model_dump(),
    )

    try:
        inventory_repository.add_inventory_item(session, item)
        session.commit()
        session.refresh(item)
    except Exception:
        session.rollback()
        raise

    return serialize_inventory_item(item)


def update_inventory_item(
    session: Session,
    active_space: Space,
    inventory_item_id: str,
    data: InventoryUpdate,
) -> InventoryRead:
    item = require_inventory_model(
        session,
        active_space,
        inventory_item_id,
    )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    try:
        session.commit()
        session.refresh(item)
    except Exception:
        session.rollback()
        raise

    return serialize_inventory_item(item)


def delete_inventory_item(
    session: Session,
    active_space: Space,
    inventory_item_id: str,
) -> None:
    item = require_inventory_model(
        session,
        active_space,
        inventory_item_id,
    )

    try:
        session.delete(item)
        session.commit()
    except Exception:
        session.rollback()
        raise
