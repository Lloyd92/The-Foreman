from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.models.calendar_entry import CalendarEntry
from app.models.calendar_setting import CalendarSetting
from app.models.calendar_series import CalendarSeries
from app.models.space import Space
from app.repositories import calendar as calendar_repository
from app.schemas.calendar import (
    CalendarEntryCreate,
    CalendarEntryRead,
    CalendarEntryUpdate,
    CalendarSettingsRead,
    CalendarSettingsUpdate,
    CalendarSeriesCreate,
    CalendarSeriesRead,
    CalendarSeriesUpdate,
)
from app.services import members as member_service


class CalendarSettingsNotFoundError(LookupError):
    pass


class CalendarEntryNotFoundError(LookupError):
    pass


class CalendarSeriesNotFoundError(LookupError):
    pass


class InvalidCalendarTimezoneError(ValueError):
    pass


class InvalidCalendarEntryError(ValueError):
    pass


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as error:
        raise InvalidCalendarTimezoneError(
            "Timezone must be a valid IANA timezone."
        ) from error


def _to_utc(value: datetime, zone: ZoneInfo) -> datetime:
    if value.tzinfo is None:
        local = value.replace(tzinfo=zone)
        round_trip = (
            local.astimezone(timezone.utc)
            .astimezone(zone)
            .replace(tzinfo=None)
        )
        if round_trip != value:
            raise InvalidCalendarEntryError(
                "The requested local time does not exist."
            )
        value = local

    return value.astimezone(timezone.utc)


def serialize_settings(value: CalendarSetting) -> CalendarSettingsRead:
    return CalendarSettingsRead.model_validate(value)


def serialize_entry(value: CalendarEntry) -> CalendarEntryRead:
    result = CalendarEntryRead.model_validate(value)

    updates = {}

    if result.start_at is not None:
        updates["start_at"] = (
            result.start_at.replace(tzinfo=timezone.utc)
            if result.start_at.tzinfo is None
            else result.start_at.astimezone(timezone.utc)
        )

    if result.end_at is not None:
        updates["end_at"] = (
            result.end_at.replace(tzinfo=timezone.utc)
            if result.end_at.tzinfo is None
            else result.end_at.astimezone(timezone.utc)
        )

    return result.model_copy(update=updates)


def require_settings_model(
    session: Session,
    active_space: Space,
) -> CalendarSetting:
    value = calendar_repository.get_settings(
        session,
        active_space.id,
    )
    if value is None:
        raise CalendarSettingsNotFoundError(
            "Calendar timezone has not been configured."
        )
    return value


def get_settings(
    session: Session,
    active_space: Space,
) -> CalendarSettingsRead:
    return serialize_settings(
        require_settings_model(session, active_space)
    )


def update_settings(
    session: Session,
    active_space: Space,
    data: CalendarSettingsUpdate,
) -> CalendarSettingsRead:
    _zone(data.timezone_name)

    value = calendar_repository.get_settings(
        session,
        active_space.id,
    )

    if value is None:
        value = CalendarSetting(
            space_id=active_space.id,
            timezone_name=data.timezone_name,
        )
        calendar_repository.add_settings(session, value)
    else:
        value.timezone_name = data.timezone_name

    session.commit()
    session.refresh(value)
    return serialize_settings(value)


def list_entries(
    session: Session,
    active_space: Space,
) -> list[CalendarEntryRead]:
    return [
        serialize_entry(value)
        for value in calendar_repository.list_entries(
            session,
            active_space.id,
        )
    ]


def require_entry_model(
    session: Session,
    active_space: Space,
    entry_id: str,
) -> CalendarEntry:
    value = calendar_repository.get_entry(
        session,
        active_space.id,
        entry_id,
    )
    if value is None:
        raise CalendarEntryNotFoundError(
            "The requested Calendar entry does not exist."
        )
    return value


def create_entry(
    session: Session,
    active_space: Space,
    data: CalendarEntryCreate,
) -> CalendarEntryRead:
    settings = require_settings_model(session, active_space)
    zone = _zone(settings.timezone_name)

    if data.member_id is not None:
        member_service.require_member(
            session,
            active_space,
            data.member_id,
        )

    values = data.model_dump()

    if not data.all_day:
        values["start_at"] = _to_utc(data.start_at, zone)
        values["end_at"] = _to_utc(data.end_at, zone)

        if values["end_at"] <= values["start_at"]:
            raise InvalidCalendarEntryError(
                "Calendar end time must follow start time."
            )

    entry = CalendarEntry(
        space_id=active_space.id,
        timezone_name=settings.timezone_name,
        **values,
    )

    calendar_repository.add_entry(session, entry)
    session.commit()
    session.refresh(entry)
    return serialize_entry(entry)


