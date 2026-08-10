from sqlalchemy import asc, desc, or_, select
from sqlalchemy.orm import Session

from app.models.tool import Tool
from app.models.tool_maintenance_record import (
    ToolMaintenanceRecord,
)


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


def list_maintenance_records(
    session: Session,
    space_id: str,
    tool_id: str,
) -> list[ToolMaintenanceRecord]:
    statement = (
        select(ToolMaintenanceRecord)
        .where(
            ToolMaintenanceRecord.space_id == space_id,
            ToolMaintenanceRecord.tool_id == tool_id,
        )
        .order_by(
            desc(ToolMaintenanceRecord.performed_at),
            asc(ToolMaintenanceRecord.id),
        )
    )

    return list(session.scalars(statement))


def get_maintenance_record(
    session: Session,
    space_id: str,
    tool_id: str,
    record_id: str,
) -> ToolMaintenanceRecord | None:
    statement = select(ToolMaintenanceRecord).where(
        ToolMaintenanceRecord.id == record_id,
        ToolMaintenanceRecord.space_id == space_id,
        ToolMaintenanceRecord.tool_id == tool_id,
    )

    return session.scalar(statement)


def add_maintenance_record(
    session: Session,
    record: ToolMaintenanceRecord,
) -> ToolMaintenanceRecord:
    session.add(record)
    session.flush()
    session.refresh(record)
    return record


def delete_maintenance_record(
    session: Session,
    record: ToolMaintenanceRecord,
) -> None:
    session.delete(record)


def tool_names_by_ids(
    session: Session,
    space_id: str,
    tool_ids: set[str],
) -> dict[str, str]:
    if not tool_ids:
        return {}

    statement = select(
        Tool.id,
        Tool.name,
    ).where(
        Tool.space_id == space_id,
        Tool.id.in_(tool_ids),
    )

    return {
        tool_id: name
        for tool_id, name in session.execute(statement)
    }
