"""Confirm or decline a finding's claimed position against the diff — never approximate.

The OCR resolver this mirrors matches exact consecutive strings only; a fuzzy match
presented as an exact location is the defect this phase exists to prevent (RESEARCH.md
Pitfall 2), so this module never imports the stdlib sequence-matching helper. Returns the
phase's own result type rather than a `models.FindingStatus` member — `models.py` is the
frozen milestone contract and has no review-position member (RESEARCH.md Pitfall 4).

The ladder in `resolve_position` runs four rungs in order and stops at the first rung that
produces exactly one match: hunk match in the claimed file, whole-file match in the claimed
file, cross-file match in exactly one other changed file, then decline. Two or more matches
at any rung decline instead of picking one — an unverifiable claim declines, it never guesses.
"""

from __future__ import annotations

from dataclasses import dataclass

from sec_overlay.diffhunks import Hunk

POSITION_DECISIONS: frozenset[str] = frozenset({"exact", "relocated", "needs-position-review"})
DECLINE_REASONS: frozenset[str] = frozenset(
    {"no-hunk-match", "ambiguous-multiple-matches", "no-snippet", "cross-file-ambiguous"}
)
RELOCATION_REASONS: frozenset[str] = frozenset({"whole-file-match", "cross-file-match"})


@dataclass(frozen=True)
class PositionResult:
    """The outcome of resolving one finding's claimed position.

    `__post_init__` refuses to construct a `needs-position-review` result that carries a
    line number, so no downstream consumer can read a guess out of a declined result.

    Attributes:
        decision: One of `POSITION_DECISIONS`.
        path: The confirmed file path, or `None` on a decline.
        line: The confirmed 1-based line number, or `None` on a decline.
        reason: The decline reason (from `DECLINE_REASONS`) or relocation reason (from
            `RELOCATION_REASONS`); `None` on an `exact` decision.
        claimed_path: The original claimed path, carried on every result including declines.
        claimed_line: The original claimed line, carried on every result including declines.
        snippet: The original claimed snippet, carried on every result including declines so
            the report section can show what the finding claimed without a second lookup.

    Raises:
        ValueError: `decision` is not in `POSITION_DECISIONS`, a `needs-position-review`
            result carries a line or a reason outside `DECLINE_REASONS`, a `relocated`
            result carries no line or a reason outside `RELOCATION_REASONS`, or an `exact`
            result carries no line.
    """

    decision: str
    path: str | None
    line: int | None
    reason: str | None
    claimed_path: str
    claimed_line: int
    snippet: str | None = None

    def __post_init__(self) -> None:
        if self.decision not in POSITION_DECISIONS:
            raise ValueError(f"unknown decision: {self.decision!r}")
        if self.decision == "needs-position-review":
            if self.reason not in DECLINE_REASONS:
                raise ValueError(f"needs-position-review requires a DECLINE_REASONS reason, got {self.reason!r}")
            if self.line is not None:
                raise ValueError("needs-position-review must not carry a line number")
        elif self.decision == "relocated":
            if self.reason not in RELOCATION_REASONS:
                raise ValueError(f"relocated requires a RELOCATION_REASONS reason, got {self.reason!r}")
            if self.line is None:
                raise ValueError("relocated must carry a line number")
        elif self.line is None:
            raise ValueError("exact must carry a line number")


def _match_consecutive(haystack_lines: list[str], needle_lines: list[str]) -> list[int]:
    """Find every 1-based start line where `needle_lines` appears consecutively.

    Lines are compared with leading and trailing whitespace stripped on both sides, so
    indentation reflow does not defeat a real match. No case folding, token normalization,
    or character-level similarity is applied.

    Args:
        haystack_lines: Lines to search.
        needle_lines: Lines to find, in order.

    Returns:
        Every 1-based start line at which `needle_lines` matches consecutively. Empty when
        `needle_lines` is empty or longer than `haystack_lines`.
    """
    needle_count = len(needle_lines)
    haystack_count = len(haystack_lines)
    if needle_count == 0 or needle_count > haystack_count:
        return []
    stripped_needle = [line.strip() for line in needle_lines]
    stripped_haystack = [line.strip() for line in haystack_lines]
    matches = []
    for start in range(haystack_count - needle_count + 1):
        if stripped_haystack[start : start + needle_count] == stripped_needle:
            matches.append(start + 1)
    return matches