def update_entry(
    session: Session,
    active_space: Space,
    entry_id: str,
    data: CalendarEntryUpdate,
) -> CalendarEntryRead:
    entry = require_entry_model(session, active_space, entry_id)
    changes = data.model_dump(exclude_unset=True)

    if "member_id" in changes and changes["member_id"] is not None:
        member_service.require_member(
            session,
            active_space,
            changes["member_id"],
        )

    for field in ("kind", "title", "all_day", "location", "notes"):
        if field in changes and changes[field] is None:
            raise InvalidCalendarEntryError(
                f"{field} cannot be null."
            )

    temporal = {
        "all_day",
        "start_at",
        "end_at",
        "start_date",
        "end_date",
    }

    if temporal.intersection(changes):
        settings = require_settings_model(session, active_space)
        zone = _zone(settings.timezone_name)

        if "start_at" in changes and changes["start_at"] is not None:
            changes["start_at"] = _to_utc(changes["start_at"], zone)

        if "end_at" in changes and changes["end_at"] is not None:
            changes["end_at"] = _to_utc(changes["end_at"], zone)

        entry.timezone_name = settings.timezone_name

    for field, value in changes.items():
        setattr(entry, field, value)

    session.flush()
    session.commit()
    session.refresh(entry)
    return serialize_entry(entry)


def delete_entry(
    session: Session,
    active_space: Space,
    entry_id: str,
) -> None:
    entry = require_entry_model(session, active_space, entry_id)
    calendar_repository.delete_entry(session, entry)
    session.commit()


WEEKDAY_BITS = {
    "monday": 1,
    "tuesday": 2,
    "wednesday": 4,
    "thursday": 8,
    "friday": 16,
    "saturday": 32,
    "sunday": 64,
}


def _weekday_mask(names: list[str]) -> int:
    return sum(WEEKDAY_BITS[name] for name in set(names))


def _weekday_names(mask: int) -> list[str]:
    return [
        name
        for name, bit in WEEKDAY_BITS.items()
        if mask & bit
    ]


def serialize_series(value: CalendarSeries) -> CalendarSeriesRead:
    return CalendarSeriesRead(
        id=value.id,
        member_id=value.member_id,
        kind=value.kind,
        title=value.title,
        frequency=value.frequency,
        interval_value=value.interval_value,
        weekdays=_weekday_names(value.weekday_mask),
        anchor_date=value.anchor_date,
        end_date=value.end_date,
        local_start_time=value.local_start_time.isoformat(),
        duration_minutes=value.duration_minutes,
        timezone_name=value.timezone_name,
        location=value.location,
        notes=value.notes,
        created_at=value.created_at,
        updated_at=value.updated_at,
    )


def list_series(
    session: Session,
    active_space: Space,
) -> list[CalendarSeriesRead]:
    return [
        serialize_series(value)
        for value in calendar_repository.list_series(
            session,
            active_space.id,
        )
    ]


def require_series_model(
    session: Session,
    active_space: Space,
    series_id: str,
) -> CalendarSeries:
    value = calendar_repository.get_series(
        session,
        active_space.id,
        series_id,
    )
    if value is None:
        raise CalendarSeriesNotFoundError(
            "The requested Calendar series does not exist."
        )
    return value


