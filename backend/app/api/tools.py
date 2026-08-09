from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.space_context import ActiveSpaceDependency
from app.schemas.tool import (
    ToolCreate,
    ToolListQuery,
    ToolRead,
    ToolUpdate,
)
from app.services import tools as tool_service


router = APIRouter(prefix="/api/tools", tags=["tools"])
SessionDependency = Annotated[Session, Depends(get_session)]


def tool_error(error: Exception) -> HTTPException:
    if isinstance(error, tool_service.ToolNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "TOOL_NOT_FOUND",
                "message": str(error),
            },
        )

    if isinstance(error, tool_service.ToolInUseError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "TOOL_IN_USE",
                "message": str(error),
            },
        )

    raise TypeError("Unsupported Tool service error.")


@router.get("", response_model=list[ToolRead])
def list_tools(
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
    filters: Annotated[ToolListQuery, Query()],
) -> list[ToolRead]:
    return tool_service.list_tools(
        session,
        active_space,
        search=filters.search.strip() if filters.search else None,
        category=filters.category,
        condition=filters.condition,
        availability=filters.availability,
        sort_by=filters.sort_by,
        sort_direction=filters.sort_direction,
    )


@router.post(
    "",
    response_model=ToolRead,
    status_code=status.HTTP_201_CREATED,
)
def create_tool(
    data: ToolCreate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> ToolRead:
    return tool_service.create_tool(
        session,
        active_space,
        data,
    )


@router.get("/{tool_id}", response_model=ToolRead)
def read_tool(
    tool_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> ToolRead:
    try:
        return tool_service.require_tool(
            session,
            active_space,
            tool_id,
        )
    except tool_service.ToolNotFoundError as error:
        raise tool_error(error) from error


@router.patch("/{tool_id}", response_model=ToolRead)
def update_tool(
    tool_id: str,
    data: ToolUpdate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> ToolRead:
    try:
        return tool_service.update_tool(
            session,
            active_space,
            tool_id,
            data,
        )
    except tool_service.ToolNotFoundError as error:
        raise tool_error(error) from error


@router.delete(
    "/{tool_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_tool(
    tool_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> Response:
    try:
        tool_service.delete_tool(
            session,
            active_space,
            tool_id,
        )
    except (
        tool_service.ToolNotFoundError,
        tool_service.ToolInUseError,
    ) as error:
        raise tool_error(error) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)
