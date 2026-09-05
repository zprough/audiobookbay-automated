from __future__ import annotations

from pathlib import Path

from agent.models.decision import Decision
from agent.models.result import OperationResult
from agent.services.filesystem import FilesystemService


class OrganizerService:
	def __init__(self, filesystem: FilesystemService, library_root: Path) -> None:
		self.filesystem = filesystem
		self.library_root = library_root

	def organize(self, audio_file: Path, decision: Decision) -> OperationResult:
		author = self.filesystem.sanitize_component(decision.author or "Unknown Author")
		title = self.filesystem.sanitize_component(decision.book_title or "Unknown Title")

		if decision.series:
			series = self.filesystem.sanitize_component(decision.series)
			index = decision.series_index or 1
			leaf = f"{index:02d} - {title}"
			target_dir = self.library_root / author / series / leaf
		else:
			target_dir = self.library_root / author / title

		destination_file = target_dir / f"{title}{audio_file.suffix.lower()}"
		if self.filesystem.detect_duplicate(target_dir, destination_file.name):
			return OperationResult(ok=False, message="Duplicate library entry detected")

		moved = self.filesystem.safe_move(audio_file, destination_file)
		return OperationResult(ok=True, message="Organized successfully", output_path=moved)
