from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.space_context import ActiveSpaceDependency
from app.schemas.project import (
    ProjectCreate,
    ProjectMaterialCreate,
    ProjectRead,
    ProjectMaterialUpdate,
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
    active_space: ActiveSpaceDependency,
    include_archived: Annotated[
        bool,
        Query(alias="includeArchived"),
    ] = False,
) -> list[ProjectRead]:
    return project_service.list_projects(
        session,
        active_space,
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
    active_space: ActiveSpaceDependency,
) -> ProjectRead:
    try:
        return project_service.create_project(
            session,
            active_space,
            data,
        )
    except (LookupError, ValueError) as error:
        raise project_error(error) from error


@router.get("/{project_id}", response_model=ProjectRead)
def read_project(
    project_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> ProjectRead:
    try:
        return project_service.read_project(
            session,
            active_space,
            project_id,
        )
    except LookupError as error:
        raise project_error(error) from error


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: str,
    data: ProjectUpdate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> ProjectRead:
    try:
        return project_service.update_project(
            session,
            active_space,
            project_id,
            data,
        )
    except (LookupError, ValueError) as error:
        raise project_error(error) from error


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_project(
    project_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> Response:
    try:
        project_service.delete_project(
            session,
            active_space,
            project_id,
        )
    except LookupError as error:
        raise project_error(error) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{project_id}/materials",
    response_model=ProjectRead,
)
def add_material_requirement(
    project_id: str,
    data: ProjectMaterialCreate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> ProjectRead:
    try:
        return project_service.add_material_requirement(
            session,
            active_space,
            project_id,
            data,
        )
    except (LookupError, ValueError) as error:
        raise project_error(error) from error


@router.patch(
    "/{project_id}/materials/{inventory_item_id}",
    response_model=ProjectRead,
)
def update_material_requirement(
    project_id: str,
    inventory_item_id: str,
    data: ProjectMaterialUpdate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> ProjectRead:
    try:
        return project_service.update_material_requirement(
            session,
            active_space,
            project_id,
            inventory_item_id,
            data,
        )
    except (LookupError, ValueError) as error:
        raise project_error(error) from error


@router.delete(
    "/{project_id}/materials/{inventory_item_id}",
    response_model=ProjectRead,
)
def remove_material_requirement(
    project_id: str,
    inventory_item_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> ProjectRead:
    try:
        return project_service.remove_material_requirement(
            session,
            active_space,
            project_id,
            inventory_item_id,
        )
    except (LookupError, ValueError) as error:
        raise project_error(error) from error


@router.post(
    "/{project_id}/archive",
    response_model=ProjectRead,
    deprecated=True,
)
def archive_project(
    project_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> ProjectRead:
    try:
        return project_service.archive_project(
            session,
            active_space,
            project_id,
        )
    except LookupError as error:
        raise project_error(error) from error
