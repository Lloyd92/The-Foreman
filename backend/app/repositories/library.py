from sqlalchemy import asc, desc, or_, select
from sqlalchemy.orm import Session

from app.models.library_record import LibraryRecord


SORT_FIELDS = {
    "title": LibraryRecord.title,
    "kind": LibraryRecord.kind,
    "created_at": LibraryRecord.created_at,
    "updated_at": LibraryRecord.updated_at,
}


def list_records(
    session: Session,
    space_id: str,
    *,
    search: str | None = None,
    kind: str | None = None,
    sort_by: str = "title",
    sort_direction: str = "asc",
) -> list[LibraryRecord]:
    statement = select(LibraryRecord).where(
        LibraryRecord.space_id == space_id
    )

    if search:
        pattern = f"%{search}%"
        statement = statement.where(
            or_(
                LibraryRecord.title.ilike(pattern),
                LibraryRecord.content.ilike(pattern),
                LibraryRecord.reference_location.ilike(pattern),
            )
        )

    if kind:
        statement = statement.where(
            LibraryRecord.kind == kind
        )

    sort_column = SORT_FIELDS[sort_by]
    order = (
        desc(sort_column)
        if sort_direction == "desc"
        else asc(sort_column)
    )

    statement = statement.order_by(
        order,
        asc(LibraryRecord.title),
        asc(LibraryRecord.id),
    )
    return list(session.scalars(statement))


def get_record(
    session: Session,
    space_id: str,
    record_id: str,
) -> LibraryRecord | None:
    statement = select(LibraryRecord).where(
        LibraryRecord.id == record_id,
        LibraryRecord.space_id == space_id,
    )
    return session.scalar(statement)


def add_record(
    session: Session,
    record: LibraryRecord,
) -> LibraryRecord:
    session.add(record)
    session.flush()
    session.refresh(record)
    return record


def delete_record(
    session: Session,
    record: LibraryRecord,
) -> None:
    session.delete(record)
