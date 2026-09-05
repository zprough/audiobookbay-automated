from pathlib import Path

from agent.deciders.rule_based import RuleBasedDecider
from agent.models.book_context import BookContext, InputType
from agent.models.decision import DecisionAction
from agent.services.filesystem import FilesystemService


def test_rule_decider_merges_mp3_folder() -> None:
    context = BookContext(
        source_path=Path("/incoming/book"),
        input_type=InputType.chapter_folder,
        files=[Path("/incoming/book/01.mp3")],
        title="Title",
        author="Author",
    )

    decision = RuleBasedDecider().decide(context)

    assert DecisionAction.merge_to_m4b in decision.recommended_actions
    assert DecisionAction.rename_and_move in decision.recommended_actions
    assert not decision.needs_human_review


def test_sanitize_component_removes_unsafe_chars() -> None:
    fs = FilesystemService()
    result = fs.sanitize_component("../../Bad:Name?*")
    assert "/" not in result
    assert result


def test_ensure_within_rejects_escape(tmp_path: Path) -> None:
    fs = FilesystemService()
    parent = tmp_path / "parent"
    parent.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()

    try:
        fs.ensure_within(parent, outside)
        raised = False
    except ValueError:
        raised = True

    assert raised
