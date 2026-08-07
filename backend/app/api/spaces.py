from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.space_context import ActiveSpaceDependency
from app.schemas.space import (
    SpaceCreate,
    SpaceRead,
    SpaceUpdate,
)
from app.services import spaces as space_service


router = APIRouter(prefix="/api/spaces", tags=["spaces"])
SessionDependency = Annotated[Session, Depends(get_session)]


def space_error(error: Exception) -> HTTPException:
    if isinstance(error, space_service.SpaceNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "SPACE_NOT_FOUND",
                "message": str(error),
            },
        )

    if isinstance(error, space_service.SpaceNameConflictError):
        code = "SPACE_NAME_CONFLICT"
    elif isinstance(error, space_service.DefaultSpaceProtectedError):
        code = "DEFAULT_SPACE_PROTECTED"
    elif isinstance(error, space_service.SpaceInUseError):
        code = "SPACE_IN_USE"
    else:
        raise TypeError("Unsupported Space service error.")

    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": code,
            "message": str(error),
        },
    )


@router.get("", response_model=list[SpaceRead])
def list_spaces(
    session: SessionDependency,
) -> list[SpaceRead]:
    return space_service.list_spaces(session)


@router.post(
    "",
    response_model=SpaceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_space(
    data: SpaceCreate,
    session: SessionDependency,
) -> SpaceRead:
    try:
        return space_service.create_space(session, data)
    except space_service.SpaceNameConflictError as error:
        raise space_error(error) from error


@router.get("/active", response_model=SpaceRead)
def read_active_space(
    active_space: ActiveSpaceDependency,
) -> SpaceRead:
    return SpaceRead.model_validate(active_space)


@router.get("/{space_id}", response_model=SpaceRead)
def read_space(
    space_id: str,
    session: SessionDependency,
) -> SpaceRead:
    try:
        return space_service.require_space(session, space_id)
    except space_service.SpaceNotFoundError as error:
        raise space_error(error) from error


@router.patch("/{space_id}", response_model=SpaceRead)
def update_space(
    space_id: str,
    data: SpaceUpdate,
    session: SessionDependency,
) -> SpaceRead:
    try:
        return space_service.update_space(
            session,
            space_id,
            data,
        )
    except (
        space_service.SpaceNotFoundError,
        space_service.SpaceNameConflictError,
    ) as error:
        raise space_error(error) from error


@router.delete(
    "/{space_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_space(
    space_id: str,
    session: SessionDependency,
) -> Response:
    try:
        space_service.delete_space(session, space_id)
    except (
        space_service.SpaceNotFoundError,
        space_service.DefaultSpaceProtectedError,
        space_service.SpaceInUseError,
    ) as error:
        raise space_error(error) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)
