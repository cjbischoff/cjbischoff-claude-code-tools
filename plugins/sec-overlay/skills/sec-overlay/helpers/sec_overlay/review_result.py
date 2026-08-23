"""Consolidated per-run review artifact (REQ-P7).

`write_review_result` serializes one `review_result.json` at the end of a review
consume pass. It mirrors the OCR reference `output.go` record: run status,
per-finding records, dropped/declined findings, reflection retractions/skips,
the coverage manifest, per-phase token records, base/head SHAs, and the
model/profile/tier the run used. It is additive — existing artifacts stay.
"""

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from .models import Severity
from .review_coverage import CoverageManifest
from .review_findings import ReviewFinding
from .workspace import Workspace, _atomic_write

RESULT_FILENAME = "review_result.json"

RESULT_KEYS = frozenset(
    {
        "status",
        "findings",
        "dropped",
        "declined",
        "retractions",
        "skips",
        "budget_exceeded",
        "coverage_manifest",
        "tokens",
        "base",
        "head",
        "model",
        "profile",
        "tier",
    }
)


def _as_dict(item: Any) -> Any:
    """Return a dataclass as a plain dict, or the item unchanged."""
    return asdict(item) if is_dataclass(item) and not isinstance(item, type) else item


def _finding_record(rf: ReviewFinding) -> dict[str, Any]:
    """Serialize one ReviewFinding to the documented seven-key record."""
    finding = rf.finding
    severity = finding.severity
    return {
        "id": finding.id,
        "path": finding.file,
        "line": finding.line,
        "severity": severity.value if isinstance(severity, Severity) else severity,
        "rule_id": finding.rule_id,
        "profile": rf.profile,
        "disposition": rf.disposition,
    }


def write_review_result(
    ws: Workspace,
    *,
    findings: list[ReviewFinding],
    dropped: list[Any],
    declines: list[Any],
    retractions: list[Any],
    skips: list[Any],
    manifest: CoverageManifest,
    budget_exceeded: bool,
    tokens: dict[str, Any],
    base: str,
    head: str,
    model: str | None,
    profile: str,
    tier: str | None,
) -> Path:
    """Write the consolidated review_result.json and return its path.

    Args:
        ws: The review workspace; the file lands in ``ws.artifacts``.
        findings: Reviewed findings to record (id/path/line/severity/rule_id/
            profile/disposition each).
        dropped: Profile/exclusion drops, as dicts or dataclasses.
        declines: Position-review declines, as dicts or dataclasses.
        retractions: Reflection retractions, as dicts or dataclasses.
        skips: Reflection skips, as dicts or dataclasses.
        manifest: Coverage manifest; its seal becomes ``status`` and its dict
            becomes ``coverage_manifest``.
        budget_exceeded: Whether the run hit its token budget.
        tokens: Per-phase token records (keys present even when empty).
        base: Base commit SHA.
        head: Head commit SHA.
        model: Review model, if known.
        profile: Review profile.
        tier: Assurance tier, if known.

    Returns:
        The path written (``ws.artifacts / review_result.json``).
    """
    coverage = manifest.to_dict()
    payload = {
        "status": coverage["seal"],
        "findings": [_finding_record(rf) for rf in findings],
        "dropped": [_as_dict(d) for d in dropped],
        "declined": [_as_dict(d) for d in declines],
        "retractions": [_as_dict(r) for r in retractions],
        "skips": [_as_dict(s) for s in skips],
        "budget_exceeded": budget_exceeded,
        "coverage_manifest": coverage,
        "tokens": tokens,
        "base": base,
        "head": head,
        "model": model,
        "profile": profile,
        "tier": tier,
    }
    path = ws.artifacts / RESULT_FILENAME
    _atomic_write(path, json.dumps(payload, indent=2))
    return path
