from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class InputType(str, Enum):
    single_m4b = "single_m4b"
    single_m4a = "single_m4a"
    chapter_folder = "chapter_folder"
    unsupported = "unsupported"


class BookContext(BaseModel):
    source_path: Path
    input_type: InputType
    files: list[Path] = Field(default_factory=list)
    title: str | None = None
    author: str | None = None
    series: str | None = None
    series_index: int | None = None
    confidence: float = 0.0
    needs_human_review: bool = False