from __future__ import annotations

from pathlib import Path

from agent.adapters.m4b_tool import M4BToolAdapter
from agent.models.book_context import BookContext, InputType
from agent.models.decision import Decision, DecisionAction
from agent.models.result import OperationResult


class ConverterService:
	def __init__(self, m4b_tool: M4BToolAdapter) -> None:
		self.m4b_tool = m4b_tool

	def run(self, context: BookContext, decision: Decision, work_dir: Path) -> OperationResult:
		if DecisionAction.merge_to_m4b not in decision.recommended_actions:
			if context.files:
				return OperationResult(ok=True, message="No conversion needed", output_path=context.files[0])
			return OperationResult(ok=False, message="No source audio files available")

		if context.input_type != InputType.chapter_folder:
			return OperationResult(ok=False, message="Merge requested for unsupported input type")

		output_file = work_dir / "merged.m4b"
		return self.m4b_tool.merge_mp3_folder(context.source_path, output_file)
