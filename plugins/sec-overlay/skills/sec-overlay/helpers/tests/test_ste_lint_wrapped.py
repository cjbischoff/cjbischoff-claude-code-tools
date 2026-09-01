"""REQ-12: the mandated sentence lints clean and a wrapped list item is one line."""

from __future__ import annotations

from pathlib import Path

from sec_overlay.ste_lint import _prose_blocks, lint_prose

_CONSTANTS = Path(__file__).resolve().parents[2] / "references" / "prompt-constants.md"

_MANDATED = (
    "Prose follows an ASD-STE100-inspired clarity standard. "
    "A linter enforces the structural rules. The lexical dictionary stays unverified."
)


def test_the_mandated_sentence_lints_clean() -> None:
    errors, _ = lint_prose(_MANDATED)
    assert errors == []


def test_prompt_constants_publishes_the_reworded_sentence() -> None:
    text = _CONSTANTS.read_text()
    assert "structural rules enforced; lexical dictionary not verified" not in text
    assert "A linter enforces the structural rules." in text


def test_wrapped_list_item_counts_as_one_sentence() -> None:
    doc = "- The service reads a header value\n  and passes it to the client.\n"
    blocks, _ = _prose_blocks(doc)
    assert blocks == ["The service reads a header value and passes it to the client."]


def test_wrapped_list_item_still_flags_a_real_violation() -> None:
    tail = " ".join(["word"] * 30)
    doc = f"- The service reads a header value\n  and {tail}.\n"
    errors, _ = lint_prose(doc)
    assert any("sentence over 25 words" in e for e in errors)


def test_an_unindented_paragraph_after_a_list_stays_separate() -> None:
    doc = "- One item here.\nA separate paragraph follows.\n"
    blocks, _ = _prose_blocks(doc)
    assert blocks == ["One item here.", "A separate paragraph follows."]
