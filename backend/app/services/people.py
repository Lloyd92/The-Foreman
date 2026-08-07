from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.person import Person
from app.repositories import people as people_repository
from app.schemas.person import PersonCreate, PersonUpdate


class PersonNotFoundError(LookupError):
    pass


class PersonInUseError(ValueError):
    pass


def list_people(session: Session) -> list[Person]:
    return people_repository.list_people(session)


def require_person(
    session: Session,
    person_id: str,
) -> Person:
    person = people_repository.get_person(session, person_id)

    if person is None:
        raise PersonNotFoundError(
            "The requested Person does not exist."
        )

    return person


def create_person(
    session: Session,
    data: PersonCreate,
) -> Person:
    person = Person(**data.model_dump())

    try:
        people_repository.add_person(session, person)
        session.commit()
        session.refresh(person)
    except Exception:
        session.rollback()
        raise

    return person


def update_person(
    session: Session,
    person_id: str,
    data: PersonUpdate,
) -> Person:
    person = require_person(session, person_id)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(person, field, value)

    try:
        session.commit()
        session.refresh(person)
    except Exception:
        session.rollback()
        raise

    return person


def delete_person(
    session: Session,
    person_id: str,
) -> None:
    person = require_person(session, person_id)

    try:
        people_repository.delete_person(session, person)
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise PersonInUseError(
            "The Person cannot be deleted while records reference it."
        ) from error
    except Exception:
        session.rollback()
        raise
