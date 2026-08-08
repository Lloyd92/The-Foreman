from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.space_context import ActiveSpaceDependency
from app.schemas.work_dependency import (
    WorkDependencyCreate,
    WorkDependencyRead,
)
from app.services import work_dependencies as dependency_service


router = APIRouter(
    prefix="/api/work-dependencies",
    tags=["work-dependencies"],
)
SessionDependency = Annotated[Session, Depends(get_session)]


def work_dependency_error(error: Exception) -> HTTPException:
    if isinstance(
        error,
        dependency_service.WorkDependencyNotFoundError,
    ):
        code = "WORK_DEPENDENCY_NOT_FOUND"
        response_status = status.HTTP_404_NOT_FOUND
    elif isinstance(
        error,
        dependency_service.WorkDependencyEndpointNotFoundError,
    ):
        code = "WORK_DEPENDENCY_ENDPOINT_NOT_FOUND"
        response_status = status.HTTP_404_NOT_FOUND
    elif isinstance(
        error,
        dependency_service.WorkDependencyAlreadyExistsError,
    ):
        code = "WORK_DEPENDENCY_ALREADY_EXISTS"
        response_status = status.HTTP_409_CONFLICT
    elif isinstance(
        error,
        dependency_service.WorkDependencySelfReferenceError,
    ):
        code = "WORK_DEPENDENCY_SELF_REFERENCE"
        response_status = status.HTTP_409_CONFLICT
    elif isinstance(
        error,
        dependency_service.WorkDependencyCycleError,
    ):
        code = "WORK_DEPENDENCY_CYCLE"
        response_status = status.HTTP_409_CONFLICT
    else:
        raise TypeError("Unsupported Work dependency service error.")

    return HTTPException(
        status_code=response_status,
        detail={
            "code": code,
            "message": str(error),
        },
    )


@router.get("", response_model=list[WorkDependencyRead])
def list_work_dependencies(
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> list[WorkDependencyRead]:
    return dependency_service.list_work_dependencies(
        session,
        active_space,
    )


@router.post(
    "",
    response_model=WorkDependencyRead,
    status_code=status.HTTP_201_CREATED,
)
def create_work_dependency(
    data: WorkDependencyCreate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> WorkDependencyRead:
    try:
        return dependency_service.create_work_dependency(
            session,
            active_space,
            data,
        )
    except (
        dependency_service.WorkDependencyEndpointNotFoundError,
        dependency_service.WorkDependencyAlreadyExistsError,
        dependency_service.WorkDependencySelfReferenceError,
        dependency_service.WorkDependencyCycleError,
    ) as error:
        raise work_dependency_error(error) from error


@router.get(
    "/{dependency_id}",
    response_model=WorkDependencyRead,
)
def read_work_dependency(
    dependency_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> WorkDependencyRead:
    try:
        return dependency_service.require_work_dependency(
            session,
            active_space,
            dependency_id,
        )
    except dependency_service.WorkDependencyNotFoundError as error:
        raise work_dependency_error(error) from error


@router.delete(
    "/{dependency_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_work_dependency(
    dependency_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> Response:
    try:
        dependency_service.delete_work_dependency(
            session,
            active_space,
            dependency_id,
        )
    except dependency_service.WorkDependencyNotFoundError as error:
        raise work_dependency_error(error) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)
