from sqlalchemy.orm import Session

from app.core.default_space import DEFAULT_SPACE_ID
from app.models.task import Task
from app.repositories import tasks as task_repository
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.projects import require_project


def list_tasks(session: Session) -> list[Task]:
    return task_repository.list_tasks(session)


def require_task(
    session: Session,
    task_id: str,
) -> Task:
    task = task_repository.get_task(session, task_id)

    if task is None:
        raise LookupError("Task not found.")

    return task


def validate_project_reference(
    session: Session,
    project_id: str | None,
) -> None:
    if project_id is None:
        return

    project = require_project(session, project_id)

    if project.archived_at is not None:
        raise ValueError("Tasks cannot be assigned to an archived project.")


def create_task(
    session: Session,
    data: TaskCreate,
) -> Task:
    validate_project_reference(session, data.project_id)
    task = Task(
        space_id=DEFAULT_SPACE_ID,
        **data.model_dump(),
    )

    try:
        task_repository.add_task(session, task)
        session.commit()
        session.refresh(task)
    except Exception:
        session.rollback()
        raise

    return task


def update_task(
    session: Session,
    task_id: str,
    data: TaskUpdate,
) -> Task:
    task = require_task(session, task_id)
    changes = data.model_dump(exclude_unset=True)

    if "project_id" in changes:
        validate_project_reference(session, changes["project_id"])

    for field, value in changes.items():
        setattr(task, field, value)

    try:
        session.commit()
        session.refresh(task)
    except Exception:
        session.rollback()
        raise

    return task


def set_task_completion(
    session: Session,
    task_id: str,
    *,
    completed: bool,
) -> Task:
    task = require_task(session, task_id)
    task.completed = completed

    try:
        session.commit()
        session.refresh(task)
    except Exception:
        session.rollback()
        raise

    return task


def delete_task(
    session: Session,
    task_id: str,
) -> None:
    task = require_task(session, task_id)

    try:
        session.delete(task)
        session.commit()
    except Exception:
        session.rollback()
        raise
