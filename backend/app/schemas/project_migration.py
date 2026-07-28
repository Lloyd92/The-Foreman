from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.project import ProjectCreate, ProjectRead


class BrowserProjectMigrationRequest(ProjectCreate):
    source_record_id: str = Field(min_length=1, max_length=120)
    created_at: datetime
    updated_at: datetime | None = None


class ProjectMigrationResponse(ProjectRead):
    migration_status: Literal["migrated", "already-migrated"]
    source_record_id: str
