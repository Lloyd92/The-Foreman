from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.project import (
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
)
from app.services import projects as project_service

router = APIRouter(prefix="/api/projects", tags=["projects"])
SessionDependency = Annotated[Session, Depends(get_session)]


def project_error(error: Exception) -> HTTPException:
    if isinstance(error, LookupError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )

    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=str(error),
    )


@router.get("", response_model=list[ProjectRead])
def list_projects(
    session: SessionDependency,
    include_archived: Annotated[
        bool,
        Query(alias="includeArchived"),
    ] = False,
) -> list[ProjectRead]:
    return project_service.list_projects(
        session,
        include_archived=include_archived,
    )


@router.post(
    "",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
)
def create_project(
    data: ProjectCreate,
    session: SessionDependency,
) -> ProjectRead:
    return project_service.create_project(session, data)


@router.get("/{project_id}", response_model=ProjectRead)
def read_project(
    project_id: str,
    session: SessionDependency,
) -> ProjectRead:
    try:
        return project_service.require_project(session, project_id)
    except LookupError as error:
        raise project_error(error) from error


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: str,
    data: ProjectUpdate,
    session: SessionDependency,
) -> ProjectRead:
    try:
        return project_service.update_project(
            session,
            project_id,
            data,
        )
    except (LookupError, ValueError) as error:
        raise project_error(error) from error


@router.post(
    "/{project_id}/archive",
    response_model=ProjectRead,
)
def archive_project(
    project_id: str,
    session: SessionDependency,
) -> ProjectRead:
    try:
        return project_service.archive_project(
            session,
            project_id,
        )
    except LookupError as error:
        raise project_error(error) from error
