from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.space import Space
from app.models.work_tool_requirement import WorkToolRequirement
from app.repositories import tools as tool_repository
from app.repositories import (
    work_tool_requirements as requirement_repository,
)
from app.schemas.work_tool_requirement import (
    WorkToolRequirementCreate,
    WorkToolRequirementRead,
    WorkToolRequirementUpdate,
)
from app.services.projects import require_project
from app.services.tasks import require_task


class WorkToolRequirementNotFoundError(LookupError):
    pass


class WorkToolRequirementWorkNotFoundError(LookupError):
    pass


class WorkToolRequirementToolNotFoundError(LookupError):
    pass


class WorkToolRequirementAlreadyExistsError(ValueError):
    pass


def _tool_names(
    session: Session,
    active_space: Space,
    requirements: list[WorkToolRequirement],
) -> dict[str, str]:
    return tool_repository.tool_names_by_ids(
        session,
        active_space.id,
        {
            requirement.tool_id
            for requirement in requirements
        },
    )


def serialize_work_tool_requirements(
    session: Session,
    active_space: Space,
    requirements: list[WorkToolRequirement],
) -> list[WorkToolRequirementRead]:
    tool_names = _tool_names(
        session,
        active_space,
        requirements,
    )

    return [
        WorkToolRequirementRead(
            id=requirement.id,
            work_type=requirement.work_type,
            work_id=requirement.work_id,
            tool_id=requirement.tool_id,
            tool_name=tool_names.get(requirement.tool_id),
            tool_exists=requirement.tool_id in tool_names,
            note=requirement.note,
            created_at=requirement.created_at,
        )
        for requirement in requirements
    ]


def serialize_work_tool_requirement(
    session: Session,
    active_space: Space,
    requirement: WorkToolRequirement,
) -> WorkToolRequirementRead:
    return serialize_work_tool_requirements(
        session,
        active_space,
        [requirement],
    )[0]


def list_work_tool_requirements(
    session: Session,
    active_space: Space,
    *,
    work_type: str | None = None,
    work_id: str | None = None,
    tool_id: str | None = None,
) -> list[WorkToolRequirementRead]:
    requirements = (
        requirement_repository.list_work_tool_requirements(
            session,
            active_space.id,
            work_type=work_type,
            work_id=work_id,
            tool_id=tool_id,
        )
    )

    return serialize_work_tool_requirements(
        session,
        active_space,
        requirements,
    )


def require_work_tool_requirement_model(
    session: Session,
    active_space: Space,
    requirement_id: str,
) -> WorkToolRequirement:
    requirement = (
        requirement_repository.get_work_tool_requirement(
            session,
            active_space.id,
            requirement_id,
        )
    )

    if requirement is None:
        raise WorkToolRequirementNotFoundError(
            "The requested Work Tool requirement does not exist."
        )

    return requirement


def require_work_tool_requirement(
    session: Session,
    active_space: Space,
    requirement_id: str,
) -> WorkToolRequirementRead:
    return serialize_work_tool_requirement(
        session,
        active_space,
        require_work_tool_requirement_model(
            session,
            active_space,
            requirement_id,
        ),
    )


def _require_work(
    session: Session,
    active_space: Space,
    *,
    work_type: str,
    work_id: str,
) -> None:
    try:
        if work_type == "task":
            require_task(
                session,
                active_space,
                work_id,
            )
            return

        if work_type == "project":
            require_project(
                session,
                active_space,
                work_id,
            )
            return
    except LookupError as error:
        raise WorkToolRequirementWorkNotFoundError(
            "The referenced Work record does not exist "
            "in the active Space."
        ) from error

    raise TypeError(
        "Unsupported Work Tool requirement owner type."
    )


def _require_tool(
    session: Session,
    active_space: Space,
    tool_id: str,
) -> None:
    tool = tool_repository.get_tool(
        session,
        active_space.id,
        tool_id,
    )

    if tool is None:
        raise WorkToolRequirementToolNotFoundError(
            "The referenced Tool does not exist "
            "in the active Space."
        )


def create_work_tool_requirement(
    session: Session,
    active_space: Space,
    data: WorkToolRequirementCreate,
) -> WorkToolRequirementRead:
    try:
        _require_work(
            session,
            active_space,
            work_type=data.work_type,
            work_id=data.work_id,
        )
        _require_tool(
            session,
            active_space,
            data.tool_id,
        )

        existing = (
            requirement_repository
            .get_work_tool_requirement_for_relationship(
                session,
                active_space.id,
                work_type=data.work_type,
                work_id=data.work_id,
                tool_id=data.tool_id,
            )
        )

        if existing is not None:
            raise WorkToolRequirementAlreadyExistsError(
                "That Work Tool requirement already exists."
            )

        requirement = WorkToolRequirement(
            space_id=active_space.id,
            **data.model_dump(),
        )

        requirement_repository.add_work_tool_requirement(
            session,
            requirement,
        )

        session.commit()
        session.refresh(requirement)
    except IntegrityError as error:
        session.rollback()
        raise WorkToolRequirementAlreadyExistsError(
            "That Work Tool requirement already exists."
        ) from error
    except Exception:
        session.rollback()
        raise

    return serialize_work_tool_requirement(
        session,
        active_space,
        requirement,
    )


def update_work_tool_requirement(
    session: Session,
    active_space: Space,
    requirement_id: str,
    data: WorkToolRequirementUpdate,
) -> WorkToolRequirementRead:
    try:
        requirement = require_work_tool_requirement_model(
            session,
            active_space,
            requirement_id,
        )
        changes = data.model_dump(exclude_unset=True)

        if (
            "tool_id" in changes
            and changes["tool_id"] != requirement.tool_id
        ):
            _require_tool(
                session,
                active_space,
                changes["tool_id"],
            )

            existing = (
                requirement_repository
                .get_work_tool_requirement_for_relationship(
                    session,
                    active_space.id,
                    work_type=requirement.work_type,
                    work_id=requirement.work_id,
                    tool_id=changes["tool_id"],
                )
            )

            if (
                existing is not None
                and existing.id != requirement.id
            ):
                raise WorkToolRequirementAlreadyExistsError(
                    "That Work Tool requirement already exists."
                )

        for field, value in changes.items():
            setattr(requirement, field, value)

        session.commit()
        session.refresh(requirement)
    except IntegrityError as error:
        session.rollback()
        raise WorkToolRequirementAlreadyExistsError(
            "That Work Tool requirement already exists."
        ) from error
    except Exception:
        session.rollback()
        raise

    return serialize_work_tool_requirement(
        session,
        active_space,
        requirement,
    )


def delete_work_tool_requirement(
    session: Session,
    active_space: Space,
    requirement_id: str,
) -> None:
    try:
        requirement = require_work_tool_requirement_model(
            session,
            active_space,
            requirement_id,
        )

        requirement_repository.delete_work_tool_requirement(
            session,
            requirement,
        )

        session.commit()
    except Exception:
        session.rollback()
        raise
