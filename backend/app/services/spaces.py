from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.default_space import DEFAULT_SPACE_ID
from app.models.space import Space
from app.repositories import spaces as space_repository
from app.schemas.space import SpaceCreate, SpaceUpdate


class SpaceNotFoundError(LookupError):
    pass


class SpaceNameConflictError(ValueError):
    pass


class DefaultSpaceProtectedError(ValueError):
    pass


class SpaceInUseError(ValueError):
    pass


def list_spaces(session: Session) -> list[Space]:
    return space_repository.list_spaces(session)


def require_space(
    session: Session,
    space_id: str,
) -> Space:
    space = space_repository.get_space(session, space_id)

    if space is None:
        raise SpaceNotFoundError(
            "The requested Space does not exist."
        )

    return space


def create_space(
    session: Session,
    data: SpaceCreate,
) -> Space:
    space = Space(**data.model_dump())

    try:
        space_repository.add_space(session, space)
        session.commit()
        session.refresh(space)
    except IntegrityError as error:
        session.rollback()
        raise SpaceNameConflictError(
            "A Space with that name already exists."
        ) from error
    except Exception:
        session.rollback()
        raise

    return space


def update_space(
    session: Session,
    space_id: str,
    data: SpaceUpdate,
) -> Space:
    space = require_space(session, space_id)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(space, field, value)

    try:
        session.commit()
        session.refresh(space)
    except IntegrityError as error:
        session.rollback()
        raise SpaceNameConflictError(
            "A Space with that name already exists."
        ) from error
    except Exception:
        session.rollback()
        raise

    return space


def delete_space(
    session: Session,
    space_id: str,
) -> None:
    if space_id == DEFAULT_SPACE_ID:
        raise DefaultSpaceProtectedError(
            "The deterministic default Space cannot be deleted."
        )

    space = require_space(session, space_id)

    try:
        space_repository.delete_space(session, space)
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise SpaceInUseError(
            "The Space cannot be deleted while records reference it."
        ) from error
    except Exception:
        session.rollback()
        raise
