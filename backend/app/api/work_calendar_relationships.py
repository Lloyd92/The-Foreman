from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.space_context import ActiveSpaceDependency
from app.schemas.work_calendar_relationship import (
    WorkCalendarRelationshipCreate,
    WorkCalendarRelationshipRead,
    WorkCalendarRelationshipUpdate,
)
from app.services import (
    work_calendar_relationships as relationship_service,
)


router = APIRouter(
    prefix="/api/work-calendar-relationships",
    tags=["work-calendar-relationships"],
)
SessionDependency = Annotated[Session, Depends(get_session)]


def relationship_error(error: Exception) -> HTTPException:
    if isinstance(
        error,
        relationship_service.WorkCalendarRelationshipNotFoundError,
    ):
        code = "WORK_CALENDAR_RELATIONSHIP_NOT_FOUND"
        response_status = status.HTTP_404_NOT_FOUND
    elif isinstance(
        error,
        relationship_service.WorkCalendarRelationshipWorkNotFoundError,
    ):
        code = "WORK_CALENDAR_RELATIONSHIP_WORK_NOT_FOUND"
        response_status = status.HTTP_404_NOT_FOUND
    elif isinstance(
        error,
        relationship_service.WorkCalendarRelationshipCalendarNotFoundError,
    ):
        code = "WORK_CALENDAR_RELATIONSHIP_CALENDAR_NOT_FOUND"
        response_status = status.HTTP_404_NOT_FOUND
    elif isinstance(
        error,
        relationship_service.WorkCalendarRelationshipAlreadyExistsError,
    ):
        code = "WORK_CALENDAR_RELATIONSHIP_ALREADY_EXISTS"
        response_status = status.HTTP_409_CONFLICT
    else:
        raise TypeError("Unsupported Work Calendar relationship error.")

    return HTTPException(
        status_code=response_status,
        detail={"code": code, "message": str(error)},
    )


@router.get("", response_model=list[WorkCalendarRelationshipRead])
def list_relationships(
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
):
    return relationship_service.list_relationships(
        session,
        active_space,
    )


@router.post(
    "",
    response_model=WorkCalendarRelationshipRead,
    status_code=status.HTTP_201_CREATED,
)
def create_relationship(
    data: WorkCalendarRelationshipCreate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
):
    try:
        return relationship_service.create_relationship(
            session, active_space, data
        )
    except (
        relationship_service.WorkCalendarRelationshipWorkNotFoundError,
        relationship_service.WorkCalendarRelationshipCalendarNotFoundError,
        relationship_service.WorkCalendarRelationshipAlreadyExistsError,
    ) as error:
        raise relationship_error(error) from error


@router.patch(
    "/{relationship_id}",
    response_model=WorkCalendarRelationshipRead,
)
def update_relationship(
    relationship_id: str,
    data: WorkCalendarRelationshipUpdate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
):
    try:
        return relationship_service.update_relationship(
            session, active_space, relationship_id, data
        )
    except relationship_service.WorkCalendarRelationshipNotFoundError as error:
        raise relationship_error(error) from error


@router.delete(
    "/{relationship_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_relationship(
    relationship_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> Response:
    try:
        relationship_service.delete_relationship(
            session, active_space, relationship_id
        )
    except relationship_service.WorkCalendarRelationshipNotFoundError as error:
        raise relationship_error(error) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{relationship_id}",
    response_model=WorkCalendarRelationshipRead,
)
def read_relationship(
    relationship_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
):
    try:
        value = relationship_service.require_relationship_model(
            session,
            active_space,
            relationship_id,
        )
        return relationship_service.serialize_relationship(
            session,
            active_space,
            value,
        )
    except relationship_service.WorkCalendarRelationshipNotFoundError as error:
        raise relationship_error(error) from error
