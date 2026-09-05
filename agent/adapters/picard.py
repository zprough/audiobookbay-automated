from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from agent.models.result import OperationResult


class PicardAdapter:
	binary_name = "picard"

	def is_available(self) -> bool:
		return shutil.which(self.binary_name) is not None

	def tag_file(self, file_path: Path) -> OperationResult:
		if not self.is_available():
			return OperationResult(ok=False, message="picard binary not found")

		completed = subprocess.run(
			[self.binary_name, str(file_path)],
			capture_output=True,
			text=True,
		)
		if completed.returncode != 0:
			return OperationResult(
				ok=False,
				message="Picard metadata tagging failed",
				details={"stderr": completed.stderr.strip(), "stdout": completed.stdout.strip()},
			)

		return OperationResult(ok=True, message="Picard executed")
