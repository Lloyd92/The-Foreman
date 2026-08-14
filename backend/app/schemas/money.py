from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from app.schemas.common import ApiModel, StableId

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


MoneyDescription = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=200,
    ),
]


class MoneyTransactionCreate(ApiModel):
    account_id: StableId
    category_id: StableId | None = None
    kind: MoneyCategoryKind
    amount_minor: int = Field(gt=0)
    currency_code: CurrencyCode = "USD"
    occurred_on: date
    description: MoneyDescription
    counterparty: str = Field(default="", max_length=160)
    notes: str = Field(default="", max_length=2000)


class MoneyTransactionUpdate(ApiModel):
    account_id: StableId | None = None
    category_id: StableId | None = None
    kind: MoneyCategoryKind | None = None
    amount_minor: int | None = Field(default=None, gt=0)
    currency_code: CurrencyCode | None = None
    occurred_on: date | None = None
    description: MoneyDescription | None = None
    counterparty: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_valid_change(self):
        if not self.model_fields_set:
            raise ValueError(
                "Provide at least one Money Transaction field to update."
            )

        nullable_fields = {"category_id"}
        for field_name in self.model_fields_set:
            if (
                field_name not in nullable_fields
                and getattr(self, field_name) is None
            ):
                raise ValueError(
                    "Money Transaction update field cannot be null."
                )

        return self


class MoneyTransactionRead(ApiModel):
    id: str
    account_id: str
    category_id: str | None
    kind: MoneyCategoryKind
    amount_minor: int
    currency_code: str
    occurred_on: date
    description: str
    counterparty: str
    notes: str
    created_at: datetime
    updated_at: datetime


MoneyObligationFrequency = Literal[
    "once",
    "weekly",
    "monthly",
    "yearly",
]


class MoneyBudgetCreate(ApiModel):
    category_id: StableId | None = None
    name: MoneyName
    amount_minor: int = Field(gt=0)
    currency_code: CurrencyCode = "USD"
    start_date: date
    end_date: date
    notes: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def require_valid_dates(self):
        if self.end_date < self.start_date:
            raise ValueError(
                "Money Budget end date cannot be before start date."
            )
        return self


class MoneyBudgetUpdate(ApiModel):
    category_id: StableId | None = None
    name: MoneyName | None = None
    amount_minor: int | None = Field(default=None, gt=0)
    currency_code: CurrencyCode | None = None
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_valid_change(self):
        if not self.model_fields_set:
            raise ValueError(
                "Provide at least one Money Budget field to update."
            )
        return self


class MoneyBudgetRead(ApiModel):
    id: str
    category_id: str | None
    name: str
    amount_minor: int
    currency_code: str
    start_date: date
    end_date: date
    notes: str
    created_at: datetime
    updated_at: datetime


class MoneyObligationCreate(ApiModel):
    account_id: StableId | None = None
    category_id: StableId | None = None
    name: MoneyName
    amount_minor: int = Field(gt=0)
    currency_code: CurrencyCode = "USD"
    frequency: MoneyObligationFrequency
    interval_value: int = Field(default=1, gt=0)
    start_date: date
    end_date: date | None = None
    notes: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def require_valid_dates(self):
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError(
                "Money Obligation end date cannot be before start date."
            )
        return self


class MoneyObligationUpdate(ApiModel):
    account_id: StableId | None = None
    category_id: StableId | None = None
    name: MoneyName | None = None
    amount_minor: int | None = Field(default=None, gt=0)
    currency_code: CurrencyCode | None = None
    frequency: MoneyObligationFrequency | None = None
    interval_value: int | None = Field(default=None, gt=0)
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_valid_change(self):
        if not self.model_fields_set:
            raise ValueError(
                "Provide at least one Money Obligation field to update."
            )
        return self


class MoneyObligationRead(ApiModel):
    id: str
    account_id: str | None
    category_id: str | None
    name: str
    amount_minor: int
    currency_code: str
    frequency: MoneyObligationFrequency
    interval_value: int
    start_date: date
    end_date: date | None
    notes: str
    created_at: datetime
    updated_at: datetime



MoneyRelationshipMoneyType = Literal[
    "account",
    "category",
    "transaction",
    "budget",
    "obligation",
]
MoneyRelationshipTargetType = Literal[
    "task",
    "project",
    "tool",
    "inventory",
    "person",
    "organization",
]


class MoneyRelationshipCreate(ApiModel):
    money_type: MoneyRelationshipMoneyType
    money_id: StableId
    target_type: MoneyRelationshipTargetType
    target_id: StableId
    note: str = Field(default="", max_length=500)


class MoneyRelationshipUpdate(ApiModel):
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set or self.note is None:
            raise ValueError("Provide a non-null relationship field.")
        return self


class MoneyRelationshipRead(ApiModel):
    id: str
    money_type: MoneyRelationshipMoneyType
    money_id: str
    money_exists: bool
    target_type: MoneyRelationshipTargetType
    target_id: str
    target_exists: bool
    note: str
    created_at: datetime
