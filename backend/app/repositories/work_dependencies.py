from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.work_dependency import WorkDependency


def list_work_dependencies(
    session: Session,
    space_id: str,
) -> list[WorkDependency]:
    statement = (
        select(WorkDependency)
        .where(WorkDependency.space_id == space_id)
        .order_by(
            WorkDependency.dependent_type.asc(),
            WorkDependency.dependent_id.asc(),
            WorkDependency.prerequisite_type.asc(),
            WorkDependency.prerequisite_id.asc(),
            WorkDependency.id.asc(),
        )
    )
    return list(session.scalars(statement))


def get_work_dependency(
    session: Session,
    space_id: str,
    dependency_id: str,
) -> WorkDependency | None:
    statement = select(WorkDependency).where(
        WorkDependency.id == dependency_id,
        WorkDependency.space_id == space_id,
    )
    return session.scalar(statement)


def get_work_dependency_for_endpoints(
    session: Session,
    space_id: str,
    *,
    dependent_type: str,
    dependent_id: str,
    prerequisite_type: str,
    prerequisite_id: str,
) -> WorkDependency | None:
    statement = select(WorkDependency).where(
        WorkDependency.space_id == space_id,
        WorkDependency.dependent_type == dependent_type,
        WorkDependency.dependent_id == dependent_id,
        WorkDependency.prerequisite_type == prerequisite_type,
        WorkDependency.prerequisite_id == prerequisite_id,
    )
    return session.scalar(statement)


def add_work_dependency(
    session: Session,
    dependency: WorkDependency,
) -> WorkDependency:
    session.add(dependency)
    session.flush()
    return dependency


def delete_work_dependency(
    session: Session,
    dependency: WorkDependency,
) -> None:
    session.delete(dependency)
