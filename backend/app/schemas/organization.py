from datetime import datetime
from typing import Annotated

from pydantic import Field, StringConstraints

from app.schemas.common import ApiModel, NormalizedRole, StableId

OrganizationName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=120,
    ),
]


class OrganizationCreate(ApiModel):
    name: OrganizationName
    description: str = Field(default="", max_length=2000)


class OrganizationRead(ApiModel):
    id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime


class OrganizationSpaceRelationshipCreate(ApiModel):
    space_id: StableId
    organization_id: StableId
    role: NormalizedRole


class OrganizationSpaceRelationshipRead(
    OrganizationSpaceRelationshipCreate
):
    id: str
    created_at: datetime
    updated_at: datetime
