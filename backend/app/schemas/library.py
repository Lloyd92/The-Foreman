from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from app.schemas.common import ApiModel


LibraryRecordKind = Literal[
    "note",
    "document",
    "manual",
    "receipt",
    "photo",
    "decision",
    "measurement",
    "cad_reference",
]

LibraryTitle = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=160,
    ),
]


class LibraryRecordCreate(ApiModel):
    kind: LibraryRecordKind
    title: LibraryTitle
    content: str = Field(default="", max_length=10000)
    reference_location: str = Field(default="", max_length=1000)


class LibraryRecordUpdate(ApiModel):
    kind: LibraryRecordKind | None = None
    title: LibraryTitle | None = None
    content: str | None = Field(default=None, max_length=10000)
    reference_location: str | None = Field(
        default=None,
        max_length=1000,
    )

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError(
                "Provide at least one Library record field to update."
            )

        if any(
            getattr(self, field) is None
            for field in self.model_fields_set
        ):
            raise ValueError(
                "Library record fields cannot be null."
            )

        return self


class LibraryRecordListQuery(ApiModel):
    search: str | None = Field(default=None, max_length=160)
    kind: LibraryRecordKind | None = None
    sort_by: Literal[
        "title",
        "kind",
        "created_at",
        "updated_at",
    ] = "title"
    sort_direction: Literal["asc", "desc"] = "asc"


class LibraryRecordRead(ApiModel):
    id: str
    kind: LibraryRecordKind
    title: str
    content: str
    reference_location: str
    created_at: datetime
    updated_at: datetime
