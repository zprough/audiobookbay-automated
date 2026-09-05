from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
	pending = "pending"
	running = "running"
	succeeded = "succeeded"
	failed = "failed"


class Job(BaseModel):
	id: str
	source_path: Path
	created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
	status: JobStatus = JobStatus.pending
	attempts: int = 0

	def mark_running(self) -> None:
		self.status = JobStatus.running
		self.attempts += 1

	def mark_succeeded(self) -> None:
		self.status = JobStatus.succeeded

	def mark_failed(self) -> None:
		self.status = JobStatus.failed
