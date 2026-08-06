from datetime import datetime
from typing import Annotated

from pydantic import Field, StringConstraints

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


class SpaceRead(ApiModel):
    id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
