from __future__ import annotations

from agent.deciders.base import BaseDecider
from agent.models.book_context import BookContext, InputType
from agent.models.decision import Decision, DecisionAction


class RuleBasedDecider(BaseDecider):
    def decide(self, context: BookContext) -> Decision:
        actions: list[DecisionAction] = []

        if context.input_type == InputType.chapter_folder:
            actions.append(DecisionAction.merge_to_m4b)

        if context.input_type in {InputType.single_m4b, InputType.single_m4a, InputType.chapter_folder}:
            actions.extend(
                [
                    DecisionAction.fetch_metadata,
                    DecisionAction.fetch_cover,
                    DecisionAction.rename_and_move,
                    DecisionAction.validate_output,
                ]
            )

        needs_review = context.needs_human_review or context.input_type == InputType.unsupported
        confidence = 0.9 if not needs_review else 0.2
        return Decision(
            book_title=context.title,
            author=context.author,
            series=context.series,
            series_index=context.series_index,
            recommended_actions=actions,
            confidence=confidence,
            needs_human_review=needs_review,
        )