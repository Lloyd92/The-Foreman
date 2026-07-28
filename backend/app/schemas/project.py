from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from app.schemas.common import ApiModel

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
ProjectName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=120,
    ),
]


class ProjectCreate(ApiModel):
    name: ProjectName
    status: EditableProjectStatus = "planning"
    progress: float = Field(default=0, ge=0, le=100)
    notes: str = Field(default="", max_length=2000)


class ProjectUpdate(ApiModel):
    name: ProjectName | None = None
    status: EditableProjectStatus | None = None
    progress: float | None = Field(default=None, ge=0, le=100)
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one project field to update.")

        return self


class ProjectRead(ApiModel):
    id: str
    name: str
    status: ProjectStatus
    progress: float
    notes: str
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None
