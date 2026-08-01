from datetime import date, datetime, timedelta
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator

from app.schemas.common import ApiModel


def _canonical_text_key(value: str) -> tuple[str, str]:
    return (value.casefold(), value)


def _require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Export timestamps must be timezone-aware.")

    if value.utcoffset() != timedelta(0):
        raise ValueError("Export timestamps must use UTC.")

    return value


class ExportRecordCounts(ApiModel):
    projects: int = Field(strict=True, ge=0)
    project_material_requirements: int = Field(strict=True, ge=0)
    tasks: int = Field(strict=True, ge=0)
    inventory_items: int = Field(strict=True, ge=0)


class ExportProjectMaterial(ApiModel):
    inventory_item_id: str
    required_quantity: float = Field(allow_inf_nan=False)
    note: str


class ExportProject(ApiModel):
    id: str
    name: str
    type: str
    status: str
    priority: str
    progress: float = Field(allow_inf_nan=False)
    start_date: date | None
    target_date: date | None
    estimated_cost: float = Field(allow_inf_nan=False)
    description: str
    notes: str
    materials: list[ExportProjectMaterial]
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None

    @field_validator("created_at", "updated_at", "archived_at")
    @classmethod
    def require_utc_timestamp(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is None:
            return None

        return _require_utc(value)

    @model_validator(mode="after")
    def require_canonical_material_order(self) -> Self:
        material_ids = [
            material.inventory_item_id
            for material in self.materials
        ]

        if material_ids != sorted(
            material_ids,
            key=_canonical_text_key,
        ):
            raise ValueError(
                "Project materials must use canonical ID ordering."
            )

        return self


class ExportTask(ApiModel):
    id: str
    title: str
    priority: str
    completed: bool
    project_id: str | None
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def require_utc_timestamp(
        cls,
        value: datetime,
    ) -> datetime:
        return _require_utc(value)


class ExportInventoryItem(ApiModel):
    id: str
    name: str
    category: str
    quantity: float = Field(allow_inf_nan=False)
    unit: str
    minimum: float = Field(allow_inf_nan=False)
    location: str
    cost: float = Field(allow_inf_nan=False)
    supplier: str
    notes: str
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def require_utc_timestamp(
        cls,
        value: datetime,
    ) -> datetime:
        return _require_utc(value)


class PortableDataExport(ApiModel):
    export_format_version: Literal[1] = 1
    artifact_type: Literal["portable-data-export"] = (
        "portable-data-export"
    )
    restorable: Literal[False] = False
    application_name: Literal["The Foreman"] = "The Foreman"
    application_version: str = Field(min_length=1, max_length=255)
    created_at: datetime
    record_counts: ExportRecordCounts
    projects: list[ExportProject]
    tasks: list[ExportTask]
    inventory_items: list[ExportInventoryItem]

    @field_validator("created_at")
    @classmethod
    def require_utc_created_at(
        cls,
        value: datetime,
    ) -> datetime:
        return _require_utc(value)

    @model_validator(mode="after")
    def validate_canonical_contents(self) -> Self:
        for records, label in (
            (self.projects, "Projects"),
            (self.tasks, "Tasks"),
            (self.inventory_items, "Inventory items"),
        ):
            record_ids = [record.id for record in records]

            if record_ids != sorted(
                record_ids,
                key=_canonical_text_key,
            ):
                raise ValueError(
                    f"{label} must use canonical ID ordering."
                )

        expected_counts = ExportRecordCounts(
            projects=len(self.projects),
            project_material_requirements=sum(
                len(project.materials)
                for project in self.projects
            ),
            tasks=len(self.tasks),
            inventory_items=len(self.inventory_items),
        )

        if self.record_counts != expected_counts:
            raise ValueError(
                "Export record counts must match exported records."
            )

        return self
