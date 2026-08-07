from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization import Organization


def list_organizations(session: Session) -> list[Organization]:
    statement = select(Organization).order_by(
        Organization.name.asc(),
        Organization.id.asc(),
    )
    return list(session.scalars(statement))


def get_organization(
    session: Session,
    organization_id: str,
) -> Organization | None:
    return session.get(Organization, organization_id)


def add_organization(
    session: Session,
    organization: Organization,
) -> Organization:
    session.add(organization)
    session.flush()
    return organization


def delete_organization(
    session: Session,
    organization: Organization,
) -> None:
    session.delete(organization)
