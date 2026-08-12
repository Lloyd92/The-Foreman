from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from app.schemas.common import ApiModel


CalendarTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=160),
]

TimezoneName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]


class CalendarSettingsUpdate(ApiModel):
    timezone_name: TimezoneName


class CalendarSettingsRead(ApiModel):
    timezone_name: str
    created_at: datetime
    updated_at: datetime


class CalendarEntryCreate(ApiModel):
    member_id: str | None = None
    kind: Literal["commitment", "event", "availability"]
    title: CalendarTitle
    all_day: bool = False
    start_at: datetime | None = None
    end_at: datetime | None = None
    start_date: date | None = None
    end_date: date | None = None
    location: str = Field(default="", max_length=200)
    notes: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def validate_time_shape(self):
        if self.all_day:
            if self.start_date is None or self.end_date is None:
                raise ValueError("All-day entries require start and end dates.")
            if self.end_date <= self.start_date:
                raise ValueError("All-day end date must follow start date.")
            if self.start_at is not None or self.end_at is not None:
                raise ValueError("All-day entries cannot contain timed values.")
        else:
            if self.start_at is None or self.end_at is None:
                raise ValueError("Timed entries require start and end times.")
            if self.start_date is not None or self.end_date is not None:
                raise ValueError("Timed entries cannot contain all-day dates.")

        return self


class CalendarEntryUpdate(ApiModel):
    member_id: str | None = None
    kind: Literal["commitment", "event", "availability"] | None = None
    title: CalendarTitle | None = None
    all_day: bool | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    start_date: date | None = None
    end_date: date | None = None
    location: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one Calendar field to update.")
        return self


class CalendarEntryRead(ApiModel):
    id: str
    member_id: str | None
    kind: str
    title: str
    all_day: bool
    start_at: datetime | None
    end_at: datetime | None
    start_date: date | None
    end_date: date | None
    timezone_name: str
    location: str
    notes: str
    created_at: datetime
    updated_at: datetime
