from sqlalchemy import asc, select
from sqlalchemy.orm import Session

from app.models.calendar_entry import CalendarEntry
from app.models.calendar_setting import CalendarSetting


def get_settings(
    session: Session,
    space_id: str,
) -> CalendarSetting | None:
    return session.scalar(
        select(CalendarSetting).where(
            CalendarSetting.space_id == space_id
        )
    )


def list_entries(
    session: Session,
    space_id: str,
) -> list[CalendarEntry]:
    statement = (
        select(CalendarEntry)
        .where(CalendarEntry.space_id == space_id)
        .order_by(
            asc(CalendarEntry.start_date),
            asc(CalendarEntry.start_at),
            asc(CalendarEntry.id),
        )
    )
    return list(session.scalars(statement))


def get_entry(
    session: Session,
    space_id: str,
    entry_id: str,
) -> CalendarEntry | None:
    return session.scalar(
        select(CalendarEntry).where(
            CalendarEntry.id == entry_id,
            CalendarEntry.space_id == space_id,
        )
    )


def add_entry(
    session: Session,
    entry: CalendarEntry,
) -> CalendarEntry:
    session.add(entry)
    session.flush()
    session.refresh(entry)
    return entry


def delete_entry(
    session: Session,
    entry: CalendarEntry,
) -> None:
    session.delete(entry)


def add_settings(
    session: Session,
    settings: CalendarSetting,
) -> CalendarSetting:
    session.add(settings)
    session.flush()
    session.refresh(settings)
    return settings
