"""Retract-only reflection filter: an LLM verdict can remove a finding, never add one.

Mirrors `evidence.py`'s "code decides, not the LLM's claim" discipline
(D-16): `apply_verdict` is the sole authority over which findings are
retracted, and `PROTECTED_SUBJECT_CLASSES` is a hardcoded veto no verdict
can override, regardless of what the LLM's mapping says.

`build_payload` deliberately omits severity, category, and suggestion from
the LLM's input so the filter cannot rank or rewrite a finding, only ask to
remove it.

Every retraction and every fail-open skip is a `ReflectionRetraction` /
`ReflectionSkip` record for the never-silent ledger (D-14/D-15) — the
caller is responsible for collecting and rendering these, never dropping
them silently.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

RETRACTED_REASON = "reflection-retracted"
SKIPPED_REASON = "reflection-skipped"

# Subject classes an LLM verdict can never retract, regardless of its
# analysis text (D-16). Code-owned veto, not configurable.
PROTECTED_SUBJECT_CLASSES = frozenset(
    {
        "memory-safety",
        "concurrency",
        "linkage",
        "compatibility",
        "unused-parameter",
    }
)


class _ReflectableFinding(Protocol):
    """Structural shape `apply_verdict`/`build_payload` need from a finding.

    `message` is deliberately absent: `build_payload` reads it defensively via
    `getattr(f, "message", "")` since not every caller's finding type carries it.
    """

    id: str
    line: int
    rule_id: str
    cls: str


@dataclass(frozen=True)
class ReflectionComment:
    """One finding's payload sent to the reflection LLM for a retract/keep verdict.

    Deliberately carries no severity, category, or suggestion field — the
    filter can only ask to remove a finding, never rank or rewrite one.
    """

    id: str
    content: str
    existing_code: str


@dataclass(frozen=True)
class ReflectionRetraction:
    """Record of a finding the reflection filter retracted."""

    path: str
    line: int
    rule_id: str
    reason: str
    analysis: str


@dataclass(frozen=True)
class ReflectionSkip:
    """Record of a file whose reflection pass was skipped (fail-open, D-15)."""

    path: str
    reason: str
    error: str


def build_payload(
    path: str,
    findings: Sequence[_ReflectableFinding],
    file_text_by_path: dict[str, str],
) -> list[ReflectionComment]:
    """Build the reflection LLM's per-file input payload from kept findings.

    Args:
        path: The file's path, used to look up `file_text_by_path`.
        findings: Findings already surviving the position gate.
        file_text_by_path: Full file text by path, for the flagged line's
            surrounding code (empty string if the path is absent).

    Returns:
        One :class:`ReflectionComment` per finding, in input order.
    """
    text = file_text_by_path.get(path, "")
    lines = text.splitlines()
    comments: list[ReflectionComment] = []
    for f in findings:
        existing_code = lines[f.line - 1] if 0 < f.line <= len(lines) else ""
        comments.append(ReflectionComment(f.id, getattr(f, "message", ""), existing_code))
    return comments


def apply_verdict(
    findings: Sequence[_ReflectableFinding],
    verdict: dict[str, str],
    *,
    path: str,
) -> tuple[list[_ReflectableFinding], list[ReflectionRetraction]]:
    """Apply an LLM retract-verdict to kept findings, retract-only (D-16).

    A finding retracts only if its id is a key in `verdict` AND its `cls`
    is not in :data:`PROTECTED_SUBJECT_CLASSES`. An id in `verdict` that
    was never submitted (not in `findings`) is silently ignored — the
    verdict can only act on what it was shown.

    Args:
        findings: Findings surviving the position gate for this file.
        verdict: Mapping of finding id -> the LLM's retraction analysis text.
        path: The file's path, recorded on each retraction.

    Returns:
        ``(kept, retractions)`` — findings not retracted, and a record per
        retraction, sorted by ``(path, line, rule_id)`` for the ledger.
    """
    kept: list[_ReflectableFinding] = []
    retractions: list[ReflectionRetraction] = []
    for f in findings:
        if f.id in verdict and f.cls not in PROTECTED_SUBJECT_CLASSES:
            retractions.append(
                ReflectionRetraction(path, f.line, f.rule_id, RETRACTED_REASON, verdict[f.id])
            )
        else:
            kept.append(f)
    retractions.sort(key=lambda r: (r.path, r.line, r.rule_id))
    return kept, retractions
