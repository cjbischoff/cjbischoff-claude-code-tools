"""Confirm or decline a finding's claimed position against the diff — never approximate.

The OCR resolver this mirrors matches exact consecutive strings only; a fuzzy match
presented as an exact location is the defect this phase exists to prevent (RESEARCH.md
Pitfall 2), so this module never imports the stdlib sequence-matching helper. Returns the
phase's own result type rather than a `models.FindingStatus` member — `models.py` is the
frozen milestone contract and has no review-position member (RESEARCH.md Pitfall 4).
"""

from __future__ import annotations

from dataclasses import dataclass

from sec_overlay.diffhunks import Hunk, added_line_numbers

POSITION_DECISIONS: frozenset[str] = frozenset({"exact", "relocated", "needs-position-review"})


@dataclass(frozen=True)
class PositionResult:
    """The outcome of resolving one finding's claimed position."""

    decision: str
    path: str | None
    line: int | None
    reason: str | None
    claimed_path: str
    claimed_line: int


def resolve_position(
    claimed_path: str, claimed_line: int, hunks_by_path: dict[str, list[Hunk]]
) -> PositionResult:
    """Confirm or decline a finding's claimed location.

    Args:
        claimed_path: The file path the finding claims.
        claimed_line: The line number the finding claims.
        hunks_by_path: Parsed hunks for every reviewed file, keyed by path.

    Returns:
        A ``PositionResult`` with decision ``"exact"`` when ``claimed_line`` is
        an added line of a hunk in ``claimed_path``; otherwise
        ``"needs-position-review"`` with reason ``"no-hunk-match"``. The full
        relocation ladder (fuzzy/cross-file matching) lands in a later plan.
    """
    hunks = hunks_by_path.get(claimed_path, [])
    if claimed_line in added_line_numbers(hunks):
        return PositionResult(
            decision="exact",
            path=claimed_path,
            line=claimed_line,
            reason=None,
            claimed_path=claimed_path,
            claimed_line=claimed_line,
        )
    return PositionResult(
        decision="needs-position-review",
        path=None,
        line=None,
        reason="no-hunk-match",
        claimed_path=claimed_path,
        claimed_line=claimed_line,
    )