def create_series(
    session: Session,
    active_space: Space,
    data: CalendarSeriesCreate,
) -> CalendarSeriesRead:
    settings = require_settings_model(session, active_space)
    _zone(settings.timezone_name)

    if data.member_id is not None:
        member_service.require_member(
            session,
            active_space,
            data.member_id,
        )

    mask = _weekday_mask(data.weekdays)

    if data.frequency == "daily" and mask != 0:
        raise InvalidCalendarEntryError(
            "Daily series cannot specify weekdays."
        )

    if data.frequency == "weekly" and mask == 0:
        raise InvalidCalendarEntryError(
            "Weekly series requires at least one weekday."
        )

    if data.end_date is not None and data.end_date < data.anchor_date:
        raise InvalidCalendarEntryError(
            "Series end date cannot precede anchor date."
        )

    try:
        start_time = time.fromisoformat(data.local_start_time)
    except ValueError as error:
        raise InvalidCalendarEntryError(
            "Series start time is invalid."
        ) from error

    series = CalendarSeries(
        space_id=active_space.id,
        member_id=data.member_id,
        kind=data.kind,
        title=data.title,
        frequency=data.frequency,
        interval_value=data.interval_value,
        weekday_mask=mask,
        anchor_date=data.anchor_date,
        end_date=data.end_date,
        local_start_time=start_time,
        duration_minutes=data.duration_minutes,
        timezone_name=settings.timezone_name,
        location=data.location,
        notes=data.notes,
    )

    calendar_repository.add_series(session, series)
    session.commit()
    session.refresh(series)
    return serialize_series(series)


def delete_series(
    session: Session,
    active_space: Space,
    series_id: str,
) -> None:
    series = require_series_model(
        session,
        active_space,
        series_id,
    )
    calendar_repository.delete_series(session, series)
    session.commit()


from app.models.calendar_series_exclusion import CalendarSeriesExclusion
from app.schemas.calendar import (
    CalendarSeriesExclusionCreate,
    CalendarSeriesExclusionRead,
)


def serialize_exclusion(
    value: CalendarSeriesExclusion,
) -> CalendarSeriesExclusionRead:
    return CalendarSeriesExclusionRead.model_validate(value)


def create_exclusion(
    session: Session,
    active_space: Space,
    series_id: str,
    data: CalendarSeriesExclusionCreate,
) -> CalendarSeriesExclusionRead:
    require_series_model(session, active_space, series_id)

    existing = calendar_repository.get_exclusion_by_date(
        session,
        active_space.id,
        series_id,
        data.excluded_date,
    )

    if existing is not None:
        return serialize_exclusion(existing)

    exclusion = CalendarSeriesExclusion(
        space_id=active_space.id,
        series_id=series_id,
        excluded_date=data.excluded_date,
    )

    calendar_repository.add_exclusion(session, exclusion)
    session.commit()
    session.refresh(exclusion)
    return serialize_exclusion(exclusion)


def delete_exclusion(
    session: Session,
    active_space: Space,
    series_id: str,
    excluded_date,
) -> None:
    require_series_model(session, active_space, series_id)

    exclusion = calendar_repository.get_exclusion_by_date(
        session,
        active_space.id,
        series_id,
        excluded_date,
    )

    if exclusion is None:
        raise CalendarSeriesNotFoundError(
            "The requested Calendar exclusion does not exist."
        )

    calendar_repository.delete_exclusion(session, exclusion)
    session.commit()



def update_series(
    session: Session,
    active_space: Space,
    series_id: str,
    data: CalendarSeriesUpdate,
) -> CalendarSeriesRead:
    series = require_series_model(session, active_space, series_id)
    changes = data.model_dump(exclude_unset=True)

    if "member_id" in changes and changes["member_id"] is not None:
        member_service.require_member(
            session, active_space, changes["member_id"]
        )

    if "weekdays" in changes:
        changes["weekday_mask"] = _weekday_mask(
            changes.pop("weekdays") or []
        )

    if "local_start_time" in changes:
        try:
            changes["local_start_time"] = time.fromisoformat(
                changes["local_start_time"]
            )
        except ValueError as error:
            raise InvalidCalendarEntryError(
                "Series start time is invalid."
            ) from error

    values = {
        "frequency": changes.get("frequency", series.frequency),
        "weekday_mask": changes.get(
            "weekday_mask", series.weekday_mask
        ),
        "anchor_date": changes.get(
            "anchor_date", series.anchor_date
        ),
        "end_date": changes.get("end_date", series.end_date),
    }

    if values["frequency"] == "daily" and values["weekday_mask"] != 0:
        raise InvalidCalendarEntryError(
            "Daily series cannot specify weekdays."
        )

    if values["frequency"] == "weekly" and values["weekday_mask"] == 0:
        raise InvalidCalendarEntryError(
            "Weekly series requires at least one weekday."
        )

    if (
        values["end_date"] is not None
        and values["end_date"] < values["anchor_date"]
    ):
        raise InvalidCalendarEntryError(
            "Series end date cannot precede anchor date."
        )

    for field, value in changes.items():
        if field != "end_date" and value is None:
            raise InvalidCalendarEntryError(
                f"{field} cannot be null."
            )
        setattr(series, field, value)

    session.commit()
    session.refresh(series)
    return serialize_series(series)


