"""Group reviewable changed files into review units (SCALE-01).

Pure and total: no filesystem, subprocess, or `Workspace` access, and no path is
ever dropped or duplicated across the returned units. This task's grouping is
the degenerate case — one unit per file — so a single-file review run is
byte-identical in behavior to before bundling existed; real multi-file grouping
lands in a later plan.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass

from sec_overlay.diffscope import ChangedFile


def _unit_id(paths: Sequence[str]) -> str:
    """Derive a deterministic unit id from member paths (`_stable_finding_id` idiom)."""
    key = "|".join(paths)
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class ReviewUnit:
    """One or more reviewable files grouped for a single review pass."""

    unit_id: str
    files: tuple[str, ...]

    def __post_init__(self) -> None:
        """Reject a unit with no members.

        Raises:
            ValueError: If `files` is empty.
        """
        if not self.files:
            raise ValueError("ReviewUnit requires at least one file")


def group_bundles(reviewable: list[ChangedFile]) -> list[ReviewUnit]:
    """Group reviewable files into review units.

    Degenerate grouping only: one unit per file, input order preserved. Real
    grouping semantics (files that group travel together) land in a later plan.

    Args:
        reviewable: Files surviving `file_select.partition`, in selection order.

    Returns:
        One `ReviewUnit` per input file.
    """
    return [
        ReviewUnit(unit_id=_unit_id([record.path]), files=(record.path,)) for record in reviewable
    ]
