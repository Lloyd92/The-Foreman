from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.inventory import (
    InventoryCreate,
    InventoryListQuery,
    InventoryRead,
    InventoryUpdate,
)
from app.services import inventory as inventory_service

router = APIRouter(prefix="/api/inventory", tags=["inventory"])
SessionDependency = Annotated[Session, Depends(get_session)]


def not_found(error: LookupError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=str(error),
    )


@router.get("", response_model=list[InventoryRead])
def list_inventory(
    session: SessionDependency,
    filters: Annotated[InventoryListQuery, Query()],
) -> list[InventoryRead]:
    return inventory_service.list_inventory(
        session,
        search=filters.search.strip() if filters.search else None,
        category=filters.category,
        stock=filters.stock,
        sort_by=filters.sort_by,
        sort_direction=filters.sort_direction,
    )


@router.post(
    "",
    response_model=InventoryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_inventory_item(
    data: InventoryCreate,
    session: SessionDependency,
) -> InventoryRead:
    return inventory_service.create_inventory_item(session, data)


@router.get("/{inventory_item_id}", response_model=InventoryRead)
def read_inventory_item(
    inventory_item_id: str,
    session: SessionDependency,
) -> InventoryRead:
    try:
        return inventory_service.require_inventory_item(
            session,
            inventory_item_id,
        )
    except LookupError as error:
        raise not_found(error) from error


@router.patch("/{inventory_item_id}", response_model=InventoryRead)
def update_inventory_item(
    inventory_item_id: str,
    data: InventoryUpdate,
    session: SessionDependency,
) -> InventoryRead:
    try:
        return inventory_service.update_inventory_item(
            session,
            inventory_item_id,
            data,
        )
    except LookupError as error:
        raise not_found(error) from error


@router.delete(
    "/{inventory_item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_inventory_item(
    inventory_item_id: str,
    session: SessionDependency,
) -> Response:
    try:
        inventory_service.delete_inventory_item(
            session,
            inventory_item_id,
        )
    except LookupError as error:
        raise not_found(error) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)
