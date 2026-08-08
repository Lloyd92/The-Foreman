from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from app.schemas.common import ApiModel, StableId

TaskPriority = Literal["high", "medium", "low"]
TaskTitle = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=120,
    ),
]


class TaskCreate(ApiModel):
    title: TaskTitle
    priority: TaskPriority = "medium"
    project_id: str | None = Field(default=None, max_length=36)
    due_date: date | None = None
    responsible_member_id: StableId | None = None


class TaskUpdate(ApiModel):
    title: TaskTitle | None = None
    priority: TaskPriority | None = None
    project_id: str | None = Field(default=None, max_length=36)
    due_date: date | None = None
    responsible_member_id: StableId | None = None

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one task field to update.")

        return self


class TaskRead(ApiModel):
    id: str
    title: str
    priority: TaskPriority
    completed: bool
    project_id: str | None
    due_date: date | None
    responsible_member_id: str | None
    created_at: datetime
    updated_at: datetime
