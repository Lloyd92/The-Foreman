from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.member import Member
from app.models.space import Space
from app.repositories import members as members_repository
from app.schemas.member import MemberCreate, MemberUpdate
from app.services import people as people_service


class MemberNotFoundError(LookupError):
    pass


class MemberAlreadyExistsError(ValueError):
    pass


def list_members(
    session: Session,
    active_space: Space,
) -> list[Member]:
    return members_repository.list_members(session, active_space.id)


def require_member(
    session: Session,
    active_space: Space,
    member_id: str,
) -> Member:
    member = members_repository.get_member(
        session,
        active_space.id,
        member_id,
    )

    if member is None:
        raise MemberNotFoundError(
            "The requested Member does not exist."
        )

    return member


def create_member(
    session: Session,
    active_space: Space,
    data: MemberCreate,
) -> Member:
    try:
        people_service.require_person(session, data.person_id)
        existing_member = members_repository.get_member_for_person(
            session,
            active_space.id,
            data.person_id,
        )

        if existing_member is not None:
            raise MemberAlreadyExistsError(
                "The Person is already a Member of the active Space."
            )

        member = Member(
            space_id=active_space.id,
            **data.model_dump(),
        )
        members_repository.add_member(session, member)
        session.commit()
        session.refresh(member)
    except IntegrityError as error:
        session.rollback()
        raise MemberAlreadyExistsError(
            "The Person is already a Member of the active Space."
        ) from error
    except Exception:
        session.rollback()
        raise

    return member


def update_member(
    session: Session,
    active_space: Space,
    member_id: str,
    data: MemberUpdate,
) -> Member:
    try:
        member = require_member(session, active_space, member_id)

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(member, field, value)

        session.commit()
        session.refresh(member)
    except Exception:
        session.rollback()
        raise

    return member


def delete_member(
    session: Session,
    active_space: Space,
    member_id: str,
) -> None:
    try:
        member = require_member(session, active_space, member_id)
        members_repository.delete_member(session, member)
        session.commit()
    except Exception:
        session.rollback()
        raise
