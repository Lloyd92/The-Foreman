from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.work_tool_requirement import WorkToolRequirement


def list_work_tool_requirements(
    session: Session,
    space_id: str,
    *,
    work_type: str | None = None,
    work_id: str | None = None,
    tool_id: str | None = None,
) -> list[WorkToolRequirement]:
    statement = select(WorkToolRequirement).where(
        WorkToolRequirement.space_id == space_id
    )

    if work_type is not None:
        statement = statement.where(
            WorkToolRequirement.work_type == work_type
        )

    if work_id is not None:
        statement = statement.where(
            WorkToolRequirement.work_id == work_id
        )

    if tool_id is not None:
        statement = statement.where(
            WorkToolRequirement.tool_id == tool_id
        )

    statement = statement.order_by(
        WorkToolRequirement.work_type.asc(),
        WorkToolRequirement.work_id.asc(),
        WorkToolRequirement.tool_id.asc(),
        WorkToolRequirement.id.asc(),
    )

    return list(session.scalars(statement))


def get_work_tool_requirement(
    session: Session,
    space_id: str,
    requirement_id: str,
) -> WorkToolRequirement | None:
    statement = select(WorkToolRequirement).where(
        WorkToolRequirement.id == requirement_id,
        WorkToolRequirement.space_id == space_id,
    )

    return session.scalar(statement)


def get_work_tool_requirement_for_relationship(
    session: Session,
    space_id: str,
    *,
    work_type: str,
    work_id: str,
    tool_id: str,
) -> WorkToolRequirement | None:
    statement = select(WorkToolRequirement).where(
        WorkToolRequirement.space_id == space_id,
        WorkToolRequirement.work_type == work_type,
        WorkToolRequirement.work_id == work_id,
        WorkToolRequirement.tool_id == tool_id,
    )

    return session.scalar(statement)


def add_work_tool_requirement(
    session: Session,
    requirement: WorkToolRequirement,
) -> WorkToolRequirement:
    session.add(requirement)
    session.flush()
    session.refresh(requirement)
    return requirement


def delete_work_tool_requirement(
    session: Session,
    requirement: WorkToolRequirement,
) -> None:
    session.delete(requirement)


def delete_requirements_for_work(
    session: Session,
    space_id: str,
    *,
    work_type: str,
    work_id: str,
) -> None:
    session.execute(
        delete(WorkToolRequirement).where(
            WorkToolRequirement.space_id == space_id,
            WorkToolRequirement.work_type == work_type,
            WorkToolRequirement.work_id == work_id,
        )
    )
