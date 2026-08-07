from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.person import Person


def list_people(session: Session) -> list[Person]:
    statement = select(Person).order_by(
        Person.display_name.asc(),
        Person.id.asc(),
    )
    return list(session.scalars(statement))


def get_person(
    session: Session,
    person_id: str,
) -> Person | None:
    return session.get(Person, person_id)


def add_person(
    session: Session,
    person: Person,
) -> Person:
    session.add(person)
    session.flush()
    return person


def delete_person(
    session: Session,
    person: Person,
) -> None:
    session.delete(person)
