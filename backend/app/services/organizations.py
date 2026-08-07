from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.repositories import organizations as organizations_repository
from app.schemas.organization import OrganizationCreate, OrganizationUpdate


class OrganizationNotFoundError(LookupError):
    pass


class OrganizationInUseError(ValueError):
    pass


def list_organizations(session: Session) -> list[Organization]:
    return organizations_repository.list_organizations(session)


def require_organization(
    session: Session,
    organization_id: str,
) -> Organization:
    organization = organizations_repository.get_organization(
        session,
        organization_id,
    )

    if organization is None:
        raise OrganizationNotFoundError(
            "The requested Organization does not exist."
        )

    return organization


def create_organization(
    session: Session,
    data: OrganizationCreate,
) -> Organization:
    organization = Organization(**data.model_dump())

    try:
        organizations_repository.add_organization(session, organization)
        session.commit()
        session.refresh(organization)
    except Exception:
        session.rollback()
        raise

    return organization


def update_organization(
    session: Session,
    organization_id: str,
    data: OrganizationUpdate,
) -> Organization:
    organization = require_organization(session, organization_id)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(organization, field, value)

    try:
        session.commit()
        session.refresh(organization)
    except Exception:
        session.rollback()
        raise

    return organization


def delete_organization(
    session: Session,
    organization_id: str,
) -> None:
    organization = require_organization(session, organization_id)

    try:
        organizations_repository.delete_organization(
            session,
            organization,
        )
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise OrganizationInUseError(
            "The Organization cannot be deleted while records reference it."
        ) from error
    except Exception:
        session.rollback()
        raise
