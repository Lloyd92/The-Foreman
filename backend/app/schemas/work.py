from datetime import date, datetime
from typing import Literal

from app.schemas.common import ApiModel
from app.schemas.work_dependency import WorkDependencyRead

WorkRecordType = Literal["task", "project"]
WorkLifecycleState = Literal[
    "open",
    "planning",
    "active",
    "on-hold",
    "completed",
    "archived",
]
WorkPriority = Literal[
    "low",
    "medium",
    "high",
    "urgent",
]


class WorkItemRead(ApiModel):
    record_type: WorkRecordType
    id: str
    title: str
    lifecycle_state: WorkLifecycleState
    priority: WorkPriority
    progress: float
    start_date: date | None
    target_date: date | None
    due_date: date | None
    responsible_member_id: str | None
    project_id: str | None
    created_at: datetime
    updated_at: datetime


class WorkRead(ApiModel):
    items: list[WorkItemRead]
    dependencies: list[WorkDependencyRead]
