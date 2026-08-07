from sqlalchemy.orm import Session

from app.core.module_registry import (
    MODULE_DEFINITIONS,
    get_module_definition,
)
from app.models.module_state import ModuleState, utc_now
from app.repositories import module_states as module_state_repository
from app.schemas.module_registry import (
    ModuleDefinition,
    ModuleRegistryRead,
)


class ModuleNotFoundError(LookupError):
    pass


class ModuleDependenciesUnsatisfiedError(ValueError):
    pass


class ModuleEnabledDependentsError(ValueError):
    pass


def require_module_definition(
    module_id: str,
) -> ModuleDefinition:
    definition = get_module_definition(module_id)

    if definition is None:
        raise ModuleNotFoundError(
            "The requested module is not registered."
        )

    return definition


def _state_mapping(
    session: Session,
) -> dict[str, ModuleState]:
    return {
        state.module_id: state
        for state in module_state_repository.list_module_states(
            session
        )
    }


def _is_enabled(
    definition: ModuleDefinition,
    states: dict[str, ModuleState],
) -> bool:
    state = states.get(definition.module_id)

    if state is None:
        return definition.default_enabled

    return state.enabled


def _serialize(
    definition: ModuleDefinition,
    states: dict[str, ModuleState],
) -> ModuleRegistryRead:
    return ModuleRegistryRead(
        **definition.model_dump(),
        enabled=_is_enabled(definition, states),
        health="ready",
    )


def list_modules(
    session: Session,
) -> list[ModuleRegistryRead]:
    states = _state_mapping(session)

    return [
        _serialize(definition, states)
        for definition in MODULE_DEFINITIONS
    ]


def require_module(
    session: Session,
    module_id: str,
) -> ModuleRegistryRead:
    definition = require_module_definition(module_id)
    states = _state_mapping(session)

    return _serialize(definition, states)


def _enabled_dependency_ids(
    definition: ModuleDefinition,
    states: dict[str, ModuleState],
) -> tuple[str, ...]:
    missing = []

    for dependency_id in definition.dependencies:
        dependency = get_module_definition(dependency_id)

        if (
            dependency is None
            or not _is_enabled(dependency, states)
        ):
            missing.append(dependency_id)

    return tuple(missing)


def _enabled_dependent_ids(
    module_id: str,
    states: dict[str, ModuleState],
) -> tuple[str, ...]:
    return tuple(
        definition.module_id
        for definition in MODULE_DEFINITIONS
        if (
            module_id in definition.dependencies
            and _is_enabled(definition, states)
        )
    )


def set_module_enabled(
    session: Session,
    module_id: str,
    enabled: bool,
) -> ModuleRegistryRead:
    definition = require_module_definition(module_id)
    states = _state_mapping(session)
    current_enabled = _is_enabled(definition, states)

    if current_enabled == enabled:
        return _serialize(definition, states)

    if enabled:
        missing_dependencies = _enabled_dependency_ids(
            definition,
            states,
        )

        if missing_dependencies:
            raise ModuleDependenciesUnsatisfiedError(
                "Required module dependencies are not enabled: "
                + ", ".join(missing_dependencies)
                + "."
            )
    else:
        enabled_dependents = _enabled_dependent_ids(
            definition.module_id,
            states,
        )

        if enabled_dependents:
            raise ModuleEnabledDependentsError(
                "Enabled modules depend on this module: "
                + ", ".join(enabled_dependents)
                + "."
            )

    state = states.get(definition.module_id)

    if state is None:
        state = ModuleState(
            module_id=definition.module_id,
            enabled=enabled,
        )
        module_state_repository.add_module_state(
            session,
            state,
        )
    else:
        state.enabled = enabled
        state.updated_at = utc_now()

    try:
        session.commit()
        session.refresh(state)
    except Exception:
        session.rollback()
        raise

    states[definition.module_id] = state
    return _serialize(definition, states)
