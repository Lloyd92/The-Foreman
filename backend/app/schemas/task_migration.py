from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from app.schemas.common import ApiModel
from app.schemas.task import TaskPriority, TaskTitle


class BrowserTaskRecord(ApiModel):
    id: str = Field(min_length=1, max_length=36)
    title: TaskTitle
    priority: TaskPriority
    completed: bool
    created_at: datetime
    project_id: str | None = Field(default=None, max_length=36)


class TaskMigrationRequest(ApiModel):
    records: list[dict[str, Any]] = Field(max_length=5000)


class TaskMigrationError(ApiModel):
    index: int
    source_record_id: str | None
    reason: str


class TaskMigrationResponse(ApiModel):
    status: Literal["success", "partial", "failed"]
    migrated: int
    already_migrated: int
    skipped: int
    confirmed_source_ids: list[str]
    errors: list[TaskMigrationError]
    browser_data_retained: Literal[True] = True
