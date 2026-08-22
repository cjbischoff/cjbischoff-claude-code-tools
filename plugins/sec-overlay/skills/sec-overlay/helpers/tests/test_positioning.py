"""Tests for the never-guess positioning ladder: exact matching, then decline."""

import pytest

from sec_overlay.diffhunks import Hunk
from sec_overlay.positioning import (
    DECLINE_REASONS,
    POSITION_DECISIONS,
    RELOCATION_REASONS,
    PositionResult,
    _match_consecutive,
    resolve_position,
)


def _hunk(new_start: int, added: list[tuple[int, str]]) -> Hunk:
    return Hunk(
        old_start=new_start,
        old_count=1,
        new_start=new_start,
        new_count=len(added) or 1,
        added=tuple(added),
    )


# --- _match_consecutive ---


def test_match_consecutive_single_occurrence():
    assert _match_consecutive(["a", "b", "c"], ["b"]) == [2]


def test_match_consecutive_two_occurrences():
    assert _match_consecutive(["x", "b", "y", "b"], ["b"]) == [2, 4]


def test_match_consecutive_no_occurrence():
    assert _match_consecutive(["a", "b", "c"], ["z"]) == []


def test_match_consecutive_strips_whitespace_on_both_sides():
    assert _match_consecutive(["   foo   "], ["foo"]) == [1]
    assert _match_consecutive(["foo"], ["   foo   "]) == [1]


def test_match_consecutive_does_not_ignore_case():
    assert _match_consecutive(["foo"], ["fOo"]) == []


def test_match_consecutive_empty_needle_returns_empty():
    assert _match_consecutive(["a", "b"], []) == []


def test_match_consecutive_multiline_needle_requires_both_lines():
    haystack = ["one", "two", "three"]
    assert _match_consecutive(haystack, ["one", "two"]) == [1]
    assert _match_consecutive(haystack, ["one", "nope"]) == []


def test_match_consecutive_needle_longer_than_haystack():
    assert _match_consecutive(["a"], ["a", "b"]) == []


# --- PositionResult validation ---


def test_position_result_exact_requires_line():
    with pytest.raises(ValueError, match="exact"):
        PositionResult("exact", "a.py", None, None, "a.py", 7)


def test_position_result_needs_position_review_rejects_line():
    with pytest.raises(ValueError, match="needs-position-review"):
        PositionResult("needs-position-review", "a.py", 7, "no-hunk-match", "a.py", 7)


def test_position_result_needs_position_review_requires_known_reason():
    with pytest.raises(ValueError, match="DECLINE_REASONS"):
        PositionResult("needs-position-review", None, None, "vibes", "a.py", 7)


def test_position_result_relocated_requires_line():
    with pytest.raises(ValueError, match="relocated"):
        PositionResult("relocated", "a.py", None, "whole-file-match", "a.py", 7)


def test_position_result_relocated_requires_known_reason():
    with pytest.raises(ValueError, match="RELOCATION_REASONS"):
        PositionResult("relocated", "a.py", 3, "no-hunk-match", "a.py", 7)


def test_position_result_rejects_unknown_decision():
    with pytest.raises(ValueError, match="unknown decision"):
        PositionResult("guessed", "a.py", 3, None, "a.py", 7)


def test_position_decisions_and_reasons_are_closed_vocabularies():
    assert POSITION_DECISIONS == {"exact", "relocated", "needs-position-review"}
    assert DECLINE_REASONS == {
        "no-hunk-match",
        "ambiguous-multiple-matches",
        "no-snippet",
        "cross-file-ambiguous",
    }
    assert RELOCATION_REASONS == {"whole-file-match", "cross-file-match"}


# --- resolve_position ladder ---


def test_rung1_single_hunk_match_is_exact():
    hunks = {"a.py": [_hunk(10, [(10, "os.system(cmd)")])]}
    result = resolve_position("a.py", 10, "os.system(cmd)", hunks, {})
    assert result.decision == "exact"
    assert result.path == "a.py"
    assert result.line == 10


def test_rung1_match_at_claimed_line_is_exact_at_that_line():
    hunks = {"a.py": [_hunk(10, [(10, "safe()"), (11, "os.system(cmd)")])]}
    result = resolve_position("a.py", 11, "os.system(cmd)", hunks, {})
    assert result.decision == "exact"
    assert result.line == 11


def test_rung1_two_hunk_matches_decline_ambiguous():
    hunks = {
        "a.py": [
            _hunk(10, [(10, "os.system(cmd)")]),
            _hunk(20, [(20, "os.system(cmd)")]),
        ]
    }
    result = resolve_position("a.py", 10, "os.system(cmd)", hunks, {})
    assert result.decision == "needs-position-review"
    assert result.reason == "ambiguous-multiple-matches"
    assert result.line is None


