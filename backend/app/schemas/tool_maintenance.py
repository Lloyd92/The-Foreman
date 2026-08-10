from datetime import datetime, timezone
from typing import Annotated

from pydantic import (
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.schemas.common import ApiModel


MaintenanceType = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=30,
    ),
]


def require_aware_utc(
    value: datetime | None,
) -> datetime | None:
    if value is None:
        return None

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(
            "Maintenance performedAt must include a timezone."
        )

    return value.astimezone(timezone.utc)


def stored_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


class ToolMaintenanceCreate(ApiModel):
    maintenance_type: MaintenanceType
    performed_at: datetime
    notes: str = Field(default="", max_length=2000)

    @field_validator("performed_at")
    @classmethod
    def validate_performed_at(
        cls,
        value: datetime,
    ) -> datetime:
        return require_aware_utc(value)


class ToolMaintenanceUpdate(ApiModel):
    maintenance_type: MaintenanceType | None = None
    performed_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("performed_at")
    @classmethod
    def validate_performed_at(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        return require_aware_utc(value)

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError(
                "Provide at least one maintenance field to update."
            )

        if any(
            getattr(self, field) is None
            for field in self.model_fields_set
        ):
            raise ValueError(
                "Maintenance fields cannot be null."
            )

        return self


class ToolMaintenanceRead(ApiModel):
    id: str
    tool_id: str
    maintenance_type: str
    performed_at: datetime
    notes: str
    created_at: datetime

    @field_validator(
        "performed_at",
        "created_at",
    )
    @classmethod
    def normalize_stored_timestamp(
        cls,
        value: datetime,
    ) -> datetime:
        return stored_utc(value)
