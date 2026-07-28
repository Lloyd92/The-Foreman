from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from app.schemas.common import ApiModel

InventoryName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=120),
]
RequiredInventoryText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
InventoryStatus = Literal["in-stock", "low-stock", "out-of-stock"]


class InventoryCreate(ApiModel):
    name: InventoryName
    category: RequiredInventoryText = Field(max_length=80)
    quantity: float = Field(ge=0)
    unit: RequiredInventoryText = Field(max_length=30)
    minimum: float = Field(ge=0)
    location: RequiredInventoryText = Field(max_length=100)
    cost: float = Field(default=0, ge=0)
    supplier: str = Field(default="", max_length=100)
    notes: str = Field(default="", max_length=500)


class InventoryUpdate(ApiModel):
    name: InventoryName | None = None
    category: RequiredInventoryText | None = Field(default=None, max_length=80)
    quantity: float | None = Field(default=None, ge=0)
    unit: RequiredInventoryText | None = Field(default=None, max_length=30)
    minimum: float | None = Field(default=None, ge=0)
    location: RequiredInventoryText | None = Field(default=None, max_length=100)
    cost: float | None = Field(default=None, ge=0)
    supplier: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one inventory field to update.")

        return self


class InventoryListQuery(ApiModel):
    search: str | None = Field(default=None, max_length=120)
    category: str | None = Field(default=None, max_length=80)
    stock: Literal["all", "low", "available"] = "all"
    sort_by: Literal["name", "quantity", "category", "stock"] = "name"
    sort_direction: Literal["asc", "desc"] = "asc"


class InventoryRead(ApiModel):
    id: str
    name: str
    category: str
    quantity: float
    unit: str
    minimum: float
    location: str
    cost: float
    supplier: str
    notes: str
    created_at: datetime
    updated_at: datetime
    is_low: bool
    is_out_of_stock: bool
    status: InventoryStatus
    explanation: str
