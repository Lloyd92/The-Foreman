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


from app.models.calendar_series import CalendarSeries
from app.models.calendar_series_exclusion import CalendarSeriesExclusion


def list_series(
    session: Session,
    space_id: str,
) -> list[CalendarSeries]:
    return list(
        session.scalars(
            select(CalendarSeries)
            .where(CalendarSeries.space_id == space_id)
            .order_by(
                asc(CalendarSeries.anchor_date),
                asc(CalendarSeries.local_start_time),
                asc(CalendarSeries.id),
            )
        )
    )


def get_series(
    session: Session,
    space_id: str,
    series_id: str,
) -> CalendarSeries | None:
    return session.scalar(
        select(CalendarSeries).where(
            CalendarSeries.id == series_id,
            CalendarSeries.space_id == space_id,
        )
    )


def add_series(
    session: Session,
    series: CalendarSeries,
) -> CalendarSeries:
    session.add(series)
    session.flush()
    session.refresh(series)
    return series


def delete_series(
    session: Session,
    series: CalendarSeries,
) -> None:
    session.delete(series)


def list_exclusions(
    session: Session,
    space_id: str,
    series_id: str,
) -> list[CalendarSeriesExclusion]:
    return list(
        session.scalars(
            select(CalendarSeriesExclusion).where(
                CalendarSeriesExclusion.space_id == space_id,
                CalendarSeriesExclusion.series_id == series_id,
            )
        )
    )


def add_exclusion(
    session: Session,
    exclusion: CalendarSeriesExclusion,
) -> CalendarSeriesExclusion:
    session.add(exclusion)
    session.flush()
    session.refresh(exclusion)
    return exclusion


def get_exclusion_by_date(
    session: Session,
    space_id: str,
    series_id: str,
    excluded_date,
) -> CalendarSeriesExclusion | None:
    return session.scalar(
        select(CalendarSeriesExclusion).where(
            CalendarSeriesExclusion.space_id == space_id,
            CalendarSeriesExclusion.series_id == series_id,
            CalendarSeriesExclusion.excluded_date == excluded_date,
        )
    )


def delete_exclusion(
    session: Session,
    exclusion: CalendarSeriesExclusion,
) -> None:
    session.delete(exclusion)
