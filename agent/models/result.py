from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class OperationResult(BaseModel):
	ok: bool
	message: str = ""
	output_path: Path | None = None
	details: dict[str, str] = Field(default_factory=dict)


class PipelineResult(BaseModel):
	success: bool
	job_id: str
	message: str
	final_path: Path | None = None
	needs_human_review: bool = False
