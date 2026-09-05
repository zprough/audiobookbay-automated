from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class DecisionAction(str, Enum):
    merge_to_m4b = "merge_to_m4b"
    fetch_metadata = "fetch_metadata"
    fetch_cover = "fetch_cover"
    rename_and_move = "rename_and_move"
    validate_output = "validate_output"


class Decision(BaseModel):
    book_title: str | None = None
    author: str | None = None
    series: str | None = None
    series_index: int | None = None
    recommended_actions: list[DecisionAction] = Field(default_factory=list)
    confidence: float = 0.0
    needs_human_review: bool = False