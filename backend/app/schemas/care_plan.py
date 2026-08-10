from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import (
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.schemas.common import ApiModel


CarePlanName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=120,
    ),
]
RequiredCareText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
    ),
]
OptionalIdentifier = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=36,
    ),
]


class CarePlanCreate(ApiModel):
    name: CarePlanName
    care_type: RequiredCareText = Field(max_length=30)
    tool_id: OptionalIdentifier | None = None
    description: str = Field(default="", max_length=2000)
    frequency_value: int | None = Field(default=None, gt=0)
    frequency_unit: RequiredCareText | None = Field(
        default=None,
        max_length=30,
    )
    notes: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def require_frequency_pair(self):
        if (
            self.frequency_value is None
        ) != (
            self.frequency_unit is None
        ):
            raise ValueError(
                "Frequency value and unit must be provided together."
            )

        return self


class CarePlanUpdate(ApiModel):
    name: CarePlanName | None = None
    care_type: RequiredCareText | None = Field(
        default=None,
        max_length=30,
    )
    tool_id: OptionalIdentifier | None = None
    description: str | None = Field(
        default=None,
        max_length=2000,
    )
    frequency_value: int | None = Field(default=None, gt=0)
    frequency_unit: RequiredCareText | None = Field(
        default=None,
        max_length=30,
    )
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_valid_change(self):
        fields = self.model_fields_set

        if not fields:
            raise ValueError(
                "Provide at least one Care Plan field to update."
            )

        for field in (
            "name",
            "care_type",
            "description",
            "notes",
        ):
            if field in fields and getattr(self, field) is None:
                raise ValueError(
                    "Care Plan non-nullable fields cannot be null."
                )

        frequency_fields = {
            "frequency_value",
            "frequency_unit",
        }
        supplied_frequency_fields = fields & frequency_fields

        if (
            supplied_frequency_fields
            and supplied_frequency_fields != frequency_fields
        ):
            raise ValueError(
                "Frequency value and unit must be changed together."
            )

        if supplied_frequency_fields:
            if (
                self.frequency_value is None
            ) != (
                self.frequency_unit is None
            ):
                raise ValueError(
                    "Frequency value and unit must both be set "
                    "or both be null."
                )

        return self


class CarePlanListQuery(ApiModel):
    search: str | None = Field(default=None, max_length=120)
    care_type: str | None = Field(default=None, max_length=30)
    tool_id: OptionalIdentifier | None = None
    sort_by: Literal[
        "name",
        "careType",
    ] = "name"
    sort_direction: Literal["asc", "desc"] = "asc"


def stored_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


class CarePlanRead(ApiModel):
    id: str
    name: str
    care_type: str
    tool_id: str | None
    description: str
    frequency_value: int | None
    frequency_unit: str | None
    notes: str
    created_at: datetime
    updated_at: datetime

    @field_validator(
        "created_at",
        "updated_at",
    )
    @classmethod
    def normalize_stored_timestamp(
        cls,
        value: datetime,
    ) -> datetime:
        return stored_utc(value)
