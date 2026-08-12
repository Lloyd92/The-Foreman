from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.models.calendar_entry import CalendarEntry
from app.models.calendar_setting import CalendarSetting
from app.models.space import Space
from app.repositories import calendar as calendar_repository
from app.schemas.calendar import (
    CalendarEntryCreate,
    CalendarEntryRead,
    CalendarEntryUpdate,
    CalendarSettingsRead,
    CalendarSettingsUpdate,
)
from app.services import members as member_service


class CalendarSettingsNotFoundError(LookupError):
    pass


class CalendarEntryNotFoundError(LookupError):
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
