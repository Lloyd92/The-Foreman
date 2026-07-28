from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.task import Task


def list_tasks(session: Session) -> list[Task]:
    statement = select(Task).order_by(Task.created_at.desc())
    return list(session.scalars(statement))


def get_task(
    session: Session,
    task_id: str,
) -> Task | None:
    return session.get(Task, task_id)


def add_task(
    session: Session,
    task: Task,
) -> Task:
    session.add(task)
    session.flush()
    session.refresh(task)
    return task


def task_priority_counts(session: Session) -> dict[str, int]:
    counts = {"high": 0, "medium": 0, "low": 0}

    for task in list_tasks(session):
        counts[task.priority] = counts.get(task.priority, 0) + 1

    return counts
