from datetime import datetime
from typing import Annotated

from pydantic import Field, StringConstraints, model_validator

from app.schemas.common import ApiModel

PersonDisplayName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=120,
    ),
]
PersonNamePart = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        max_length=80,
    ),
]


class PersonCreate(ApiModel):
    display_name: PersonDisplayName
    given_name: PersonNamePart = ""
    family_name: PersonNamePart = ""
    description: str = Field(default="", max_length=2000)


class PersonUpdate(ApiModel):
    display_name: PersonDisplayName | None = None
    given_name: PersonNamePart | None = None
    family_name: PersonNamePart | None = None
    description: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_valid_change(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one Person field to update.")

        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError("Person update fields cannot be null.")

        return self


class PersonRead(ApiModel):
    id: str
    display_name: str
    given_name: str
    family_name: str
    description: str
    created_at: datetime
    updated_at: datetime
