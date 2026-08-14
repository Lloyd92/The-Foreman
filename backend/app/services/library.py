from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.library_record import LibraryRecord
from app.models.library_relationship import LibraryRelationship
from app.models.space import Space
from app.repositories import calendar as calendar_repository
from app.repositories import care_plans as care_plans_repository
from app.repositories import inventory as inventory_repository
from app.repositories import library as library_repository
from app.repositories import members as members_repository
from app.repositories import money as money_repository
from app.repositories import tools as tools_repository
from app.repositories import (
    organization_relationships as organization_relationships_repository,
)
from app.schemas.library import (
    LibraryRecordCreate,
    LibraryRecordRead,
    LibraryRecordUpdate,
    LibraryRelationshipCreate,
    LibraryRelationshipRead,
    LibraryRelationshipUpdate,
)
from app.services.projects import require_project
from app.services.tasks import require_task
from app.services.tools import require_tool


class LibraryRecordNotFoundError(LookupError):
    pass


class LibraryRelationshipNotFoundError(LookupError):
    pass


class LibraryRelationshipConflictError(ValueError):
    pass


class LibraryRelationshipTargetNotFoundError(LookupError):
    pass


def serialize_record(
    record: LibraryRecord,
) -> LibraryRecordRead:
    return LibraryRecordRead(
        id=record.id,
        kind=record.kind,
        title=record.title,
        content=record.content,
        reference_location=record.reference_location,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def list_records(
    session: Session,
    active_space: Space,
    *,
    search: str | None = None,
    kind: str | None = None,
    sort_by: str = "title",
    sort_direction: str = "asc",
) -> list[LibraryRecordRead]:
    return [
        serialize_record(record)
        for record in library_repository.list_records(
            session,
            active_space.id,
            search=search,
            kind=kind,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )
    ]


def require_record_model(
    session: Session,
    active_space: Space,
    record_id: str,
) -> LibraryRecord:
    record = library_repository.get_record(
        session,
        active_space.id,
        record_id,
    )

    if record is None:
        raise LibraryRecordNotFoundError(
            "The requested Library record does not exist."
        )

    return record


def require_record(
    session: Session,
    active_space: Space,
    record_id: str,
) -> LibraryRecordRead:
    return serialize_record(
        require_record_model(
            session,
            active_space,
            record_id,
        )
    )


def create_record(
    session: Session,
    active_space: Space,
    data: LibraryRecordCreate,
) -> LibraryRecordRead:
    record = LibraryRecord(
        space_id=active_space.id,
        **data.model_dump(),
    )

    try:
        library_repository.add_record(session, record)
        session.commit()
        session.refresh(record)
    except Exception:
        session.rollback()
        raise

    return serialize_record(record)


def update_record(
    session: Session,
    active_space: Space,
    record_id: str,
    data: LibraryRecordUpdate,
) -> LibraryRecordRead:
    record = require_record_model(
        session,
        active_space,
        record_id,
    )

    for field, value in data.model_dump(
        exclude_unset=True
    ).items():
        setattr(record, field, value)

    try:
        session.commit()
        session.refresh(record)
    except Exception:
        session.rollback()
        raise

    return serialize_record(record)


def delete_record(
    session: Session,
    active_space: Space,
    record_id: str,
) -> None:
    record = require_record_model(
        session,
        active_space,
        record_id,
    )

    try:
        library_repository.delete_record(session, record)
        session.commit()
    except Exception:
        session.rollback()
        raise



def _target_exists(
    session: Session,
    active_space: Space,
    *,
    target_type: str,
    target_id: str,
) -> bool:
    if target_type == "task":
        try:
            require_task(session, active_space, target_id)
            return True
        except LookupError:
            return False

    if target_type == "project":
        try:
            require_project(session, active_space, target_id)
            return True
        except LookupError:
            return False

    if target_type == "tool":
        try:
            require_tool(session, active_space, target_id)
            return True
        except LookupError:
            return False

    if target_type == "inventory":
        return (
            inventory_repository.get_inventory_item(
                session,
                active_space.id,
                target_id,
            )
            is not None
        )

    if target_type == "care_plan":
        return (
            care_plans_repository.get_care_plan(
                session,
                active_space.id,
                target_id,
            )
            is not None
        )

    if target_type == "tool_maintenance_record":
        return (
            tools_repository.get_maintenance_record_by_id(
                session,
                active_space.id,
                target_id,
            )
            is not None
        )

    if target_type == "calendar_entry":
        return (
            calendar_repository.get_entry(
                session,
                active_space.id,
                target_id,
            )
            is not None
        )

    if target_type == "calendar_series":
        return (
            calendar_repository.get_series(
                session,
                active_space.id,
                target_id,
            )
            is not None
        )

    money_lookup = {
        "money_account": money_repository.get_account,
        "money_category": money_repository.get_category,
        "money_transaction": money_repository.get_transaction,
        "money_budget": money_repository.get_budget,
        "money_obligation": money_repository.get_obligation,
    }.get(target_type)

    if money_lookup is not None:
        return (
            money_lookup(
                session,
                active_space.id,
                target_id,
            )
            is not None
        )

    if target_type == "person":
        return (
            members_repository.get_member_for_person(
                session,
                active_space.id,
                target_id,
            )
            is not None
        )

    return (
        organization_relationships_repository
        .organization_has_relationship(
            session,
            active_space.id,
            target_id,
        )
    )


def serialize_relationship(
    session: Session,
    active_space: Space,
    value: LibraryRelationship,
) -> LibraryRelationshipRead:
    return LibraryRelationshipRead(
        id=value.id,
        library_record_id=value.library_record_id,
        target_type=value.target_type,
        target_id=value.target_id,
        target_exists=_target_exists(
            session,
            active_space,
            target_type=value.target_type,
            target_id=value.target_id,
        ),
        note=value.note,
        created_at=value.created_at,
    )


def list_relationships(
    session: Session,
    active_space: Space,
    record_id: str,
) -> list[LibraryRelationshipRead]:
    require_record_model(session, active_space, record_id)

    return [
        serialize_relationship(session, active_space, value)
        for value in library_repository.list_relationships(
            session,
            active_space.id,
            record_id,
        )
    ]


def require_relationship_model(
    session: Session,
    active_space: Space,
    record_id: str,
    relationship_id: str,
) -> LibraryRelationship:
    require_record_model(session, active_space, record_id)

    value = library_repository.get_relationship(
        session,
        active_space.id,
        record_id,
        relationship_id,
    )

    if value is None:
        raise LibraryRelationshipNotFoundError(
            "The requested Library relationship does not exist."
        )

    return value


def create_relationship(
    session: Session,
    active_space: Space,
    record_id: str,
    data: LibraryRelationshipCreate,
) -> LibraryRelationshipRead:
    require_record_model(session, active_space, record_id)

    if not _target_exists(
        session,
        active_space,
        target_type=data.target_type,
        target_id=data.target_id,
    ):
        raise LibraryRelationshipTargetNotFoundError(
            "Referenced target does not exist in the active Space."
        )

    value = LibraryRelationship(
        space_id=active_space.id,
        library_record_id=record_id,
        **data.model_dump(),
    )

    try:
        library_repository.add_relationship(session, value)
        session.commit()
        session.refresh(value)
    except IntegrityError as error:
        session.rollback()
        raise LibraryRelationshipConflictError(
            "That Library relationship already exists."
        ) from error

    return serialize_relationship(session, active_space, value)


def update_relationship(
    session: Session,
    active_space: Space,
    record_id: str,
    relationship_id: str,
    data: LibraryRelationshipUpdate,
) -> LibraryRelationshipRead:
    value = require_relationship_model(
        session,
        active_space,
        record_id,
        relationship_id,
    )
    value.note = data.note

    try:
        session.commit()
        session.refresh(value)
    except Exception:
        session.rollback()
        raise

    return serialize_relationship(session, active_space, value)


def delete_relationship(
    session: Session,
    active_space: Space,
    record_id: str,
    relationship_id: str,
) -> None:
    value = require_relationship_model(
        session,
        active_space,
        record_id,
        relationship_id,
    )

    try:
        library_repository.delete_relationship(session, value)
        session.commit()
    except Exception:
        session.rollback()
        raise
