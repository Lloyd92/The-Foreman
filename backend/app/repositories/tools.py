from sqlalchemy import asc, desc, or_, select
from sqlalchemy.orm import Session

from app.models.tool import Tool


SORT_FIELDS = {
    "name": Tool.name,
    "category": Tool.category,
    "condition": Tool.condition,
    "location": Tool.location,
    "availability": Tool.availability,
}


def list_tools(
    session: Session,
    space_id: str,
    *,
    search: str | None = None,
    category: str | None = None,
    condition: str | None = None,
    availability: str | None = None,
    sort_by: str = "name",
    sort_direction: str = "asc",
) -> list[Tool]:
    statement = select(Tool).where(Tool.space_id == space_id)

    if search:
        pattern = f"%{search}%"
        statement = statement.where(
            or_(
                Tool.name.ilike(pattern),
                Tool.category.ilike(pattern),
                Tool.condition.ilike(pattern),
                Tool.location.ilike(pattern),
                Tool.availability.ilike(pattern),
            )
        )

    if category:
        statement = statement.where(Tool.category == category)

    if condition:
        statement = statement.where(Tool.condition == condition)

    if availability:
        statement = statement.where(
            Tool.availability == availability
        )

    sort_column = SORT_FIELDS[sort_by]
    order = (
        desc(sort_column)
        if sort_direction == "desc"
        else asc(sort_column)
    )

    statement = statement.order_by(
        order,
        asc(Tool.name),
        asc(Tool.id),
    )
    return list(session.scalars(statement))


def get_tool(
    session: Session,
    space_id: str,
    tool_id: str,
) -> Tool | None:
    statement = select(Tool).where(
        Tool.id == tool_id,
        Tool.space_id == space_id,
    )
    return session.scalar(statement)


def add_tool(
    session: Session,
    tool: Tool,
) -> Tool:
    session.add(tool)
    session.flush()
    session.refresh(tool)
    return tool


def delete_tool(
    session: Session,
    tool: Tool,
) -> None:
    session.delete(tool)
