from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from app.schemas.common import ApiModel

MoneyAccountKind = Literal[
    "cash",
    "checking",
    "savings",
    "credit",
    "loan",
    "other",
]
MoneyCategoryKind = Literal["income", "expense"]

MoneyName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=120,
    ),
]
CurrencyCode = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        pattern=r"^[A-Z]{3}$",
    ),
]


class MoneyAccountCreate(ApiModel):
    name: MoneyName
    kind: MoneyAccountKind = "other"
    currency_code: CurrencyCode = "USD"
    opening_balance_minor: int = 0
    is_active: bool = True
    notes: str = Field(default="", max_length=2000)


class MoneyAccountUpdate(ApiModel):
    name: MoneyName | None = None
    kind: MoneyAccountKind | None = None
    currency_code: CurrencyCode | None = None
    opening_balance_minor: int | None = None
    is_active: bool | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_valid_change(self):
        if not self.model_fields_set:
            raise ValueError(
                "Provide at least one Money Account field to update."
            )

        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(
                    "Money Account update fields cannot be null."
                )

        return self


class MoneyAccountRead(ApiModel):
    id: str
    name: str
    kind: MoneyAccountKind
    currency_code: str
    opening_balance_minor: int
    is_active: bool
    notes: str
    created_at: datetime
    updated_at: datetime


class MoneyCategoryCreate(ApiModel):
    kind: MoneyCategoryKind
    name: MoneyName


class MoneyCategoryUpdate(ApiModel):
    kind: MoneyCategoryKind | None = None
    name: MoneyName | None = None

    @model_validator(mode="after")
    def require_valid_change(self):
        if not self.model_fields_set:
            raise ValueError(
                "Provide at least one Money Category field to update."
            )

        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(
                    "Money Category update fields cannot be null."
                )

        return self


class MoneyCategoryRead(ApiModel):
    id: str
    kind: MoneyCategoryKind
    name: str
    created_at: datetime
    updated_at: datetime
