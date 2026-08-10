from sqlalchemy.orm import Session

from app.models.care_plan import CarePlan
from app.models.space import Space
from app.repositories import care_plans as care_plan_repository
from app.repositories import tools as tool_repository
from app.schemas.care_plan import (
    CarePlanCreate,
    CarePlanRead,
    CarePlanUpdate,
)


class CarePlanNotFoundError(LookupError):
    pass


class CarePlanToolNotFoundError(ValueError):
    pass


def serialize_care_plan(
    care_plan: CarePlan,
) -> CarePlanRead:
    return CarePlanRead(
        id=care_plan.id,
        name=care_plan.name,
        care_type=care_plan.care_type,
        tool_id=care_plan.tool_id,
        description=care_plan.description,
        frequency_value=care_plan.frequency_value,
        frequency_unit=care_plan.frequency_unit,
        notes=care_plan.notes,
        created_at=care_plan.created_at,
        updated_at=care_plan.updated_at,
    )


def validate_tool_reference(
    session: Session,
    active_space: Space,
    tool_id: str | None,
) -> None:
    if tool_id is None:
        return

    tool = tool_repository.get_tool(
        session,
        active_space.id,
        tool_id,
    )

    if tool is None:
        raise CarePlanToolNotFoundError(
            "The referenced Tool does not exist in the active Space."
        )


def list_care_plans(
    session: Session,
    active_space: Space,
    *,
    search: str | None = None,
    care_type: str | None = None,
    tool_id: str | None = None,
    sort_by: str = "name",
    sort_direction: str = "asc",
) -> list[CarePlanRead]:
    return [
        serialize_care_plan(care_plan)
        for care_plan in care_plan_repository.list_care_plans(
            session,
            active_space.id,
            search=search,
            care_type=care_type,
            tool_id=tool_id,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )
    ]


def require_care_plan_model(
    session: Session,
    active_space: Space,
    care_plan_id: str,
) -> CarePlan:
    care_plan = care_plan_repository.get_care_plan(
        session,
        active_space.id,
        care_plan_id,
    )

    if care_plan is None:
        raise CarePlanNotFoundError(
            "The requested Care Plan does not exist."
        )

    return care_plan


def require_care_plan(
    session: Session,
    active_space: Space,
    care_plan_id: str,
) -> CarePlanRead:
    return serialize_care_plan(
        require_care_plan_model(
            session,
            active_space,
            care_plan_id,
        )
    )


def create_care_plan(
    session: Session,
    active_space: Space,
    data: CarePlanCreate,
) -> CarePlanRead:
    validate_tool_reference(
        session,
        active_space,
        data.tool_id,
    )

    care_plan = CarePlan(
        space_id=active_space.id,
        **data.model_dump(),
    )

    try:
        care_plan_repository.add_care_plan(
            session,
            care_plan,
        )
        session.commit()
        session.refresh(care_plan)
    except Exception:
        session.rollback()
        raise

    return serialize_care_plan(care_plan)


def update_care_plan(
    session: Session,
    active_space: Space,
    care_plan_id: str,
    data: CarePlanUpdate,
) -> CarePlanRead:
    care_plan = require_care_plan_model(
        session,
        active_space,
        care_plan_id,
    )

    changes = data.model_dump(exclude_unset=True)

    if "tool_id" in changes:
        validate_tool_reference(
            session,
            active_space,
            changes["tool_id"],
        )

    for field, value in changes.items():
        setattr(care_plan, field, value)

    try:
        session.commit()
        session.refresh(care_plan)
    except Exception:
        session.rollback()
        raise

    return serialize_care_plan(care_plan)


def delete_care_plan(
    session: Session,
    active_space: Space,
    care_plan_id: str,
) -> None:
    care_plan = require_care_plan_model(
        session,
        active_space,
        care_plan_id,
    )

    try:
        care_plan_repository.delete_care_plan(
            session,
            care_plan,
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
