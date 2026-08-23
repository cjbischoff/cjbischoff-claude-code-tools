"""Token-size estimation for review-mode budgeting (REQ-P1, extended by REQ-P4).

`estimate_tokens` is the raw size primitive — OCR's `len(text) // 4`
characters-per-token heuristic. Bundle grouping (`bundle.py`) and sibling-context
capping (`review_agent.py`) share it for their size caps. REQ-P4's budget
projection (round-cost accounting) will build on this primitive rather than
redefine it, so one estimator governs every review-mode size decision.
"""

from __future__ import annotations


def estimate_tokens(text: str) -> int:
    """Estimate the token count of a text block.

    Uses OCR's `len // 4` characters-per-token heuristic — an approximation,
    not a real tokenizer. Sufficient for size caps where exactness is not
    required and a cheap, deterministic estimate matters more.

    Args:
        text: Any text (a diff, a prompt fragment).

    Returns:
        Estimated token count, `len(text) // 4`, never negative.

    Example:
        >>> estimate_tokens("abcdefgh")
        2
    """
    return len(text) // 4
