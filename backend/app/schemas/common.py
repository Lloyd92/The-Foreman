from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, StringConstraints
from pydantic.alias_generators import to_camel


def normalize_role(value: object) -> object:
    if not isinstance(value, str):
        return value

    return " ".join(value.strip().lower().split())


NormalizedRole = Annotated[
    str,
    BeforeValidator(normalize_role),
    StringConstraints(
        min_length=1,
        max_length=80,
        pattern=r"^[a-z0-9]+(?:[ -][a-z0-9]+)*$",
    ),
]

StableId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=36,
    ),
]


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
    )
