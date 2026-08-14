from typing import Literal

from pydantic import Field

from app.schemas.common import ApiModel


SearchSourceType = Literal[
    "project",
    "task",
    "tool",
    "inventory",
    "care_plan",
    "calendar_entry",
    "calendar_series",
    "money_account",
    "money_category",
    "money_transaction",
    "money_budget",
    "money_obligation",
    "library_record",
    "person",
    "organization",
]


class SearchResultRead(ApiModel):
    source_type: SearchSourceType
    source_id: str
    title: str
    summary: str = Field(max_length=500)
    matched_text: str = Field(max_length=500)


class UniversalSearchRead(ApiModel):
    query: str
    results: list[SearchResultRead]
