from sqlalchemy.orm import Session

from app.models.space import Space
from app.models.task import Task
from app.repositories import tasks as task_repository
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.members import require_member
from app.services.projects import require_project


def list_tasks(
    session: Session,
    active_space: Space,
) -> list[Task]:
    return task_repository.list_tasks(session, active_space.id)


def require_task(
    session: Session,
    active_space: Space,
    task_id: str,
) -> Task:
    task = task_repository.get_task(
        session,
        active_space.id,
        task_id,
    )

    if task is None:
        raise LookupError("Task not found.")

    return task


def validate_project_reference(
    session: Session,
    active_space: Space,
    project_id: str | None,
) -> None:
    if project_id is None:
        return

    project = require_project(
        session,
        active_space,
        project_id,
    )

    if project.archived_at is not None:
        raise ValueError("Tasks cannot be assigned to an archived project.")


def validate_responsible_member_reference(
    session: Session,
    active_space: Space,
    responsible_member_id: str | None,
) -> None:
    if responsible_member_id is None:
        return

    require_member(
        session,
        active_space,
        responsible_member_id,
    )


def create_task(
    session: Session,
    active_space: Space,
    data: TaskCreate,
) -> Task:
    validate_project_reference(
        session,
        active_space,
        data.project_id,
    )
    validate_responsible_member_reference(
        session,
        active_space,
        data.responsible_member_id,
    )
    task = Task(
        space_id=active_space.id,
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
    active_space: Space,
    task_id: str,
    data: TaskUpdate,
) -> Task:
    task = require_task(session, active_space, task_id)
    changes = data.model_dump(exclude_unset=True)

    if "project_id" in changes:
        validate_project_reference(
            session,
            active_space,
            changes["project_id"],
        )

    if "responsible_member_id" in changes:
        validate_responsible_member_reference(
            session,
            active_space,
            changes["responsible_member_id"],
        )

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
    active_space: Space,
    task_id: str,
    *,
    completed: bool,
) -> Task:
    task = require_task(session, active_space, task_id)
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
    active_space: Space,
    task_id: str,
) -> None:
    task = require_task(session, active_space, task_id)

    try:
        session.delete(task)
        session.commit()
    except Exception:
        session.rollback()
        raise
