from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.space_context import ActiveSpaceDependency
from app.schemas.organization import (
    OrganizationSpaceRelationshipCreate,
    OrganizationSpaceRelationshipRead,
    OrganizationSpaceRelationshipUpdate,
)
from app.services import (
    organization_relationships as organization_relationships_service,
)
from app.services import organizations as organizations_service


router = APIRouter(
    prefix="/api/organization-relationships",
    tags=["organization-relationships"],
)
SessionDependency = Annotated[Session, Depends(get_session)]


def organization_relationship_error(error: Exception) -> HTTPException:
    if isinstance(
        error,
        organization_relationships_service.OrganizationRelationshipNotFoundError,
    ):
        code = "ORGANIZATION_RELATIONSHIP_NOT_FOUND"
        response_status = status.HTTP_404_NOT_FOUND
    elif isinstance(
        error,
        organization_relationships_service.OrganizationRelationshipAlreadyExistsError,
    ):
        code = "ORGANIZATION_RELATIONSHIP_ALREADY_EXISTS"
        response_status = status.HTTP_409_CONFLICT
    elif isinstance(
        error,
        organizations_service.OrganizationNotFoundError,
    ):
        code = "ORGANIZATION_NOT_FOUND"
        response_status = status.HTTP_404_NOT_FOUND
    else:
        raise TypeError("Unsupported Organization relationship service error.")

    return HTTPException(
        status_code=response_status,
        detail={
            "code": code,
            "message": str(error),
        },
    )


@router.get(
    "",
    response_model=list[OrganizationSpaceRelationshipRead],
)
def list_organization_relationships(
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> list[OrganizationSpaceRelationshipRead]:
    return organization_relationships_service.list_organization_relationships(
        session,
        active_space,
    )


@router.post(
    "",
    response_model=OrganizationSpaceRelationshipRead,
    status_code=status.HTTP_201_CREATED,
)
def create_organization_relationship(
    data: OrganizationSpaceRelationshipCreate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> OrganizationSpaceRelationshipRead:
    try:
        return organization_relationships_service.create_organization_relationship(
            session,
            active_space,
            data,
        )
    except (
        organization_relationships_service.OrganizationRelationshipAlreadyExistsError,
        organizations_service.OrganizationNotFoundError,
    ) as error:
        raise organization_relationship_error(error) from error


@router.get(
    "/{relationship_id}",
    response_model=OrganizationSpaceRelationshipRead,
)
def read_organization_relationship(
    relationship_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> OrganizationSpaceRelationshipRead:
    try:
        return organization_relationships_service.require_organization_relationship(
            session,
            active_space,
            relationship_id,
        )
    except (
        organization_relationships_service.OrganizationRelationshipNotFoundError
    ) as error:
        raise organization_relationship_error(error) from error


@router.patch(
    "/{relationship_id}",
    response_model=OrganizationSpaceRelationshipRead,
)
def update_organization_relationship(
    relationship_id: str,
    data: OrganizationSpaceRelationshipUpdate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> OrganizationSpaceRelationshipRead:
    try:
        return organization_relationships_service.update_organization_relationship(
            session,
            active_space,
            relationship_id,
            data,
        )
    except (
        organization_relationships_service.OrganizationRelationshipNotFoundError,
        organization_relationships_service.OrganizationRelationshipAlreadyExistsError,
    ) as error:
        raise organization_relationship_error(error) from error


@router.delete(
    "/{relationship_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_organization_relationship(
    relationship_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> Response:
    try:
        organization_relationships_service.delete_organization_relationship(
            session,
            active_space,
            relationship_id,
        )
    except (
        organization_relationships_service.OrganizationRelationshipNotFoundError
    ) as error:
        raise organization_relationship_error(error) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)
