from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import BeforeValidator, Field, StringConstraints, model_validator

from app.schemas.common import ApiModel


def normalize_module_id(value: object) -> object:
    if not isinstance(value, str):
        return value

    return value.strip().lower()


ModuleIdentifier = Annotated[
    str,
    BeforeValidator(normalize_module_id),
    StringConstraints(
        min_length=1,
        max_length=80,
        pattern=r"^[a-z][a-z0-9.-]*$",
    ),
]
ModuleName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=120,
    ),
]
ContributionLocation = Literal[
    "today",
    "calendar",
    "work",
    "resources",
    "money",
    "library",
    "settings",
]
SafeEnableRule = Literal["dependencies-satisfied"]
SafeDisableRule = Literal["no-enabled-dependents"]
DataRetentionBehavior = Literal["retain"]
ModuleHealth = Literal["ready"]


class ModuleDefinition(ApiModel):
    module_id: ModuleIdentifier
    name: ModuleName
    description: str = Field(max_length=2000)
    dependencies: tuple[ModuleIdentifier, ...] = Field(
        default=(),
        max_length=64,
    )
    contribution_locations: tuple[ContributionLocation, ...] = Field(
        default=(),
        max_length=7,
    )
    safe_enable_rule: SafeEnableRule = "dependencies-satisfied"
    safe_disable_rule: SafeDisableRule = "no-enabled-dependents"
    data_retention_behavior: DataRetentionBehavior = "retain"
    default_enabled: bool

    @model_validator(mode="after")
    def require_canonical_relationships(self) -> Self:
        if self.module_id in self.dependencies:
            raise ValueError("A module cannot depend on itself.")

        if len(self.dependencies) != len(set(self.dependencies)):
            raise ValueError("Module dependencies must be unique.")

        if len(self.contribution_locations) != len(
            set(self.contribution_locations)
        ):
            raise ValueError("Module contribution locations must be unique.")

        return self


class ModuleStateCreate(ApiModel):
    module_id: ModuleIdentifier
    enabled: bool


class ModuleStateUpdate(ApiModel):
    enabled: bool


class ModuleStateRead(ModuleStateCreate):
    created_at: datetime
    updated_at: datetime


class ModuleRegistryRead(ModuleDefinition):
    enabled: bool
    health: ModuleHealth = "ready"
