from __future__ import annotations

from agent.config import Settings
from agent.deciders.ollama_decider import OllamaDecider
from agent.deciders.rule_based import RuleBasedDecider
from agent.models.book_context import BookContext
from agent.models.decision import Decision


class DecisionService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.rule_decider = RuleBasedDecider()
        self.ollama_decider = OllamaDecider(settings)

    def decide(self, context: BookContext) -> Decision:
        base = self.rule_decider.decide(context)
        if not self.settings.enable_llm or self.settings.llm_provider != "ollama":
            return base

        llm_decision = self.ollama_decider.decide(context)
        if llm_decision.confidence >= self.settings.llm_min_confidence:
            return llm_decision
        return base