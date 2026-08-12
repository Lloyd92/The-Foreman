from datetime import datetime, timezone
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.schemas.common import ApiModel, StableId


WorkType = Literal["task", "project"]
CalendarType = Literal["entry", "series"]


class WorkCalendarRelationshipCreate(ApiModel):
    work_type: WorkType
    work_id: StableId
    calendar_type: CalendarType
    calendar_id: StableId
    note: str = Field(default="", max_length=500)


class WorkCalendarRelationshipUpdate(ApiModel):
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set or self.note is None:
            raise ValueError("Provide a non-null relationship field.")
        return self


class WorkCalendarRelationshipRead(ApiModel):
    id: str
    work_type: WorkType
    work_id: str
    calendar_type: CalendarType
    calendar_id: str
    calendar_exists: bool
    note: str
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
