from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.space_context import ActiveSpaceDependency
from app.schemas.library import (
    LibraryRecordCreate,
    LibraryRecordListQuery,
    LibraryRecordRead,
    LibraryRecordUpdate,
)
from app.services import library as library_service


router = APIRouter(prefix="/api/library", tags=["library"])
SessionDependency = Annotated[Session, Depends(get_session)]


def library_error(error: Exception) -> HTTPException:
    if isinstance(
        error,
        library_service.LibraryRecordNotFoundError,
    ):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "LIBRARY_RECORD_NOT_FOUND",
                "message": str(error),
            },
        )

    raise TypeError("Unsupported Library service error.")


@router.get("", response_model=list[LibraryRecordRead])
def list_records(
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
    filters: Annotated[LibraryRecordListQuery, Query()],
) -> list[LibraryRecordRead]:
    return library_service.list_records(
        session,
        active_space,
        search=filters.search.strip() if filters.search else None,
        kind=filters.kind,
        sort_by=filters.sort_by,
        sort_direction=filters.sort_direction,
    )


@router.post(
    "",
    response_model=LibraryRecordRead,
    status_code=status.HTTP_201_CREATED,
)
def create_record(
    data: LibraryRecordCreate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> LibraryRecordRead:
    return library_service.create_record(
        session,
        active_space,
        data,
    )


@router.get(
    "/{record_id}",
    response_model=LibraryRecordRead,
)
def read_record(
    record_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> LibraryRecordRead:
    try:
        return library_service.require_record(
            session,
            active_space,
            record_id,
        )
    except library_service.LibraryRecordNotFoundError as error:
        raise library_error(error) from error


@router.patch(
    "/{record_id}",
    response_model=LibraryRecordRead,
)
def update_record(
    record_id: str,
    data: LibraryRecordUpdate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> LibraryRecordRead:
    try:
        return library_service.update_record(
            session,
            active_space,
            record_id,
            data,
        )
    except library_service.LibraryRecordNotFoundError as error:
        raise library_error(error) from error


@router.delete(
    "/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_record(
    record_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> Response:
    try:
        library_service.delete_record(
            session,
            active_space,
            record_id,
        )
    except library_service.LibraryRecordNotFoundError as error:
        raise library_error(error) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)
