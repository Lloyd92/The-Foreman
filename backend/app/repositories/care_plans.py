from sqlalchemy import asc, desc, or_, select
from sqlalchemy.orm import Session

from app.models.care_plan import CarePlan


SORT_FIELDS = {
    "name": CarePlan.name,
    "careType": CarePlan.care_type,
}


def list_care_plans(
    session: Session,
    space_id: str,
    *,
    search: str | None = None,
    care_type: str | None = None,
    tool_id: str | None = None,
    sort_by: str = "name",
    sort_direction: str = "asc",
) -> list[CarePlan]:
    statement = select(CarePlan).where(
        CarePlan.space_id == space_id
    )

    if search:
        pattern = f"%{search}%"
        statement = statement.where(
            or_(
                CarePlan.name.ilike(pattern),
                CarePlan.care_type.ilike(pattern),
                CarePlan.description.ilike(pattern),
                CarePlan.notes.ilike(pattern),
            )
        )

    if care_type:
        statement = statement.where(
            CarePlan.care_type == care_type
        )

    if tool_id:
        statement = statement.where(
            CarePlan.tool_id == tool_id
        )

    sort_column = SORT_FIELDS[sort_by]
    order = (
        desc(sort_column)
        if sort_direction == "desc"
        else asc(sort_column)
    )

    statement = statement.order_by(
        order,
        asc(CarePlan.name),
        asc(CarePlan.id),
    )

    return list(session.scalars(statement))


def get_care_plan(
    session: Session,
    space_id: str,
    care_plan_id: str,
) -> CarePlan | None:
    statement = select(CarePlan).where(
        CarePlan.id == care_plan_id,
        CarePlan.space_id == space_id,
    )
    return session.scalar(statement)


def add_care_plan(
    session: Session,
    care_plan: CarePlan,
) -> CarePlan:
    session.add(care_plan)
    session.flush()
    session.refresh(care_plan)
    return care_plan


def delete_care_plan(
    session: Session,
    care_plan: CarePlan,
) -> None:
    session.delete(care_plan)
