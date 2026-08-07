from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.space_context import ActiveSpaceDependency
from app.schemas.member import MemberCreate, MemberRead, MemberUpdate
from app.services import members as members_service
from app.services import people as people_service


router = APIRouter(prefix="/api/members", tags=["members"])
SessionDependency = Annotated[Session, Depends(get_session)]


def member_error(error: Exception) -> HTTPException:
    if isinstance(error, members_service.MemberNotFoundError):
        code = "MEMBER_NOT_FOUND"
        response_status = status.HTTP_404_NOT_FOUND
    elif isinstance(error, members_service.MemberAlreadyExistsError):
        code = "MEMBER_ALREADY_EXISTS"
        response_status = status.HTTP_409_CONFLICT
    elif isinstance(error, people_service.PersonNotFoundError):
        code = "PERSON_NOT_FOUND"
        response_status = status.HTTP_404_NOT_FOUND
    else:
        raise TypeError("Unsupported Member service error.")

    return HTTPException(
        status_code=response_status,
        detail={
            "code": code,
            "message": str(error),
        },
    )


@router.get("", response_model=list[MemberRead])
def list_members(
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> list[MemberRead]:
    return members_service.list_members(session, active_space)


@router.post(
    "",
    response_model=MemberRead,
    status_code=status.HTTP_201_CREATED,
)
def create_member(
    data: MemberCreate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> MemberRead:
    try:
        return members_service.create_member(
            session,
            active_space,
            data,
        )
    except (
        members_service.MemberAlreadyExistsError,
        people_service.PersonNotFoundError,
    ) as error:
        raise member_error(error) from error


@router.get("/{member_id}", response_model=MemberRead)
def read_member(
    member_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> MemberRead:
    try:
        return members_service.require_member(
            session,
            active_space,
            member_id,
        )
    except members_service.MemberNotFoundError as error:
        raise member_error(error) from error


@router.patch("/{member_id}", response_model=MemberRead)
def update_member(
    member_id: str,
    data: MemberUpdate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> MemberRead:
    try:
        return members_service.update_member(
            session,
            active_space,
            member_id,
            data,
        )
    except members_service.MemberNotFoundError as error:
        raise member_error(error) from error


@router.delete(
    "/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_member(
    member_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> Response:
    try:
        members_service.delete_member(
            session,
            active_space,
            member_id,
        )
    except members_service.MemberNotFoundError as error:
        raise member_error(error) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)
