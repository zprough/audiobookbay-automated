from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from agent.models.result import OperationResult


class M4BToolAdapter:
	binary_name = "m4b-tool"

	def is_available(self) -> bool:
		return shutil.which(self.binary_name) is not None

	def merge_mp3_folder(self, source_folder: Path, output_file: Path) -> OperationResult:
		if not self.is_available():
			return OperationResult(ok=False, message="m4b-tool binary not found")

		output_file.parent.mkdir(parents=True, exist_ok=True)
		command = [
			self.binary_name,
			"merge",
			"--jobs=1",
			f"--output-file={output_file}",
			str(source_folder),
		]
		completed = subprocess.run(command, capture_output=True, text=True)
		if completed.returncode != 0:
			return OperationResult(
				ok=False,
				message="m4b-tool merge failed",
				details={"stderr": completed.stderr.strip(), "stdout": completed.stdout.strip()},
			)

		return OperationResult(ok=True, message="Merged successfully", output_path=output_file)
