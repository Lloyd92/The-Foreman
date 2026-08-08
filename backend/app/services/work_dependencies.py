from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.space import Space
from app.models.work_dependency import WorkDependency
from app.repositories import work_dependencies as dependency_repository
from app.schemas.work_dependency import WorkDependencyCreate
from app.services.projects import require_project
from app.services.tasks import require_task


class WorkDependencyNotFoundError(LookupError):
    pass


class WorkDependencyEndpointNotFoundError(LookupError):
    pass


class WorkDependencyAlreadyExistsError(ValueError):
    pass


class WorkDependencySelfReferenceError(ValueError):
    pass


class WorkDependencyCycleError(ValueError):
    pass


def list_work_dependencies(
    session: Session,
    active_space: Space,
) -> list[WorkDependency]:
    return dependency_repository.list_work_dependencies(
        session,
        active_space.id,
    )


def require_work_dependency(
    session: Session,
    active_space: Space,
    dependency_id: str,
) -> WorkDependency:
    dependency = dependency_repository.get_work_dependency(
        session,
        active_space.id,
        dependency_id,
    )

    if dependency is None:
        raise WorkDependencyNotFoundError(
            "The requested Work dependency does not exist."
        )

    return dependency


def _require_endpoint(
    session: Session,
    active_space: Space,
    *,
    endpoint_type: str,
    endpoint_id: str,
    endpoint_label: str,
) -> None:
    try:
        if endpoint_type == "task":
            require_task(
                session,
                active_space,
                endpoint_id,
            )
            return

        if endpoint_type == "project":
            require_project(
                session,
                active_space,
                endpoint_id,
            )
            return
    except LookupError as error:
        raise WorkDependencyEndpointNotFoundError(
            f"The {endpoint_label} Work endpoint does not exist "
            "in the active Space."
        ) from error

    raise TypeError("Unsupported Work dependency endpoint type.")


def _would_create_cycle(
    dependencies: list[WorkDependency],
    data: WorkDependencyCreate,
) -> bool:
    dependent = (
        data.dependent_type,
        data.dependent_id,
    )
    prerequisite = (
        data.prerequisite_type,
        data.prerequisite_id,
    )

    adjacency: dict[
        tuple[str, str],
        set[tuple[str, str]],
    ] = {}

    for dependency in dependencies:
        source = (
            dependency.dependent_type,
            dependency.dependent_id,
        )
        target = (
            dependency.prerequisite_type,
            dependency.prerequisite_id,
        )
        adjacency.setdefault(source, set()).add(target)

    pending = [prerequisite]
    visited: set[tuple[str, str]] = set()

    while pending:
        node = pending.pop()

        if node == dependent:
            return True

        if node in visited:
            continue

        visited.add(node)
        pending.extend(adjacency.get(node, ()))

    return False


def create_work_dependency(
    session: Session,
    active_space: Space,
    data: WorkDependencyCreate,
) -> WorkDependency:
    try:
        _require_endpoint(
            session,
            active_space,
            endpoint_type=data.dependent_type,
            endpoint_id=data.dependent_id,
            endpoint_label="dependent",
        )
        _require_endpoint(
            session,
            active_space,
            endpoint_type=data.prerequisite_type,
            endpoint_id=data.prerequisite_id,
            endpoint_label="prerequisite",
        )

        if (
            data.dependent_type == data.prerequisite_type
            and data.dependent_id == data.prerequisite_id
        ):
            raise WorkDependencySelfReferenceError(
                "Work cannot depend on itself."
            )

        existing = (
            dependency_repository.get_work_dependency_for_endpoints(
                session,
                active_space.id,
                dependent_type=data.dependent_type,
                dependent_id=data.dependent_id,
                prerequisite_type=data.prerequisite_type,
                prerequisite_id=data.prerequisite_id,
            )
        )

        if existing is not None:
            raise WorkDependencyAlreadyExistsError(
                "That Work dependency already exists."
            )

        dependencies = dependency_repository.list_work_dependencies(
            session,
            active_space.id,
        )

        if _would_create_cycle(dependencies, data):
            raise WorkDependencyCycleError(
                "That Work dependency would create a cycle."
            )

        dependency = WorkDependency(
            space_id=active_space.id,
            **data.model_dump(),
        )
        dependency_repository.add_work_dependency(
            session,
            dependency,
        )
        session.commit()
        session.refresh(dependency)
    except IntegrityError as error:
        session.rollback()
        raise WorkDependencyAlreadyExistsError(
            "That Work dependency already exists."
        ) from error
    except Exception:
        session.rollback()
        raise

    return dependency


def delete_work_dependency(
    session: Session,
    active_space: Space,
    dependency_id: str,
) -> None:
    try:
        dependency = require_work_dependency(
            session,
            active_space,
            dependency_id,
        )
        dependency_repository.delete_work_dependency(
            session,
            dependency,
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
