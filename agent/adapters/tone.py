from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from agent.models.result import OperationResult


class ToneAdapter:
	preferred_binary = "tone"
	fallback_binary = "kid3-cli"

	def _binary(self) -> str | None:
		if shutil.which(self.preferred_binary):
			return self.preferred_binary
		if shutil.which(self.fallback_binary):
			return self.fallback_binary
		return None

	def is_available(self) -> bool:
		return self._binary() is not None

	def apply_basic_metadata(
		self,
		file_path: Path,
		title: str | None,
		author: str | None,
	) -> OperationResult:
		binary = self._binary()
		if binary is None:
			return OperationResult(ok=False, message="tone/kid3-cli binary not found")

		completed = subprocess.run(
			[binary, str(file_path)],
			capture_output=True,
			text=True,
		)
		if completed.returncode != 0:
			return OperationResult(
				ok=False,
				message="Metadata edit command failed",
				details={"stderr": completed.stderr.strip(), "stdout": completed.stdout.strip()},
			)

		return OperationResult(
			ok=True,
			message="Metadata command executed",
			details={"title": title or "", "author": author or ""},
		)
