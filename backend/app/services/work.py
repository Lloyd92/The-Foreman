from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.space import Space
from app.models.task import Task
from app.repositories import projects as project_repository
from app.repositories import tasks as task_repository
from app.repositories import work_dependencies as dependency_repository
from app.schemas.work import WorkItemRead, WorkRead
from app.schemas.work_dependency import WorkDependencyRead
from app.services import (
    work_tool_requirements as tool_requirement_service,
)


def _project_item(project: Project) -> WorkItemRead:
    return WorkItemRead(
        record_type="project",
        id=project.id,
        title=project.name,
        lifecycle_state=project.status,
        priority=project.priority,
        progress=project.progress,
        start_date=project.start_date,
        target_date=project.target_date,
        due_date=None,
        responsible_member_id=project.responsible_member_id,
        project_id=None,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def _task_item(task: Task) -> WorkItemRead:
    return WorkItemRead(
        record_type="task",
        id=task.id,
        title=task.title,
        lifecycle_state=(
            "completed"
            if task.completed
            else "open"
        ),
        priority=task.priority,
        progress=100.0 if task.completed else 0.0,
        start_date=None,
        target_date=None,
        due_date=task.due_date,
        responsible_member_id=task.responsible_member_id,
        project_id=task.project_id,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def _item_order(item: WorkItemRead) -> tuple[int, str, str, str]:
    type_order = {
        "project": 0,
        "task": 1,
    }

    return (
        type_order[item.record_type],
        item.title.casefold(),
        item.title,
        item.id,
    )


def get_work(
    session: Session,
    active_space: Space,
) -> WorkRead:
    projects = project_repository.list_projects(
        session,
        active_space.id,
        include_archived=True,
    )
    tasks = task_repository.list_tasks(
        session,
        active_space.id,
    )
    dependencies = dependency_repository.list_work_dependencies(
        session,
        active_space.id,
    )
    tool_requirements = (
        tool_requirement_service.list_work_tool_requirements(
            session,
            active_space,
        )
    )

    items = [
        *(_project_item(project) for project in projects),
        *(_task_item(task) for task in tasks),
    ]

    return WorkRead(
        items=sorted(items, key=_item_order),
        dependencies=[
            WorkDependencyRead.model_validate(dependency)
            for dependency in dependencies
        ],
        tool_requirements=tool_requirements,
    )
