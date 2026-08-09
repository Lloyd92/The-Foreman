from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.space import Space
from app.models.tool import Tool
from app.repositories import tools as tool_repository
from app.schemas.tool import ToolCreate, ToolRead, ToolUpdate


class ToolNotFoundError(LookupError):
    pass


class ToolInUseError(ValueError):
    pass


def serialize_tool(tool: Tool) -> ToolRead:
    return ToolRead(
        id=tool.id,
        name=tool.name,
        category=tool.category,
        condition=tool.condition,
        location=tool.location,
        availability=tool.availability,
        notes=tool.notes,
        created_at=tool.created_at,
        updated_at=tool.updated_at,
    )


def list_tools(
    session: Session,
    active_space: Space,
    *,
    search: str | None = None,
    category: str | None = None,
    condition: str | None = None,
    availability: str | None = None,
    sort_by: str = "name",
    sort_direction: str = "asc",
) -> list[ToolRead]:
    return [
        serialize_tool(tool)
        for tool in tool_repository.list_tools(
            session,
            active_space.id,
            search=search,
            category=category,
            condition=condition,
            availability=availability,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )
    ]


def require_tool_model(
    session: Session,
    active_space: Space,
    tool_id: str,
) -> Tool:
    tool = tool_repository.get_tool(
        session,
        active_space.id,
        tool_id,
    )

    if tool is None:
        raise ToolNotFoundError(
            "The requested Tool does not exist."
        )

    return tool


def require_tool(
    session: Session,
    active_space: Space,
    tool_id: str,
) -> ToolRead:
    return serialize_tool(
        require_tool_model(
            session,
            active_space,
            tool_id,
        )
    )


def create_tool(
    session: Session,
    active_space: Space,
    data: ToolCreate,
) -> ToolRead:
    tool = Tool(
        space_id=active_space.id,
        **data.model_dump(),
    )

    try:
        tool_repository.add_tool(session, tool)
        session.commit()
        session.refresh(tool)
    except Exception:
        session.rollback()
        raise

    return serialize_tool(tool)


def update_tool(
    session: Session,
    active_space: Space,
    tool_id: str,
    data: ToolUpdate,
) -> ToolRead:
    tool = require_tool_model(
        session,
        active_space,
        tool_id,
    )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(tool, field, value)

    try:
        session.commit()
        session.refresh(tool)
    except Exception:
        session.rollback()
        raise

    return serialize_tool(tool)


def delete_tool(
    session: Session,
    active_space: Space,
    tool_id: str,
) -> None:
    tool = require_tool_model(
        session,
        active_space,
        tool_id,
    )

    try:
        tool_repository.delete_tool(session, tool)
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise ToolInUseError(
            "The Tool cannot be deleted while maintenance "
            "history references it."
        ) from error
    except Exception:
        session.rollback()
        raise
