from __future__ import annotations

import logging

import requests

from agent.config import Settings
from agent.deciders.base import BaseDecider
from agent.models.book_context import BookContext
from agent.models.decision import Decision

logger = logging.getLogger(__name__)


class OllamaDecider(BaseDecider):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def decide(self, context: BookContext) -> Decision:
        prompt = self._build_prompt(context)
        try:
            response = requests.post(
                f"{self.settings.ollama_base_url}/api/generate",
                json={
                    "model": self.settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
                timeout=self.settings.llm_timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            raw = payload.get("response", "")
            decision = Decision.model_validate_json(raw)
            if decision.confidence < self.settings.llm_min_confidence:
                decision.needs_human_review = True
            return decision
        except Exception as error:
            logger.warning("Ollama decision failed: %s", error)
            return Decision(
                book_title=context.title,
                author=context.author,
                series=context.series,
                series_index=context.series_index,
                confidence=0.0,
                needs_human_review=True,
            )

    def _build_prompt(self, context: BookContext) -> str:
        file_list = "\n".join(str(item) for item in context.files)
        return (
            "Return a JSON object with keys book_title, author, series, series_index, "
            "recommended_actions, confidence, needs_human_review.\n"
            f"source: {context.source_path}\n"
            f"files:\n{file_list}\n"
        )