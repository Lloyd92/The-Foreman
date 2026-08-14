from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization_space_relationship import (
    OrganizationSpaceRelationship,
)


def list_organization_relationships(
    session: Session,
    space_id: str,
) -> list[OrganizationSpaceRelationship]:
    statement = (
        select(OrganizationSpaceRelationship)
        .where(OrganizationSpaceRelationship.space_id == space_id)
        .order_by(
            OrganizationSpaceRelationship.role.asc(),
            OrganizationSpaceRelationship.organization_id.asc(),
            OrganizationSpaceRelationship.id.asc(),
        )
    )
    return list(session.scalars(statement))


def get_organization_relationship(
    session: Session,
    space_id: str,
    relationship_id: str,
) -> OrganizationSpaceRelationship | None:
    statement = select(OrganizationSpaceRelationship).where(
        OrganizationSpaceRelationship.id == relationship_id,
        OrganizationSpaceRelationship.space_id == space_id,
    )
    return session.scalar(statement)


def get_organization_relationship_for_role(
    session: Session,
    space_id: str,
    organization_id: str,
    role: str,
) -> OrganizationSpaceRelationship | None:
    statement = select(OrganizationSpaceRelationship).where(
        OrganizationSpaceRelationship.space_id == space_id,
        OrganizationSpaceRelationship.organization_id == organization_id,
        OrganizationSpaceRelationship.role == role,
    )
    return session.scalar(statement)


def add_organization_relationship(
    session: Session,
    relationship: OrganizationSpaceRelationship,
) -> OrganizationSpaceRelationship:
    session.add(relationship)
    session.flush()
    return relationship


def delete_organization_relationship(
    session: Session,
    relationship: OrganizationSpaceRelationship,
) -> None:
    session.delete(relationship)



def organization_has_relationship(
    session: Session,
    space_id: str,
    organization_id: str,
) -> bool:
    statement = select(OrganizationSpaceRelationship.id).where(
        OrganizationSpaceRelationship.space_id == space_id,
        OrganizationSpaceRelationship.organization_id == organization_id,
    )
    return session.scalar(statement) is not None
