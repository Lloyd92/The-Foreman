from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.project_migration import (
    BrowserProjectMigrationRequest,
    ProjectMigrationResponse,
)
from app.services.project_migrations import (
    ProjectMigrationConflictError,
    ProjectMigrationGoneError,
    migrate_browser_project,
)

router = APIRouter(
    prefix="/api/project-migrations",
    tags=["project migrations"],
)
SessionDependency = Annotated[Session, Depends(get_session)]


@router.post(
    "/browser",
    response_model=ProjectMigrationResponse,
    status_code=status.HTTP_201_CREATED,
)
def migrate_browser_project_record(
    data: BrowserProjectMigrationRequest,
    session: SessionDependency,
    response: Response,
) -> ProjectMigrationResponse:
    try:
        result = migrate_browser_project(session, data)
    except ProjectMigrationConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except ProjectMigrationGoneError as error:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    if result.migration_status == "already-migrated":
        response.status_code = status.HTTP_200_OK

    return result
