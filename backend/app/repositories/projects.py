from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.project import Project
from app.models.project_material_requirement import (
    ProjectMaterialRequirement,
)


def list_projects(
    session: Session,
    space_id: str,
    *,
    include_archived: bool = False,
) -> list[Project]:
    statement = (
        select(Project)
        .options(selectinload(Project.material_requirements))
        .where(Project.space_id == space_id)
        .order_by(Project.created_at.desc())
    )

    if not include_archived:
        statement = statement.where(Project.archived_at.is_(None))

    return list(session.scalars(statement))


def get_project(
    session: Session,
    space_id: str,
    project_id: str,
) -> Project | None:
    statement = (
        select(Project)
        .options(selectinload(Project.material_requirements))
        .where(
            Project.id == project_id,
            Project.space_id == space_id,
        )
    )
    return session.scalar(statement)


def add_project(
    session: Session,
    project: Project,
) -> Project:
    session.add(project)
    session.flush()
    session.refresh(project)
    return project


def get_material_requirement(
    session: Session,
    *,
    project_id: str,
    inventory_item_id: str,
) -> ProjectMaterialRequirement | None:
    return session.get(
        ProjectMaterialRequirement,
        (project_id, inventory_item_id),
    )


def delete_project(
    session: Session,
    project: Project,
) -> None:
    session.delete(project)


def project_status_counts(
    session: Session,
    space_id: str,
) -> dict[str, int]:
    counts: dict[str, int] = {}

    for project in list_projects(
        session,
        space_id,
        include_archived=True,
    ):
        counts[project.status] = counts.get(project.status, 0) + 1

    return counts