from datetime import date, timedelta

from app.schemas.calendar import CalendarOccurrenceRead


def list_occurrences(
    session: Session,
    active_space: Space,
    start_date: date,
    end_date: date,
) -> list[CalendarOccurrenceRead]:
    if end_date <= start_date:
        raise InvalidCalendarEntryError(
            "Occurrence end date must follow start date."
        )

    if (end_date - start_date).days > 366:
        raise InvalidCalendarEntryError(
            "Occurrence range cannot exceed 366 days."
        )

    settings = require_settings_model(session, active_space)
    zone = _zone(settings.timezone_name)
    results: list[CalendarOccurrenceRead] = []

    for entry in calendar_repository.list_entries(
        session, active_space.id
    ):
        if entry.all_day:
            if entry.start_date < end_date and entry.end_date > start_date:
                results.append(
                    CalendarOccurrenceRead(
                        key=f"entry:{entry.id}",
                        source_type="entry",
                        source_id=entry.id,
                        member_id=entry.member_id,
                        kind=entry.kind,
                        title=entry.title,
                        start_date=entry.start_date,
                        end_date=entry.end_date,
                        timezone_name=entry.timezone_name,
                        location=entry.location,
                        notes=entry.notes,
                    )
                )
            continue

        start = (
            entry.start_at.replace(tzinfo=timezone.utc)
            if entry.start_at.tzinfo is None
            else entry.start_at.astimezone(timezone.utc)
        )
        end = (
            entry.end_at.replace(tzinfo=timezone.utc)
            if entry.end_at.tzinfo is None
            else entry.end_at.astimezone(timezone.utc)
        )

        range_start = datetime.combine(
            start_date, time.min, zone
        ).astimezone(timezone.utc)
        range_end = datetime.combine(
            end_date, time.min, zone
        ).astimezone(timezone.utc)

        if start < range_end and end > range_start:
            results.append(
                CalendarOccurrenceRead(
                    key=f"entry:{entry.id}",
                    source_type="entry",
                    source_id=entry.id,
                    member_id=entry.member_id,
                    kind=entry.kind,
                    title=entry.title,
                    start_at=start,
                    end_at=end,
                    timezone_name=entry.timezone_name,
                    location=entry.location,
                    notes=entry.notes,
                )
            )

    for series in calendar_repository.list_series(
        session, active_space.id
    ):
        series_zone = _zone(series.timezone_name)

        exclusions = {
            value.excluded_date
            for value in calendar_repository.list_exclusions(
                session,
                active_space.id,
                series.id,
            )
        }

        cursor = max(start_date, series.anchor_date)
        stop = min(
            end_date,
            (
                series.end_date + timedelta(days=1)
                if series.end_date is not None
                else end_date
            ),
        )

        while cursor < stop:
            delta_days = (cursor - series.anchor_date).days
            include = False

            if series.frequency == "daily":
                include = delta_days % series.interval_value == 0
            else:
                week_index = delta_days // 7
                weekday_bit = 1 << cursor.weekday()
                include = (
                    week_index % series.interval_value == 0
                    and bool(series.weekday_mask & weekday_bit)
                )

            if include and cursor not in exclusions:
                local_start = datetime.combine(
                    cursor,
                    series.local_start_time,
                    series_zone,
                )
                start = local_start.astimezone(timezone.utc)
                end = start + timedelta(
                    minutes=series.duration_minutes
                )

                results.append(
                    CalendarOccurrenceRead(
                        key=f"series:{series.id}:{cursor.isoformat()}",
                        source_type="series",
                        source_id=series.id,
                        member_id=series.member_id,
                        kind=series.kind,
                        title=series.title,
                        start_at=start,
                        end_at=end,
                        timezone_name=series.timezone_name,
                        location=series.location,
                        notes=series.notes,
                    )
                )

            cursor += timedelta(days=1)

    return sorted(
        results,
        key=lambda item: (
            item.start_date or date.max,
            item.start_at or datetime.max.replace(tzinfo=timezone.utc),
            item.key,
        ),
    )
