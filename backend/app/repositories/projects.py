from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project


def list_projects(
    session: Session,
    *,
    include_archived: bool = False,
) -> list[Project]:
    statement = select(Project).order_by(Project.created_at.desc())

    if not include_archived:
        statement = statement.where(Project.archived_at.is_(None))

    return list(session.scalars(statement))


def get_project(
    session: Session,
    project_id: str,
) -> Project | None:
    return session.get(Project, project_id)


def add_project(
    session: Session,
    project: Project,
) -> Project:
    session.add(project)
    session.flush()
    session.refresh(project)
    return project


def project_status_counts(session: Session) -> dict[str, int]:
    counts: dict[str, int] = {}

    for project in list_projects(session, include_archived=True):
        counts[project.status] = counts.get(project.status, 0) + 1

    return counts
