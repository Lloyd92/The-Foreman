from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.space_context import ActiveSpaceDependency
from app.schemas.calendar import (
    CalendarEntryCreate,
    CalendarEntryRead,
    CalendarEntryUpdate,
    CalendarSettingsRead,
    CalendarSettingsUpdate,
)
from app.services import calendar as calendar_service
from app.services.members import MemberNotFoundError


router = APIRouter(prefix="/api/calendar", tags=["calendar"])
SessionDependency = Annotated[Session, Depends(get_session)]


def calendar_error(error: Exception) -> HTTPException:
    if isinstance(error, calendar_service.CalendarSettingsNotFoundError):
        code = "CALENDAR_SETTINGS_NOT_FOUND"
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(error, calendar_service.CalendarEntryNotFoundError):
        code = "CALENDAR_ENTRY_NOT_FOUND"
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(error, MemberNotFoundError):
        code = "MEMBER_NOT_FOUND"
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(error, calendar_service.InvalidCalendarTimezoneError):
        code = "INVALID_CALENDAR_TIMEZONE"
        status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    elif isinstance(error, calendar_service.InvalidCalendarEntryError):
        code = "INVALID_CALENDAR_ENTRY"
        status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    else:
        raise TypeError("Unsupported Calendar service error.")

    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": str(error)},
    )


@router.get("/settings", response_model=CalendarSettingsRead)
def get_settings(
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> CalendarSettingsRead:
    try:
        return calendar_service.get_settings(session, active_space)
    except calendar_service.CalendarSettingsNotFoundError as error:
        raise calendar_error(error) from error


@router.put("/settings", response_model=CalendarSettingsRead)
def update_settings(
    data: CalendarSettingsUpdate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> CalendarSettingsRead:
    try:
        return calendar_service.update_settings(session, active_space, data)
    except calendar_service.InvalidCalendarTimezoneError as error:
        raise calendar_error(error) from error


@router.get("/entries", response_model=list[CalendarEntryRead])
def list_entries(
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> list[CalendarEntryRead]:
    return calendar_service.list_entries(session, active_space)


@router.post(
    "/entries",
    response_model=CalendarEntryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_entry(
    data: CalendarEntryCreate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> CalendarEntryRead:
    try:
        return calendar_service.create_entry(session, active_space, data)
    except (
        calendar_service.CalendarSettingsNotFoundError,
        calendar_service.InvalidCalendarEntryError,
        MemberNotFoundError,
    ) as error:
        raise calendar_error(error) from error


@router.get("/entries/{entry_id}", response_model=CalendarEntryRead)
def read_entry(
    entry_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> CalendarEntryRead:
    try:
        return calendar_service.serialize_entry(
            calendar_service.require_entry_model(
                session, active_space, entry_id
            )
        )
    except calendar_service.CalendarEntryNotFoundError as error:
        raise calendar_error(error) from error


@router.patch("/entries/{entry_id}", response_model=CalendarEntryRead)
def update_entry(
    entry_id: str,
    data: CalendarEntryUpdate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> CalendarEntryRead:
    try:
        return calendar_service.update_entry(
            session, active_space, entry_id, data
        )
    except (
        calendar_service.CalendarEntryNotFoundError,
        calendar_service.CalendarSettingsNotFoundError,
        calendar_service.InvalidCalendarEntryError,
        MemberNotFoundError,
    ) as error:
        raise calendar_error(error) from error


@router.delete(
    "/entries/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_entry(
    entry_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> Response:
    try:
        calendar_service.delete_entry(session, active_space, entry_id)
    except calendar_service.CalendarEntryNotFoundError as error:
        raise calendar_error(error) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/series", response_model=list[calendar_service.CalendarSeriesRead])
def list_series(
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
):
    return calendar_service.list_series(session, active_space)


@router.post(
    "/series",
    response_model=calendar_service.CalendarSeriesRead,
    status_code=status.HTTP_201_CREATED,
)
def create_series(
    data: calendar_service.CalendarSeriesCreate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
):
    try:
        return calendar_service.create_series(session, active_space, data)
    except (
        calendar_service.CalendarSettingsNotFoundError,
        calendar_service.InvalidCalendarEntryError,
        MemberNotFoundError,
    ) as error:
        raise calendar_error(error) from error


@router.get(
    "/series/{series_id}",
    response_model=calendar_service.CalendarSeriesRead,
)
def read_series(
    series_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
):
    try:
        return calendar_service.serialize_series(
            calendar_service.require_series_model(
                session, active_space, series_id
            )
        )
    except calendar_service.CalendarSeriesNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "CALENDAR_SERIES_NOT_FOUND",
                "message": str(error),
            },
        ) from error


@router.delete(
    "/series/{series_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_series(
    series_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> Response:
    try:
        calendar_service.delete_series(
            session, active_space, series_id
        )
    except calendar_service.CalendarSeriesNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "CALENDAR_SERIES_NOT_FOUND",
                "message": str(error),
            },
        ) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/series/{series_id}/exclusions",
    response_model=calendar_service.CalendarSeriesExclusionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_exclusion(
    series_id: str,
    data: calendar_service.CalendarSeriesExclusionCreate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
):
    try:
        return calendar_service.create_exclusion(
            session,
            active_space,
            series_id,
            data,
        )
    except calendar_service.CalendarSeriesNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "CALENDAR_SERIES_NOT_FOUND",
                "message": str(error),
            },
        ) from error


@router.delete(
    "/series/{series_id}/exclusions/{excluded_date}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_exclusion(
    series_id: str,
    excluded_date: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> Response:
    from datetime import date

    try:
        parsed = date.fromisoformat(excluded_date)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_CALENDAR_DATE",
                "message": "Exclusion date is invalid.",
            },
        ) from error

    try:
        calendar_service.delete_exclusion(
            session,
            active_space,
            series_id,
            parsed,
        )
    except calendar_service.CalendarSeriesNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "CALENDAR_SERIES_NOT_FOUND",
                "message": str(error),
            },
        ) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch(
    "/series/{series_id}",
    response_model=calendar_service.CalendarSeriesRead,
)
def update_series(
    series_id: str,
    data: calendar_service.CalendarSeriesUpdate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
):
    try:
        return calendar_service.update_series(
            session, active_space, series_id, data
        )
    except (
        calendar_service.CalendarSeriesNotFoundError,
        calendar_service.InvalidCalendarEntryError,
        MemberNotFoundError,
    ) as error:
        if isinstance(error, calendar_service.CalendarSeriesNotFoundError):
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "CALENDAR_SERIES_NOT_FOUND",
                    "message": str(error),
                },
            ) from error
        raise calendar_error(error) from error


@router.get(
    "/occurrences",
    response_model=list[calendar_service.CalendarOccurrenceRead],
)
def list_occurrences(
    start_date: str,
    end_date: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
):
    from datetime import date

    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_CALENDAR_DATE",
                "message": "Occurrence range dates are invalid.",
            },
        ) from error

    try:
        return calendar_service.list_occurrences(
            session,
            active_space,
            start,
            end,
        )
    except (
        calendar_service.CalendarSettingsNotFoundError,
        calendar_service.InvalidCalendarEntryError,
    ) as error:
        raise calendar_error(error) from error
