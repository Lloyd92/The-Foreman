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
from app.schemas.work_tool_requirement import (
    WorkToolRequirementCreate,
    WorkToolRequirementListQuery,
    WorkToolRequirementRead,
    WorkToolRequirementUpdate,
)
from app.services import (
    work_tool_requirements as requirement_service,
)


router = APIRouter(
    prefix="/api/work-tool-requirements",
    tags=["work-tool-requirements"],
)
SessionDependency = Annotated[Session, Depends(get_session)]


def work_tool_requirement_error(
    error: Exception,
) -> HTTPException:
    if isinstance(
        error,
        requirement_service.WorkToolRequirementNotFoundError,
    ):
        code = "WORK_TOOL_REQUIREMENT_NOT_FOUND"
        response_status = status.HTTP_404_NOT_FOUND

    elif isinstance(
        error,
        requirement_service.WorkToolRequirementWorkNotFoundError,
    ):
        code = "WORK_TOOL_REQUIREMENT_WORK_NOT_FOUND"
        response_status = status.HTTP_404_NOT_FOUND

    elif isinstance(
        error,
        requirement_service.WorkToolRequirementToolNotFoundError,
    ):
        code = "WORK_TOOL_REQUIREMENT_TOOL_NOT_FOUND"
        response_status = status.HTTP_404_NOT_FOUND

    elif isinstance(
        error,
        requirement_service.WorkToolRequirementAlreadyExistsError,
    ):
        code = "WORK_TOOL_REQUIREMENT_ALREADY_EXISTS"
        response_status = status.HTTP_409_CONFLICT

    else:
        raise TypeError(
            "Unsupported Work Tool requirement service error."
        )

    return HTTPException(
        status_code=response_status,
        detail={
            "code": code,
            "message": str(error),
        },
    )


@router.get(
    "",
    response_model=list[WorkToolRequirementRead],
)
def list_work_tool_requirements(
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
    filters: Annotated[
        WorkToolRequirementListQuery,
        Query(),
    ],
) -> list[WorkToolRequirementRead]:
    return requirement_service.list_work_tool_requirements(
        session,
        active_space,
        work_type=filters.work_type,
        work_id=filters.work_id,
        tool_id=filters.tool_id,
    )


@router.post(
    "",
    response_model=WorkToolRequirementRead,
    status_code=status.HTTP_201_CREATED,
)
def create_work_tool_requirement(
    data: WorkToolRequirementCreate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> WorkToolRequirementRead:
    try:
        return requirement_service.create_work_tool_requirement(
            session,
            active_space,
            data,
        )
    except (
        requirement_service.WorkToolRequirementWorkNotFoundError,
        requirement_service.WorkToolRequirementToolNotFoundError,
        requirement_service.WorkToolRequirementAlreadyExistsError,
    ) as error:
        raise work_tool_requirement_error(error) from error


@router.get(
    "/{requirement_id}",
    response_model=WorkToolRequirementRead,
)
def read_work_tool_requirement(
    requirement_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> WorkToolRequirementRead:
    try:
        return requirement_service.require_work_tool_requirement(
            session,
            active_space,
            requirement_id,
        )
    except (
        requirement_service.WorkToolRequirementNotFoundError
    ) as error:
        raise work_tool_requirement_error(error) from error


@router.patch(
    "/{requirement_id}",
    response_model=WorkToolRequirementRead,
)
def update_work_tool_requirement(
    requirement_id: str,
    data: WorkToolRequirementUpdate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> WorkToolRequirementRead:
    try:
        return requirement_service.update_work_tool_requirement(
            session,
            active_space,
            requirement_id,
            data,
        )
    except (
        requirement_service.WorkToolRequirementNotFoundError,
        requirement_service.WorkToolRequirementToolNotFoundError,
        requirement_service.WorkToolRequirementAlreadyExistsError,
    ) as error:
        raise work_tool_requirement_error(error) from error


@router.delete(
    "/{requirement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_work_tool_requirement(
    requirement_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> Response:
    try:
        requirement_service.delete_work_tool_requirement(
            session,
            active_space,
            requirement_id,
        )
    except (
        requirement_service.WorkToolRequirementNotFoundError
    ) as error:
        raise work_tool_requirement_error(error) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)
