from __future__ import annotations

import hashlib
import os
import re
import shutil
from pathlib import Path


class FilesystemService:
	_unsafe_chars = re.compile(r"[^\w\-.() ]+")

	@staticmethod
	def sanitize_component(value: str) -> str:
		sanitized = FilesystemService._unsafe_chars.sub("_", value).strip().strip(".")
		return sanitized or "unknown"

	@staticmethod
	def ensure_within(parent: Path, candidate: Path) -> Path:
		parent_resolved = parent.resolve()
		candidate_resolved = candidate.resolve()
		if parent_resolved not in candidate_resolved.parents and candidate_resolved != parent_resolved:
			raise ValueError(f"Path escapes parent directory: {candidate_resolved}")
		return candidate_resolved

	@staticmethod
	def fingerprint_path(path: Path) -> str:
		stat = path.stat()
		payload = f"{path.resolve()}:{stat.st_size}:{int(stat.st_mtime)}"
		return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

	def create_job_work_dir(self, work_root: Path, source_path: Path) -> Path:
		token = self.fingerprint_path(source_path)
		work_dir = work_root / token
		work_dir.mkdir(parents=True, exist_ok=True)
		return work_dir

	def safe_copy(self, source: Path, destination: Path) -> Path:
		destination.parent.mkdir(parents=True, exist_ok=True)
		shutil.copy2(source, destination)
		return destination

	def safe_move(self, source: Path, destination: Path) -> Path:
		destination.parent.mkdir(parents=True, exist_ok=True)
		shutil.move(str(source), str(destination))
		return destination

	@staticmethod
	def detect_duplicate(target_dir: Path, filename: str) -> bool:
		return (target_dir / filename).exists()

	@staticmethod
	def list_audio_files(path: Path) -> list[Path]:
		if path.is_file():
			return [path]

		found: list[Path] = []
		for root, _, files in os.walk(path):
			for file_name in files:
				candidate = Path(root) / file_name
				if candidate.suffix.lower() in {".m4b", ".m4a", ".mp3"}:
					found.append(candidate)
		return sorted(found)
