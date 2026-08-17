"""Partition changed files into reviewable and excluded sets — path-shaped, not finding-shaped.

Deliberately distinct from `exclusions.py`, which filters findings (RESEARCH.md Pitfall 5):
this module never imports `Finding`. Only the D-12 exclusion vocabulary and a minimal
extension allowlist are wired for the tracer path — glob-based "generated" exclusion and the
diff-line size cap ("too-large", D-11) land in 02-02, which also ports the full extension
allowlist from the OCR source (D-09/D-10).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sec_overlay.diffscope import ChangedFile

EXCLUSION_REASONS: frozenset[str] = frozenset(
    {"deleted", "binary", "generated", "not-allowlisted", "too-large"}
)
# ponytail: minimal set for the tracer fixture; 02-02 ports the full OCR allowlist.
ALLOWED_EXTENSIONS: frozenset[str] = frozenset({".py"})


@dataclass(frozen=True)
class ExcludedFile:
    """A changed file routed out of review, with the reason it was excluded."""

    path: str
    reason: str


@dataclass(frozen=True)
class Selection:
    """Changed files split into what review covers and what it skips."""

    reviewable: list[ChangedFile] = field(default_factory=list)
    excluded: list[ExcludedFile] = field(default_factory=list)


def partition(records: list[ChangedFile]) -> Selection:
    """Split changed-file records into reviewable and excluded (tracer-scoped).

    Args:
        records: Changed-file records from :func:`sec_overlay.diffscope.changed_file_records`.

    Returns:
        A Selection: a record lands in ``reviewable`` when its status is not a
        delete and its extension is in :data:`ALLOWED_EXTENSIONS`; otherwise it
        lands in ``excluded`` with a reason from :data:`EXCLUSION_REASONS`.
    """
    reviewable: list[ChangedFile] = []
    excluded: list[ExcludedFile] = []
    for record in records:
        if record.status == "D":
            excluded.append(ExcludedFile(path=record.path, reason="deleted"))
            continue
        suffix = f".{record.path.rsplit('.', 1)[-1]}" if "." in record.path else ""
        if suffix not in ALLOWED_EXTENSIONS:
            excluded.append(ExcludedFile(path=record.path, reason="not-allowlisted"))
            continue
        reviewable.append(record)
    return Selection(reviewable=reviewable, excluded=excluded)
