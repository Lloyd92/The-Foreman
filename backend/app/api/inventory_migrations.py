from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.space_context import ActiveSpaceDependency
from app.schemas.inventory_migration import (
    InventoryMigrationRequest,
    InventoryMigrationResponse,
)
from app.services.inventory_migrations import migrate_browser_inventory

router = APIRouter(
    prefix="/api/inventory-migrations",
    tags=["inventory-migrations"],
)
SessionDependency = Annotated[Session, Depends(get_session)]


@router.post("/browser", response_model=InventoryMigrationResponse)
def migrate_browser_records(
    data: InventoryMigrationRequest,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> InventoryMigrationResponse:
    try:
        return migrate_browser_inventory(
            session,
            active_space,
            data.records,
        )
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Inventory migration failed and was rolled back. "
                "Browser-local records were not removed."
            ),
        ) from error
