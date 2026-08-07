from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.member import Member


def list_members(
    session: Session,
    space_id: str,
) -> list[Member]:
    statement = (
        select(Member)
        .where(Member.space_id == space_id)
        .order_by(
            Member.role.asc(),
            Member.person_id.asc(),
            Member.id.asc(),
        )
    )
    return list(session.scalars(statement))


def get_member(
    session: Session,
    space_id: str,
    member_id: str,
) -> Member | None:
    statement = select(Member).where(
        Member.id == member_id,
        Member.space_id == space_id,
    )
    return session.scalar(statement)


def get_member_for_person(
    session: Session,
    space_id: str,
    person_id: str,
) -> Member | None:
    statement = select(Member).where(
        Member.space_id == space_id,
        Member.person_id == person_id,
    )
    return session.scalar(statement)


def add_member(
    session: Session,
    member: Member,
) -> Member:
    session.add(member)
    session.flush()
    return member


def delete_member(
    session: Session,
    member: Member,
) -> None:
    session.delete(member)
