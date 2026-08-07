from datetime import datetime
from typing import Annotated

from pydantic import Field, StringConstraints, model_validator

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


class OrganizationUpdate(ApiModel):
    name: OrganizationName | None = None
    description: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_valid_change(self):
        if not self.model_fields_set:
            raise ValueError(
                "Provide at least one Organization field to update."
            )

        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(
                    "Organization update fields cannot be null."
                )

        return self


class OrganizationRead(ApiModel):
    id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime


class OrganizationSpaceRelationshipCreate(ApiModel):
    organization_id: StableId
    role: NormalizedRole


class OrganizationSpaceRelationshipUpdate(ApiModel):
    role: NormalizedRole | None = None

    @model_validator(mode="after")
    def require_valid_change(self):
        if not self.model_fields_set:
            raise ValueError(
                "Provide at least one Organization relationship field "
                "to update."
            )

        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(
                    "Organization relationship update fields cannot be "
                    "null."
                )

        return self


class OrganizationSpaceRelationshipRead(
    OrganizationSpaceRelationshipCreate
):
    id: str
    created_at: datetime
    updated_at: datetime
