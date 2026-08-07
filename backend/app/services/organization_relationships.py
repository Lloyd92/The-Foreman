from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.organization_space_relationship import (
    OrganizationSpaceRelationship,
)
from app.models.space import Space
from app.repositories import (
    organization_relationships as relationships_repository,
)
from app.schemas.organization import (
    OrganizationSpaceRelationshipCreate,
    OrganizationSpaceRelationshipUpdate,
)
from app.services import organizations as organizations_service


class OrganizationRelationshipNotFoundError(LookupError):
    pass


class OrganizationRelationshipAlreadyExistsError(ValueError):
    pass


def list_organization_relationships(
    session: Session,
    active_space: Space,
) -> list[OrganizationSpaceRelationship]:
    return relationships_repository.list_organization_relationships(
        session,
        active_space.id,
    )


def require_organization_relationship(
    session: Session,
    active_space: Space,
    relationship_id: str,
) -> OrganizationSpaceRelationship:
    relationship = (
        relationships_repository.get_organization_relationship(
            session,
            active_space.id,
            relationship_id,
        )
    )

    if relationship is None:
        raise OrganizationRelationshipNotFoundError(
            "The requested Organization relationship does not exist."
        )

    return relationship


def create_organization_relationship(
    session: Session,
    active_space: Space,
    data: OrganizationSpaceRelationshipCreate,
) -> OrganizationSpaceRelationship:
    try:
        organizations_service.require_organization(
            session,
            data.organization_id,
        )
        existing_relationship = (
            relationships_repository.get_organization_relationship_for_role(
                session,
                active_space.id,
                data.organization_id,
                data.role,
            )
        )

        if existing_relationship is not None:
            raise OrganizationRelationshipAlreadyExistsError(
                "The Organization already has that role in the active Space."
            )

        relationship = OrganizationSpaceRelationship(
            space_id=active_space.id,
            **data.model_dump(),
        )
        relationships_repository.add_organization_relationship(
            session,
            relationship,
        )
        session.commit()
        session.refresh(relationship)
    except IntegrityError as error:
        session.rollback()
        raise OrganizationRelationshipAlreadyExistsError(
            "The Organization already has that role in the active Space."
        ) from error
    except Exception:
        session.rollback()
        raise

    return relationship


def update_organization_relationship(
    session: Session,
    active_space: Space,
    relationship_id: str,
    data: OrganizationSpaceRelationshipUpdate,
) -> OrganizationSpaceRelationship:
    try:
        relationship = require_organization_relationship(
            session,
            active_space,
            relationship_id,
        )
        changes = data.model_dump(exclude_unset=True)
        new_role = changes.get("role", relationship.role)
        existing_relationship = (
            relationships_repository.get_organization_relationship_for_role(
                session,
                active_space.id,
                relationship.organization_id,
                new_role,
            )
        )

        if (
            existing_relationship is not None
            and existing_relationship.id != relationship.id
        ):
            raise OrganizationRelationshipAlreadyExistsError(
                "The Organization already has that role in the active Space."
            )

        for field, value in changes.items():
            setattr(relationship, field, value)

        session.commit()
        session.refresh(relationship)
    except IntegrityError as error:
        session.rollback()
        raise OrganizationRelationshipAlreadyExistsError(
            "The Organization already has that role in the active Space."
        ) from error
    except Exception:
        session.rollback()
        raise

    return relationship


def delete_organization_relationship(
    session: Session,
    active_space: Space,
    relationship_id: str,
) -> None:
    try:
        relationship = require_organization_relationship(
            session,
            active_space,
            relationship_id,
        )
        relationships_repository.delete_organization_relationship(
            session,
            relationship,
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
