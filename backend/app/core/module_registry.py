from app.schemas.module_registry import ModuleDefinition


MODULE_DEFINITIONS: tuple[ModuleDefinition, ...] = (
    ModuleDefinition(
        module_id="work",
        name="Work",
        description=(
            "Owns Tasks, Projects, requirements, dependencies, "
            "and progress."
        ),
        dependencies=(),
        contribution_locations=("today", "work"),
        default_enabled=True,
    ),
    ModuleDefinition(
        module_id="inventory",
        name="Inventory",
        description=(
            "Owns consumable stock, quantities, thresholds, "
            "locations, and usage."
        ),
        dependencies=(),
        contribution_locations=("today", "resources"),
        default_enabled=True,
    ),
    ModuleDefinition(
        module_id="tools",
        name="Tools",
        description=(
            "Owns durable equipment, condition, location, "
            "factual availability, and maintenance history."
        ),
        dependencies=(),
        contribution_locations=("resources",),
        default_enabled=True,
    ),
)


MODULE_DEFINITIONS_BY_ID = {
    definition.module_id: definition
    for definition in MODULE_DEFINITIONS
}


def get_module_definition(
    module_id: str,
) -> ModuleDefinition | None:
    return MODULE_DEFINITIONS_BY_ID.get(
        module_id.strip().lower()
    )
