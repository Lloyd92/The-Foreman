from datetime import datetime
from typing import Annotated

from pydantic import Field, StringConstraints

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


class PersonRead(ApiModel):
    id: str
    display_name: str
    given_name: str
    family_name: str
    description: str
    created_at: datetime
    updated_at: datetime
