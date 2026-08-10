from datetime import datetime, timezone
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.schemas.common import ApiModel, StableId


WorkToolWorkType = Literal["task", "project"]


def stored_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


class WorkToolRequirementCreate(ApiModel):
    work_type: WorkToolWorkType
    work_id: StableId
    tool_id: StableId
    note: str = Field(default="", max_length=500)


class WorkToolRequirementUpdate(ApiModel):
    tool_id: StableId | None = None
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError(
                "Provide at least one Tool requirement field "
                "to update."
            )

        if any(
            getattr(self, field) is None
            for field in self.model_fields_set
        ):
            raise ValueError(
                "Tool requirement fields cannot be null."
            )

        return self


class WorkToolRequirementListQuery(ApiModel):
    work_type: WorkToolWorkType | None = None
    work_id: StableId | None = None
    tool_id: StableId | None = None


class WorkToolRequirementRead(ApiModel):
    id: str
    work_type: WorkToolWorkType
    work_id: str
    tool_id: str
    tool_name: str | None
    tool_exists: bool
    note: str
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(
        cls,
        value: datetime,
    ) -> datetime:
        return stored_utc(value)
