from datetime import datetime
from typing import Literal

from app.schemas.common import ApiModel, StableId

WorkEndpointType = Literal["task", "project"]


class WorkDependencyCreate(ApiModel):
    dependent_type: WorkEndpointType
    dependent_id: StableId
    prerequisite_type: WorkEndpointType
    prerequisite_id: StableId


class WorkDependencyRead(WorkDependencyCreate):
    id: str
    created_at: datetime
