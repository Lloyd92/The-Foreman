from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.space import Space


def list_spaces(session: Session) -> list[Space]:
    statement = select(Space).order_by(
        Space.name.asc(),
        Space.id.asc(),
    )
    return list(session.scalars(statement))


def get_space(
    session: Session,
    space_id: str,
) -> Space | None:
    return session.get(Space, space_id)


def add_space(
    session: Session,
    space: Space,
) -> Space:
    session.add(space)
    session.flush()
    return space


def delete_space(
    session: Session,
    space: Space,
) -> None:
    session.delete(space)
