from datetime import datetime

from pydantic import Field, model_validator

from app.schemas.common import ApiModel, NormalizedRole, StableId


class MemberCreate(ApiModel):
    person_id: StableId
    role: NormalizedRole
    responsibilities: str = Field(default="", max_length=2000)


class MemberUpdate(ApiModel):
    role: NormalizedRole | None = None
    responsibilities: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_valid_change(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one Member field to update.")

        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError("Member update fields cannot be null.")

        return self


class MemberRead(ApiModel):
    id: str
    person_id: StableId
    role: NormalizedRole
    responsibilities: str
    created_at: datetime
    updated_at: datetime
