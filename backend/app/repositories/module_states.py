from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.module_state import ModuleState


def list_module_states(
    session: Session,
) -> list[ModuleState]:
    return list(
        session.scalars(
            select(ModuleState).order_by(ModuleState.module_id)
        )
    )


def get_module_state(
    session: Session,
    module_id: str,
) -> ModuleState | None:
    return session.get(ModuleState, module_id)


def add_module_state(
    session: Session,
    state: ModuleState,
) -> None:
    session.add(state)
