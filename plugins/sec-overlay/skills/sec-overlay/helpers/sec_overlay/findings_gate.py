"""Deterministic gate: verify every finding file conforms to the schema."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sec_overlay.campaign import record_stage
from sec_overlay.evidence import RUNTIME_DISPOSITIONS, confirms_alone, receipt_tier
from sec_overlay.models import Finding
from sec_overlay.schema import validate as _schema_validate
from sec_overlay.workspace import Workspace

_FINDING_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "references" / "finding.schema.json"


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
    record_stage(ws, "findings-gate")
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
