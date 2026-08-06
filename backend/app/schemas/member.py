from datetime import datetime

from pydantic import Field

from app.schemas.common import ApiModel, NormalizedRole, StableId


class MemberCreate(ApiModel):
    space_id: StableId
    person_id: StableId
    role: NormalizedRole
    responsibilities: str = Field(default="", max_length=2000)


class MemberRead(MemberCreate):
    id: str
    created_at: datetime
    updated_at: datetime
