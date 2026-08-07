from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
)
from app.services import organizations as organizations_service


router = APIRouter(
    prefix="/api/organizations",
    tags=["organizations"],
)
SessionDependency = Annotated[Session, Depends(get_session)]


def organization_error(error: Exception) -> HTTPException:
    if isinstance(
        error,
        organizations_service.OrganizationNotFoundError,
    ):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ORGANIZATION_NOT_FOUND",
                "message": str(error),
            },
        )

    if isinstance(error, organizations_service.OrganizationInUseError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "ORGANIZATION_IN_USE",
                "message": str(error),
            },
        )

    raise TypeError("Unsupported Organization service error.")


@router.get("", response_model=list[OrganizationRead])
def list_organizations(
    session: SessionDependency,
) -> list[OrganizationRead]:
    return organizations_service.list_organizations(session)


@router.post(
    "",
    response_model=OrganizationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_organization(
    data: OrganizationCreate,
    session: SessionDependency,
) -> OrganizationRead:
    return organizations_service.create_organization(session, data)


@router.get("/{organization_id}", response_model=OrganizationRead)
def read_organization(
    organization_id: str,
    session: SessionDependency,
) -> OrganizationRead:
    try:
        return organizations_service.require_organization(
            session,
            organization_id,
        )
    except organizations_service.OrganizationNotFoundError as error:
        raise organization_error(error) from error


@router.patch("/{organization_id}", response_model=OrganizationRead)
def update_organization(
    organization_id: str,
    data: OrganizationUpdate,
    session: SessionDependency,
) -> OrganizationRead:
    try:
        return organizations_service.update_organization(
            session,
            organization_id,
            data,
        )
    except organizations_service.OrganizationNotFoundError as error:
        raise organization_error(error) from error


@router.delete(
    "/{organization_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_organization(
    organization_id: str,
    session: SessionDependency,
) -> Response:
    try:
        organizations_service.delete_organization(
            session,
            organization_id,
        )
    except (
        organizations_service.OrganizationNotFoundError,
        organizations_service.OrganizationInUseError,
    ) as error:
        raise organization_error(error) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)
