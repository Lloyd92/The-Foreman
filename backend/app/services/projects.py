from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.project import Project
from app.repositories import projects as project_repository
from app.schemas.project import ProjectCreate, ProjectUpdate


def list_projects(
    session: Session,
    *,
    include_archived: bool = False,
) -> list[Project]:
    return project_repository.list_projects(
        session,
        include_archived=include_archived,
    )


def require_project(
    session: Session,
    project_id: str,
) -> Project:
    project = project_repository.get_project(session, project_id)

    if project is None:
        raise LookupError("Project not found.")

    return project


def create_project(
    session: Session,
    data: ProjectCreate,
) -> Project:
    project = Project(**data.model_dump())

    try:
        project_repository.add_project(session, project)
        session.commit()
        session.refresh(project)
    except Exception:
        session.rollback()
        raise

    return project


def update_project(
    session: Session,
    project_id: str,
    data: ProjectUpdate,
) -> Project:
    project = require_project(session, project_id)

    if project.archived_at is not None:
        raise ValueError("Archived projects cannot be updated.")

    changes = data.model_dump(exclude_unset=True)

    for field, value in changes.items():
        setattr(project, field, value)

    try:
        session.commit()
        session.refresh(project)
    except Exception:
        session.rollback()
        raise

    return project


def archive_project(
    session: Session,
    project_id: str,
) -> Project:
    project = require_project(session, project_id)

    if project.archived_at is not None:
        return project

    project.status = "archived"
    project.archived_at = datetime.now(timezone.utc)

    try:
        session.commit()
        session.refresh(project)
    except Exception:
        session.rollback()
        raise

    return project
