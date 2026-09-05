from __future__ import annotations

import logging
from pathlib import Path

from agent.adapters.picard import PicardAdapter
from agent.adapters.tone import ToneAdapter
from agent.models.decision import Decision, DecisionAction
from agent.models.result import OperationResult

logger = logging.getLogger(__name__)


class MetadataService:
    def __init__(self, picard: PicardAdapter, tone: ToneAdapter, enable_picard: bool = False) -> None:
        self.picard = picard
        self.tone = tone
        self.enable_picard = enable_picard

    def enrich(self, audio_file: Path, decision: Decision) -> OperationResult:
        if DecisionAction.fetch_metadata not in decision.recommended_actions:
            return OperationResult(ok=True, message="Metadata step skipped", output_path=audio_file)

        # Picard is a GUI app with no reliable headless mode; skip unless explicitly enabled.
        if self.enable_picard:
            picard_result = self.picard.tag_file(audio_file)
            if not picard_result.ok:
                logger.warning("picard_tagging_failed message=%s", picard_result.message)

        # Tagging tools are best-effort: missing binaries must not block organize/move.
        tone_result = self.tone.apply_basic_metadata(audio_file, decision.book_title, decision.author)
        if not tone_result.ok:
            logger.warning("tone_tagging_failed message=%s", tone_result.message)
            return OperationResult(ok=True, message="Metadata tagging skipped", output_path=audio_file)
        return OperationResult(ok=True, message="Metadata enriched", output_path=audio_file)