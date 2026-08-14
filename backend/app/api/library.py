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
    LibraryRelationshipCreate,
    LibraryRelationshipRead,
    LibraryRelationshipUpdate,
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

    if isinstance(
        error,
        library_service.LibraryRelationshipNotFoundError,
    ):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "LIBRARY_RELATIONSHIP_NOT_FOUND",
                "message": str(error),
            },
        )

    if isinstance(
        error,
        library_service.LibraryRelationshipTargetNotFoundError,
    ):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "LIBRARY_RELATIONSHIP_TARGET_NOT_FOUND",
                "message": str(error),
            },
        )

    if isinstance(
        error,
        library_service.LibraryRelationshipConflictError,
    ):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "LIBRARY_RELATIONSHIP_CONFLICT",
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



@router.get(
    "/{record_id}/relationships",
    response_model=list[LibraryRelationshipRead],
)
def list_relationships(
    record_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> list[LibraryRelationshipRead]:
    try:
        return library_service.list_relationships(
            session,
            active_space,
            record_id,
        )
    except library_service.LibraryRecordNotFoundError as error:
        raise library_error(error) from error


@router.post(
    "/{record_id}/relationships",
    response_model=LibraryRelationshipRead,
    status_code=status.HTTP_201_CREATED,
)
def create_relationship(
    record_id: str,
    data: LibraryRelationshipCreate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> LibraryRelationshipRead:
    try:
        return library_service.create_relationship(
            session,
            active_space,
            record_id,
            data,
        )
    except (
        library_service.LibraryRecordNotFoundError,
        library_service.LibraryRelationshipTargetNotFoundError,
        library_service.LibraryRelationshipConflictError,
    ) as error:
        raise library_error(error) from error


@router.patch(
    "/{record_id}/relationships/{relationship_id}",
    response_model=LibraryRelationshipRead,
)
def update_relationship(
    record_id: str,
    relationship_id: str,
    data: LibraryRelationshipUpdate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> LibraryRelationshipRead:
    try:
        return library_service.update_relationship(
            session,
            active_space,
            record_id,
            relationship_id,
            data,
        )
    except (
        library_service.LibraryRecordNotFoundError,
        library_service.LibraryRelationshipNotFoundError,
    ) as error:
        raise library_error(error) from error


@router.delete(
    "/{record_id}/relationships/{relationship_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_relationship(
    record_id: str,
    relationship_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> Response:
    try:
        library_service.delete_relationship(
            session,
            active_space,
            record_id,
            relationship_id,
        )
    except (
        library_service.LibraryRecordNotFoundError,
        library_service.LibraryRelationshipNotFoundError,
    ) as error:
        raise library_error(error) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)
