from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.task_migration import (
    TaskMigrationRequest,
    TaskMigrationResponse,
)
from app.services.task_migrations import migrate_browser_tasks

router = APIRouter(
    prefix="/api/task-migrations",
    tags=["task migrations"],
)
SessionDependency = Annotated[Session, Depends(get_session)]


@router.post(
    "/browser",
    response_model=TaskMigrationResponse,
)
def migrate_browser_task_records(
    data: TaskMigrationRequest,
    session: SessionDependency,
) -> TaskMigrationResponse:
    try:
        return migrate_browser_tasks(session, data.records)
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Task migration failed. Browser-local data was retained."
            ),
        ) from error
