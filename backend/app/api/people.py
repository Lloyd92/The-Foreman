from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.person import PersonCreate, PersonRead, PersonUpdate
from app.services import people as people_service


router = APIRouter(prefix="/api/people", tags=["people"])
SessionDependency = Annotated[Session, Depends(get_session)]


def person_error(error: Exception) -> HTTPException:
    if isinstance(error, people_service.PersonNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PERSON_NOT_FOUND",
                "message": str(error),
            },
        )

    if isinstance(error, people_service.PersonInUseError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "PERSON_IN_USE",
                "message": str(error),
            },
        )

    raise TypeError("Unsupported Person service error.")


@router.get("", response_model=list[PersonRead])
def list_people(
    session: SessionDependency,
) -> list[PersonRead]:
    return people_service.list_people(session)


@router.post(
    "",
    response_model=PersonRead,
    status_code=status.HTTP_201_CREATED,
)
def create_person(
    data: PersonCreate,
    session: SessionDependency,
) -> PersonRead:
    return people_service.create_person(session, data)


@router.get("/{person_id}", response_model=PersonRead)
def read_person(
    person_id: str,
    session: SessionDependency,
) -> PersonRead:
    try:
        return people_service.require_person(session, person_id)
    except people_service.PersonNotFoundError as error:
        raise person_error(error) from error


@router.patch("/{person_id}", response_model=PersonRead)
def update_person(
    person_id: str,
    data: PersonUpdate,
    session: SessionDependency,
) -> PersonRead:
    try:
        return people_service.update_person(
            session,
            person_id,
            data,
        )
    except people_service.PersonNotFoundError as error:
        raise person_error(error) from error


@router.delete(
    "/{person_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_person(
    person_id: str,
    session: SessionDependency,
) -> Response:
    try:
        people_service.delete_person(session, person_id)
    except (
        people_service.PersonNotFoundError,
        people_service.PersonInUseError,
    ) as error:
        raise person_error(error) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)
