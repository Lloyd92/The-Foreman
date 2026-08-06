from app.schemas.module_registry import ModuleDefinition

# Commit 2 defines the static configuration boundary only. The approved
# module catalog and enable-disable behavior arrive in Commit 7.
MODULE_DEFINITIONS: tuple[ModuleDefinition, ...] = ()
