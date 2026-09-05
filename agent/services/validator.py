from __future__ import annotations

from pathlib import Path

from agent.models.result import OperationResult


class ValidatorService:
    def validate_output(self, output_dir: Path) -> OperationResult:
        if not output_dir.exists() or not output_dir.is_dir():
            return OperationResult(ok=False, message="Output directory does not exist")

        audio_files = [
            candidate
            for candidate in output_dir.iterdir()
            if candidate.is_file() and candidate.suffix.lower() in {".m4b", ".m4a"}
        ]
        if not audio_files:
            return OperationResult(ok=False, message="No final audiobook file found")

        return OperationResult(ok=True, message="Validation successful", output_path=audio_files[0])