def resolve_position(
    claimed_path: str,
    claimed_line: int,
    snippet: str | None,
    hunks_by_path: dict[str, list[Hunk]],
    file_text_by_path: dict[str, str],
) -> PositionResult:
    """Confirm or decline a finding's claimed location by walking the four-rung ladder.

    Rung 1 searches the claimed path's hunk-added lines. Rung 2 searches the claimed
    path's whole text. Rung 3 searches every other changed file's whole text. Rung 4
    declines. Each rung stops the ladder on exactly one match and declines on more than
    one; nothing beyond exact consecutive matching is attempted at any rung.

    Args:
        claimed_path: The file path the finding claims.
        claimed_line: The line number the finding claims.
        snippet: The finding's claimed code snippet. An absent or whitespace-only snippet
            declines immediately — there is nothing to verify the claimed line against.
        hunks_by_path: Parsed hunks for every reviewed file, keyed by path.
        file_text_by_path: Whole file text for every changed file, keyed by path.

    Returns:
        A `PositionResult` carrying `claimed_path`/`claimed_line` regardless of outcome.
    """
    if not snippet or not snippet.strip():
        return PositionResult(
            "needs-position-review", None, None, "no-snippet", claimed_path, claimed_line, snippet
        )

    needle_lines = snippet.splitlines()

    hunk_matches: list[int] = []
    for hunk in hunks_by_path.get(claimed_path, []):
        haystack = [content for _, content in hunk.added]
        line_numbers = [line for line, _ in hunk.added]
        for start in _match_consecutive(haystack, needle_lines):
            hunk_matches.append(line_numbers[start - 1])
    if len(hunk_matches) == 1:
        return PositionResult(
            "exact", claimed_path, hunk_matches[0], None, claimed_path, claimed_line, snippet
        )
    if len(hunk_matches) > 1:
        return PositionResult(
            "needs-position-review",
            None,
            None,
            "ambiguous-multiple-matches",
            claimed_path,
            claimed_line,
            snippet,
        )

    claimed_text = file_text_by_path.get(claimed_path)
    if claimed_text is not None:
        file_matches = _match_consecutive(claimed_text.splitlines(), needle_lines)
        if len(file_matches) == 1:
            return PositionResult(
                "relocated",
                claimed_path,
                file_matches[0],
                "whole-file-match",
                claimed_path,
                claimed_line,
                snippet,
            )
        if len(file_matches) > 1:
            return PositionResult(
                "needs-position-review",
                None,
                None,
                "ambiguous-multiple-matches",
                claimed_path,
                claimed_line,
                snippet,
            )

    cross_hits: list[tuple[str, int]] = []
    for path, text in file_text_by_path.items():
        if path == claimed_path:
            continue
        matches = _match_consecutive(text.splitlines(), needle_lines)
        if len(matches) > 1:
            return PositionResult(
                "needs-position-review",
                None,
                None,
                "cross-file-ambiguous",
                claimed_path,
                claimed_line,
                snippet,
            )
        if len(matches) == 1:
            cross_hits.append((path, matches[0]))
    if len(cross_hits) == 1:
        hit_path, hit_line = cross_hits[0]
        return PositionResult(
            "relocated", hit_path, hit_line, "cross-file-match", claimed_path, claimed_line, snippet
        )
    if len(cross_hits) > 1:
        return PositionResult(
            "needs-position-review",
            None,
            None,
            "cross-file-ambiguous",
            claimed_path,
            claimed_line,
            snippet,
        )

    return PositionResult(
        "needs-position-review", None, None, "no-hunk-match", claimed_path, claimed_line, snippet
    )
