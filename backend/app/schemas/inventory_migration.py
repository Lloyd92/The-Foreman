from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from app.schemas.common import ApiModel
from app.schemas.inventory import InventoryCreate


class BrowserInventoryRecord(InventoryCreate):
    id: str = Field(min_length=1, max_length=36)
    created_at: datetime
    updated_at: datetime | None = None


class InventoryMigrationRequest(ApiModel):
    records: list[dict[str, Any]] = Field(max_length=5000)


class InventoryMigrationError(ApiModel):
    index: int
    source_record_id: str | None
    reason: str


class InventoryMigrationResponse(ApiModel):
    status: Literal["success", "partial", "failed"]
    migrated: int
    already_migrated: int
    duplicates: int
    malformed: int
    confirmed_source_ids: list[str]
    errors: list[InventoryMigrationError]
    browser_data_retained: Literal[True] = True
