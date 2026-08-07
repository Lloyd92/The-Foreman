from datetime import datetime
from typing import Annotated

from pydantic import Field, StringConstraints, model_validator

from app.schemas.common import ApiModel

SpaceName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=120,
    ),
]


class SpaceCreate(ApiModel):
    name: SpaceName
    description: str = Field(default="", max_length=2000)


class SpaceUpdate(ApiModel):
    name: SpaceName | None = None
    description: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_valid_change(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one Space field to update.")

        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError("Space update fields cannot be null.")

        return self


class SpaceRead(ApiModel):
    id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
