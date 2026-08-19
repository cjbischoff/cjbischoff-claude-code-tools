"""Deterministic gate: verify every finding file conforms to the schema."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sec_overlay.campaign import record_stage
from sec_overlay.evidence import (
    RUNTIME_DISPOSITIONS,
    SHIPPING_STATUSES,
    confirms_alone,
    receipt_tier,
)
from sec_overlay.models import Finding
from sec_overlay.phase_gate import resolve_ref
from sec_overlay.review_findings import (
    GENERAL_DEFECT_CLASSES,
    NEEDS_DEPLOYMENT_TESTING_DISPOSITION,
    UNCONFIRMED_DISPOSITION,
)
from sec_overlay.schema import validate as _schema_validate
from sec_overlay.workspace import Workspace, read_findings

_FINDING_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "references" / "finding.schema.json"

# D-12 receipt-gate disposition ladder: a general-defect finding (REV-01) with no Tier-1
# receipt ships as a review-mode disposition, never as `confirmed`/`fixed` — those remain
# gated solely by `confirms_alone` below. Null dereference and error swallowing are visible
# from the code alone (no receipt needed to see the missing check); resource leak is the
# same for a missing close/release on every path. Injection is assigned here explicitly
# (not left to fall through a default) because its sink is what a Tier-1 tool (semgrep/
# codeql) already targets — the same reachability a receipt would confirm is what makes it
# statically checkable, unlike a race that only manifests under real concurrent load.
STATIC_CHECKABLE_CLASSES: frozenset[str] = frozenset(
    {"null-dereference", "error-swallowing", "resource-leak", "injection"}
)
RUNTIME_DEPENDENT_CLASSES: frozenset[str] = frozenset({"thread-safety"})

assert STATIC_CHECKABLE_CLASSES | RUNTIME_DEPENDENT_CLASSES == GENERAL_DEFECT_CLASSES
assert not (STATIC_CHECKABLE_CLASSES & RUNTIME_DEPENDENT_CLASSES)


def disposition_without_receipt(defect_class: str) -> str:
    """Pick the review-mode disposition for a general-defect finding with no Tier-1 receipt.

    This never grants `confirmed`/`fixed` — those remain the sole province of
    `confirms_alone` on the finding's evidence sources. It only decides what a
    general-defect finding ships as in the absence of that receipt (D-12, REV-03).

    Args:
        defect_class: A `review_findings.GENERAL_DEFECT_CLASSES` member.

    Returns:
        `NEEDS_DEPLOYMENT_TESTING_DISPOSITION` for a class in
        `RUNTIME_DEPENDENT_CLASSES`, else `UNCONFIRMED_DISPOSITION`.

    Raises:
        ValueError: `defect_class` is not a `GENERAL_DEFECT_CLASSES` member — a
            new class must be assigned here explicitly before it can ship.
    """
    if defect_class in RUNTIME_DEPENDENT_CLASSES:
        return NEEDS_DEPLOYMENT_TESTING_DISPOSITION
    if defect_class in STATIC_CHECKABLE_CLASSES:
        return UNCONFIRMED_DISPOSITION
    raise ValueError(f"disposition_without_receipt: unknown general-defect class {defect_class!r}")


def _load_finding_schema() -> dict:
    """Load the finding JSON schema.

    Returns:
        The parsed ``finding.schema.json`` contents.
    """
    return json.loads(_FINDING_SCHEMA_PATH.read_text())


def validate_findings(ws: Workspace) -> list[str]:
    """Validate all finding files in a workspace.

    Each ``findings/*.json`` must parse as a :class:`Finding` and have a
    non-empty ``file``, ``line >= 1``, and a list ``dataflow``.

    Args:
        ws: Workspace to inspect.

    Returns:
        Error strings ``"<id-or-filename>: <problem>"``; empty if all valid.
    """
    errors: list[str] = []
    for p in sorted(ws.findings_dir.glob("*.json")):
        try:
            data = json.loads(p.read_text())
            f = Finding.from_dict(data)
        except (ValueError, TypeError, KeyError) as exc:
            errors.append(f"{p.stem}: unparseable finding ({exc})")
            continue
        errors.extend(f"{p.stem}: {e}" for e in _schema_validate(data, _load_finding_schema()))
        if not f.file:
            errors.append(f"{f.id}: empty file")
        if f.line < 1:
            errors.append(f"{f.id}: line must be >= 1")
        if not isinstance(f.dataflow, list):
            errors.append(f"{f.id}: dataflow must be a list")
        if f.status.value in ("raw", "confirmed") and f.duplicate_of is not None:
            errors.append(
                f"{f.id}: {f.status.value} finding must not set duplicate_of "
                f"(set status=duplicate instead)"
            )
        # Safety contract, now enforced (was prose-only): a confirmed/fixed finding
        # must rest on at least one Tier-1 tool receipt (codeql/semgrep/sca/secrets).
        # A Tier-2 receipt (ripgrep/ast-grep/structural-index/tree-sitter) only locates
        # code — it does not prove reachability — so it routes to
        # needs-deployment-testing instead of confirming alone.
        tiers = [t for t in (receipt_tier(s) for s in f.evidence_sources) if t is not None]
        stamped_tier = min(tiers) if tiers else None  # 1 outranks 2
        if data.get("receipt_tier") != stamped_tier:
            data["receipt_tier"] = stamped_tier
            p.write_text(json.dumps(data))

        if f.status.value in ("confirmed", "fixed") and not confirms_alone(f.evidence_sources):
            errors.append(
                f"{f.id}: {f.status.value} finding has no Tier-1 tool receipt "
                f"(sources {f.evidence_sources or 'none'}) — a Tier-2-only match "
                f"(ripgrep/ast-grep/structural-index/tree-sitter) locates code but does "
                f"not prove reachability; route to needs-deployment-testing"
            )

        if f.runtime_disposition is not None and f.runtime_disposition not in RUNTIME_DISPOSITIONS:
            errors.append(
                f"{f.id}: runtime_disposition {f.runtime_disposition!r} is not one of "
                f"{sorted(RUNTIME_DISPOSITIONS)}"
            )

        if f.status.value in SHIPPING_STATUSES and not (f.impact or "").strip():
            errors.append(
                f"{f.id}: impact must be non-empty for a shipping finding "
                f"(status {f.status.value})"
            )
    record_stage(ws, "findings-gate")
    return errors


def validate_citations(
    ws: Workspace, root: str | Path, *, statuses: set[str] | None = None
) -> list[str]:
    """Reject shipping findings whose ``file:line`` citation does not resolve in ``root``.

    A ``line: 1`` anchor is rejected only when the reference does not resolve, so a
    genuine top-of-file finding survives while a placeholder anchor on a missing or
    short file does not. Control findings (``context.control_findings``) inherit the
    check because they flow through the same finding files.

    Args:
        ws: Workspace holding the findings to check.
        root: Target source root the citations point into.
        statuses: Finding statuses to gate; defaults to ``evidence.SHIPPING_STATUSES``.

    Returns:
        One error string per finding whose citation does not resolve; empty if all
        gated findings resolve.
    """
    gated = statuses if statuses is not None else SHIPPING_STATUSES
    errors: list[str] = []
    for f in read_findings(ws):
        if f.status.value not in gated:
            continue
        ok, _ = resolve_ref(root, f"{f.file}:{f.line}")
        if not ok:
            errors.append(f"{f.id}: citation {f.file}:{f.line} does not resolve")
    return errors


def main(argv: list[str] | None = None) -> int:
    """CLI: validate a workspace's findings and report errors.

    Args:
        argv: Optional argument vector.

    Returns:
        0 if all findings valid, 1 otherwise.
    """
    parser = argparse.ArgumentParser(prog="sec-overlay-findings-gate")
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args(argv)
    errors = validate_findings(Workspace(Path(args.workspace)))
    for e in errors:
        print(e)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