def test_rung2_whole_file_match_relocates():
    hunks = {"a.py": [_hunk(10, [(10, "safe()")])]}
    files = {"a.py": "line one\nos.system(cmd)\nline three\n"}
    result = resolve_position("a.py", 10, "os.system(cmd)", hunks, files)
    assert result.decision == "relocated"
    assert result.path == "a.py"
    assert result.line == 2
    assert result.reason == "whole-file-match"


def test_rung2_two_whole_file_matches_decline_ambiguous():
    hunks = {"a.py": [_hunk(10, [(10, "safe()")])]}
    files = {"a.py": "os.system(cmd)\nos.system(cmd)\n"}
    result = resolve_position("a.py", 10, "os.system(cmd)", hunks, files)
    assert result.decision == "needs-position-review"
    assert result.reason == "ambiguous-multiple-matches"


def test_rung3_cross_file_match_relocates():
    hunks = {"a.py": [_hunk(10, [(10, "safe()")])], "b.py": []}
    files = {"a.py": "safe()\n", "b.py": "line one\nos.system(cmd)\n"}
    result = resolve_position("a.py", 10, "os.system(cmd)", hunks, files)
    assert result.decision == "relocated"
    assert result.path == "b.py"
    assert result.line == 2
    assert result.reason == "cross-file-match"


def test_rung3_matches_in_two_files_decline_cross_file_ambiguous():
    hunks = {"a.py": [_hunk(10, [(10, "safe()")])], "b.py": [], "c.py": []}
    files = {
        "a.py": "safe()\n",
        "b.py": "os.system(cmd)\n",
        "c.py": "os.system(cmd)\n",
    }
    result = resolve_position("a.py", 10, "os.system(cmd)", hunks, files)
    assert result.decision == "needs-position-review"
    assert result.reason == "cross-file-ambiguous"


def test_rung4_no_match_anywhere_declines():
    hunks = {"a.py": [_hunk(10, [(10, "safe()")])]}
    files = {"a.py": "safe()\n"}
    result = resolve_position("a.py", 10, "os.system(cmd)", hunks, files)
    assert result.decision == "needs-position-review"
    assert result.reason == "no-hunk-match"
    assert result.line is None


def test_absent_snippet_declines_without_attempting_any_rung():
    hunks = {"a.py": [_hunk(10, [(10, "os.system(cmd)")])]}
    result = resolve_position("a.py", 10, None, hunks, {})
    assert result.decision == "needs-position-review"
    assert result.reason == "no-snippet"


def test_whitespace_only_snippet_declines():
    hunks = {"a.py": [_hunk(10, [(10, "os.system(cmd)")])]}
    result = resolve_position("a.py", 10, "   \n  ", hunks, {})
    assert result.reason == "no-snippet"


def test_claimed_path_absent_from_both_mappings_declines_not_raises():
    result = resolve_position("missing.py", 5, "os.system(cmd)", {}, {})
    assert result.decision == "needs-position-review"
    assert result.reason == "no-hunk-match"


def test_rung_order_rung1_wins_over_rung2():
    hunks = {"a.py": [_hunk(10, [(10, "os.system(cmd)")])]}
    files = {"a.py": "unrelated\nos.system(cmd)\nmore\nos.system(cmd)\n"}
    result = resolve_position("a.py", 10, "os.system(cmd)", hunks, files)
    assert result.decision == "exact"
    assert result.line == 10


def test_resolve_position_is_deterministic_across_calls():
    hunks = {"a.py": [_hunk(10, [(10, "os.system(cmd)")])]}
    first = resolve_position("a.py", 10, "os.system(cmd)", hunks, {})
    second = resolve_position("a.py", 10, "os.system(cmd)", hunks, {})
    assert first == second


def test_every_result_carries_the_original_claim():
    hunks = {"a.py": [_hunk(10, [(10, "safe()")])]}
    result = resolve_position("a.py", 99, "os.system(cmd)", hunks, {})
    assert result.claimed_path == "a.py"
    assert result.claimed_line == 99


def test_every_result_carries_the_original_snippet():
    hunks = {"a.py": [_hunk(10, [(10, "os.system(cmd)")])]}
    exact = resolve_position("a.py", 10, "os.system(cmd)", hunks, {})
    assert exact.snippet == "os.system(cmd)"
    declined = resolve_position("a.py", 10, "os.system(cmd)", {}, {})
    assert declined.snippet == "os.system(cmd)"
