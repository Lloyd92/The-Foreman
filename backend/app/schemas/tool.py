from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from app.schemas.common import ApiModel


ToolName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=120,
    ),
]
RequiredToolText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
    ),
]


class ToolCreate(ApiModel):
    name: ToolName
    category: RequiredToolText = Field(max_length=80)
    condition: RequiredToolText = Field(max_length=30)
    location: RequiredToolText = Field(max_length=100)
    availability: RequiredToolText = Field(max_length=30)
    notes: str = Field(default="", max_length=500)


class ToolUpdate(ApiModel):
    name: ToolName | None = None
    category: RequiredToolText | None = Field(
        default=None,
        max_length=80,
    )
    condition: RequiredToolText | None = Field(
        default=None,
        max_length=30,
    )
    location: RequiredToolText | None = Field(
        default=None,
        max_length=100,
    )
    availability: RequiredToolText | None = Field(
        default=None,
        max_length=30,
    )
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError(
                "Provide at least one Tool field to update."
            )

        if any(
            getattr(self, field) is None
            for field in self.model_fields_set
        ):
            raise ValueError(
                "Tool fields cannot be null."
            )

        return self


class ToolListQuery(ApiModel):
    search: str | None = Field(default=None, max_length=120)
    category: str | None = Field(default=None, max_length=80)
    condition: str | None = Field(default=None, max_length=30)
    availability: str | None = Field(default=None, max_length=30)
    sort_by: Literal[
        "name",
        "category",
        "condition",
        "location",
        "availability",
    ] = "name"
    sort_direction: Literal["asc", "desc"] = "asc"


class ToolRead(ApiModel):
    id: str
    name: str
    category: str
    condition: str
    location: str
    availability: str
    notes: str
    created_at: datetime
    updated_at: datetime
