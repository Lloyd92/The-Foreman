from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.space import Space
from app.models.work_calendar_relationship import WorkCalendarRelationship
from app.repositories import calendar as calendar_repository
from app.repositories import (
    work_calendar_relationships as relationship_repository,
)
from app.schemas.work_calendar_relationship import (
    WorkCalendarRelationshipCreate,
    WorkCalendarRelationshipRead,
    WorkCalendarRelationshipUpdate,
)
from app.services.projects import require_project
from app.services.tasks import require_task


class WorkCalendarRelationshipNotFoundError(LookupError):
    pass


class WorkCalendarRelationshipWorkNotFoundError(LookupError):
    pass


class WorkCalendarRelationshipCalendarNotFoundError(LookupError):
    pass


class WorkCalendarRelationshipAlreadyExistsError(ValueError):
    pass


def _require_work(
    session: Session,
    active_space: Space,
    *,
    work_type: str,
    work_id: str,
) -> None:
    try:
        if work_type == "task":
            require_task(session, active_space, work_id)
            return

        require_project(session, active_space, work_id)
    except LookupError as error:
        raise WorkCalendarRelationshipWorkNotFoundError(
            "The referenced Work record does not exist in the active Space."
        ) from error


def _calendar_exists(
    session: Session,
    active_space: Space,
    *,
    calendar_type: str,
    calendar_id: str,
) -> bool:
    if calendar_type == "entry":
        return (
            calendar_repository.get_entry(
                session,
                active_space.id,
                calendar_id,
            )
            is not None
        )

    return (
        calendar_repository.get_series(
            session,
            active_space.id,
            calendar_id,
        )
        is not None
    )


def serialize_relationship(
    session: Session,
    active_space: Space,
    value: WorkCalendarRelationship,
) -> WorkCalendarRelationshipRead:
    return WorkCalendarRelationshipRead(
        id=value.id,
        work_type=value.work_type,
        work_id=value.work_id,
        calendar_type=value.calendar_type,
        calendar_id=value.calendar_id,
        calendar_exists=_calendar_exists(
            session,
            active_space,
            calendar_type=value.calendar_type,
            calendar_id=value.calendar_id,
        ),
        note=value.note,
        created_at=value.created_at,
    )


def list_relationships(
    session: Session,
    active_space: Space,
) -> list[WorkCalendarRelationshipRead]:
    return [
        serialize_relationship(session, active_space, value)
        for value in relationship_repository.list_relationships(
            session,
            active_space.id,
        )
    ]


def require_relationship_model(
    session: Session,
    active_space: Space,
    relationship_id: str,
) -> WorkCalendarRelationship:
    value = relationship_repository.get_relationship(
        session,
        active_space.id,
        relationship_id,
    )

    if value is None:
        raise WorkCalendarRelationshipNotFoundError(
            "The requested Work Calendar relationship does not exist."
        )

    return value


def create_relationship(
    session: Session,
    active_space: Space,
    data: WorkCalendarRelationshipCreate,
) -> WorkCalendarRelationshipRead:
    _require_work(
        session,
        active_space,
        work_type=data.work_type,
        work_id=data.work_id,
    )

    if not _calendar_exists(
        session,
        active_space,
        calendar_type=data.calendar_type,
        calendar_id=data.calendar_id,
    ):
        raise WorkCalendarRelationshipCalendarNotFoundError(
            "The referenced Calendar record does not exist in the active Space."
        )

    value = WorkCalendarRelationship(
        space_id=active_space.id,
        **data.model_dump(),
    )

    try:
        relationship_repository.add_relationship(session, value)
        session.commit()
        session.refresh(value)
    except IntegrityError as error:
        session.rollback()
        raise WorkCalendarRelationshipAlreadyExistsError(
            "That Work Calendar relationship already exists."
        ) from error

    return serialize_relationship(session, active_space, value)


def update_relationship(
    session: Session,
    active_space: Space,
    relationship_id: str,
    data: WorkCalendarRelationshipUpdate,
) -> WorkCalendarRelationshipRead:
    value = require_relationship_model(
        session,
        active_space,
        relationship_id,
    )

    value.note = data.note
    session.commit()
    session.refresh(value)

    return serialize_relationship(session, active_space, value)


def delete_relationship(
    session: Session,
    active_space: Space,
    relationship_id: str,
) -> None:
    value = require_relationship_model(
        session,
        active_space,
        relationship_id,
    )

    relationship_repository.delete_relationship(session, value)
    session.commit()
