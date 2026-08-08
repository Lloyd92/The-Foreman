from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from app.schemas.common import ApiModel, StableId

ProjectStatus = Literal[
    "planning",
    "active",
    "on-hold",
    "completed",
    "archived",
]
EditableProjectStatus = Literal[
    "planning",
    "active",
    "on-hold",
    "completed",
]
ProjectType = Literal[
    "build",
    "repair",
    "prototype",
    "customer",
    "internal",
    "other",
]
ProjectPriority = Literal[
    "low",
    "medium",
    "high",
    "urgent",
]
ProjectName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=120,
    ),
]
InventoryItemId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=36,
    ),
]


class ProjectMaterialCreate(ApiModel):
    inventory_item_id: InventoryItemId
    required_quantity: float = Field(
        gt=0,
        allow_inf_nan=False,
    )
    note: str = Field(default="", max_length=500)


class ProjectMaterialUpdate(ApiModel):
    required_quantity: float | None = Field(
        default=None,
        gt=0,
        allow_inf_nan=False,
    )
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError(
                "Provide at least one material requirement field to update."
            )

        return self


class ProjectMaterialRead(ApiModel):
    inventory_item_id: str
    required_quantity: float
    note: str


class ProjectCreate(ApiModel):
    name: ProjectName
    type: ProjectType = "other"
    status: EditableProjectStatus = "planning"
    priority: ProjectPriority = "medium"
    progress: float = Field(
        default=0,
        ge=0,
        le=100,
        allow_inf_nan=False,
    )
    start_date: date | None = None
    target_date: date | None = None
    responsible_member_id: StableId | None = None
    estimated_cost: float = Field(
        default=0,
        ge=0,
        allow_inf_nan=False,
    )
    description: str = Field(default="", max_length=2000)
    notes: str = Field(default="", max_length=2000)
    materials: list[ProjectMaterialCreate] = Field(
        default_factory=list,
        max_length=5000,
    )

    @model_validator(mode="after")
    def require_unique_materials(self):
        inventory_ids = [
            material.inventory_item_id
            for material in self.materials
        ]

        if len(inventory_ids) != len(set(inventory_ids)):
            raise ValueError(
                "A project may require each inventory item only once."
            )

        return self


class ProjectUpdate(ApiModel):
    name: ProjectName | None = None
    type: ProjectType | None = None
    status: EditableProjectStatus | None = None
    priority: ProjectPriority | None = None
    progress: float | None = Field(
        default=None,
        ge=0,
        le=100,
        allow_inf_nan=False,
    )
    start_date: date | None = None
    target_date: date | None = None
    responsible_member_id: StableId | None = None
    estimated_cost: float | None = Field(
        default=None,
        ge=0,
        allow_inf_nan=False,
    )
    description: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one project field to update.")

        return self


class ProjectRead(ApiModel):
    id: str
    name: str
    type: ProjectType
    status: ProjectStatus
    priority: ProjectPriority
    progress: float
    start_date: date | None
    target_date: date | None
    responsible_member_id: str | None
    estimated_cost: float
    description: str
    notes: str
    materials: list[ProjectMaterialRead]
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None
