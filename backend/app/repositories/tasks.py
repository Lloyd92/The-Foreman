from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.task import Task


def list_tasks(
    session: Session,
    space_id: str,
) -> list[Task]:
    statement = (
        select(Task)
        .where(Task.space_id == space_id)
        .order_by(Task.created_at.desc())
    )
    return list(session.scalars(statement))


def get_task(
    session: Session,
    space_id: str,
    task_id: str,
) -> Task | None:
    statement = select(Task).where(
        Task.id == task_id,
        Task.space_id == space_id,
    )
    return session.scalar(statement)


def add_task(
    session: Session,
    task: Task,
) -> Task:
    session.add(task)
    session.flush()
    session.refresh(task)
    return task


def task_priority_counts(
    session: Session,
    space_id: str,
) -> dict[str, int]:
    counts = {"high": 0, "medium": 0, "low": 0}

    for task in list_tasks(session, space_id):
        counts[task.priority] = counts.get(task.priority, 0) + 1

    return counts
