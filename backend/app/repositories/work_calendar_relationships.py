from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.work_calendar_relationship import WorkCalendarRelationship


def list_relationships(
    session: Session,
    space_id: str,
) -> list[WorkCalendarRelationship]:
    return list(
        session.scalars(
            select(WorkCalendarRelationship)
            .where(WorkCalendarRelationship.space_id == space_id)
            .order_by(WorkCalendarRelationship.created_at.asc())
        )
    )


def get_relationship(
    session: Session,
    space_id: str,
    relationship_id: str,
) -> WorkCalendarRelationship | None:
    return session.scalar(
        select(WorkCalendarRelationship).where(
            WorkCalendarRelationship.id == relationship_id,
            WorkCalendarRelationship.space_id == space_id,
        )
    )


def add_relationship(
    session: Session,
    relationship: WorkCalendarRelationship,
) -> WorkCalendarRelationship:
    session.add(relationship)
    session.flush()
    session.refresh(relationship)
    return relationship


def delete_relationship(
    session: Session,
    relationship: WorkCalendarRelationship,
) -> None:
    session.delete(relationship)


def delete_relationships_for_work(
    session: Session,
    space_id: str,
    *,
    work_type: str,
    work_id: str,
) -> None:
    session.execute(
        delete(WorkCalendarRelationship).where(
            WorkCalendarRelationship.space_id == space_id,
            WorkCalendarRelationship.work_type == work_type,
            WorkCalendarRelationship.work_id == work_id,
        )
    )
