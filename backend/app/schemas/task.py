from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from app.schemas.common import ApiModel

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


class TaskUpdate(ApiModel):
    title: TaskTitle | None = None
    priority: TaskPriority | None = None
    project_id: str | None = Field(default=None, max_length=36)

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
    created_at: datetime
    updated_at: datetime
