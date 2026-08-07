from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.space_context import ActiveSpaceDependency
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.services import tasks as task_service

router = APIRouter(prefix="/api/tasks", tags=["tasks"])
SessionDependency = Annotated[Session, Depends(get_session)]


def task_error(error: Exception) -> HTTPException:
    if isinstance(error, LookupError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )

    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=str(error),
    )


@router.get("", response_model=list[TaskRead])
def list_tasks(
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> list[TaskRead]:
    return task_service.list_tasks(session, active_space)


@router.post(
    "",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    data: TaskCreate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> TaskRead:
    try:
        return task_service.create_task(
            session,
            active_space,
            data,
        )
    except (LookupError, ValueError) as error:
        raise task_error(error) from error


@router.get("/{task_id}", response_model=TaskRead)
def read_task(
    task_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> TaskRead:
    try:
        return task_service.require_task(
            session,
            active_space,
            task_id,
        )
    except LookupError as error:
        raise task_error(error) from error


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: str,
    data: TaskUpdate,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> TaskRead:
    try:
        return task_service.update_task(
            session,
            active_space,
            task_id,
            data,
        )
    except (LookupError, ValueError) as error:
        raise task_error(error) from error


@router.post("/{task_id}/complete", response_model=TaskRead)
def complete_task(
    task_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> TaskRead:
    try:
        return task_service.set_task_completion(
            session,
            active_space,
            task_id,
            completed=True,
        )
    except LookupError as error:
        raise task_error(error) from error


@router.post("/{task_id}/reopen", response_model=TaskRead)
def reopen_task(
    task_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> TaskRead:
    try:
        return task_service.set_task_completion(
            session,
            active_space,
            task_id,
            completed=False,
        )
    except LookupError as error:
        raise task_error(error) from error


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_task(
    task_id: str,
    session: SessionDependency,
    active_space: ActiveSpaceDependency,
) -> Response:
    try:
        task_service.delete_task(
            session,
            active_space,
            task_id,
        )
    except LookupError as error:
        raise task_error(error) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)
