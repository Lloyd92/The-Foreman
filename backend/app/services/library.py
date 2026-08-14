from sqlalchemy.orm import Session

from app.models.library_record import LibraryRecord
from app.models.space import Space
from app.repositories import library as library_repository
from app.schemas.library import (
    LibraryRecordCreate,
    LibraryRecordRead,
    LibraryRecordUpdate,
)


class LibraryRecordNotFoundError(LookupError):
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
