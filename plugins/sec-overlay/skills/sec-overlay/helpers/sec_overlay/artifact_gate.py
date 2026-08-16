"""Deterministic gate over a run's own output artifacts (§4.8).

Runs first in the artifact-review phase, before the opus adversary. It is a cheap
mechanical check that the rendered report, per-finding detail files, and red-team
plan are internally consistent: no leftover constant/placeholder section, no
truncated triage cell, every shipping finding has a detail file and a red-team
directive, every triage ID resolves to a finding, and the context diagram obeys
the 10-node style cap (ISSUE-022). It never judges exploitability — that is the
adversary's job — and it never deletes a finding.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from sec_overlay.evidence import SHIPPING_STATUSES
from sec_overlay.workspace import Workspace, read_findings

# Constant/placeholder fragments that ISSUE-052 removed from the renderer. Their
# reappearance in report.md means a stale render or a regression.
_BANNED_FRAGMENTS = (
    "Confirmed Attack Scenario** (theoretical",
    "**8. Testing.** Negative:",
)
_TRIAGE_WHAT_MAX = 72  # matches report._short_title's default limit

# Ownership boundary between architecture/arc42.md and threat-model/threat-model.md
# (§6): a threat-model heading that restates an arc42 heading, or that names an
# arc42-owned structure section outright, is a duplication defect.
_ALLOWED_SHARED_HEADINGS = {"glossary", "introduction", "references"}
_STRUCTURE_HEADINGS = {
    "building block view", "solution strategy", "deployment view",
    "context and scope", "runtime view", "tech stack",
}


def _triage_rows(report_md: str) -> list[list[str]]:
    """Return the triage table's data rows as lists of stripped cells."""
    rows: list[list[str]] = []
    in_triage = False
    for line in report_md.splitlines():
        if line.strip().startswith("## Triage"):
            in_triage = True
            continue
        if in_triage and line.strip().startswith("## "):
            break
        if in_triage and line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells and cells[0] in ("ID", "----") or set("".join(cells)) <= set("-| "):
                continue
            rows.append(cells)
    return rows


def _mermaid_node_count(context_md: str) -> int | None:
    """Count nodes in the first mermaid block of CONTEXT.md, or None if absent."""
    m = re.search(r"```mermaid\n(.*?)```", context_md, re.DOTALL)
    if not m:
        return None
    ids: set[str] = set()
    for tok in re.findall(r"\b([A-Za-z][A-Za-z0-9_]*)\b(?=\[|\(|\{|-->|---)", m.group(1)):
        ids.add(tok)
    ids.discard("graph")
    ids.discard("flowchart")
    return len(ids)


def _headings(md: str) -> set[str]:
    """Return the lower-cased, number-stripped heading text of every ``#`` line."""
    return {
        re.sub(r"^[\d.\s]+", "", ln.lstrip("#").strip()).lower()
        for ln in md.splitlines()
        if ln.startswith("#")
    }


def check_duplication(arc42_text: str, tm_text: str) -> list[str]:
    """Flag threat-model sections that duplicate arc42 building-block content.

    Args:
        arc42_text: Content of ``architecture/arc42.md``.
        tm_text: Content of ``threat-model/threat-model.md``.

    Returns:
        Error strings; empty when the ownership boundary holds.
    """
    tm = _headings(tm_text)
    errors = [
        f"artifact-gate: threat-model restates architecture section {h!r}"
        for h in sorted((_headings(arc42_text) & tm) - _ALLOWED_SHARED_HEADINGS)
    ]
    errors.extend(
        f"artifact-gate: structure heading {h!r} belongs to the architecture doc"
        for h in sorted(_STRUCTURE_HEADINGS & tm)
    )
    return errors


def run_artifact_gate(ws: Workspace) -> list[str]:
    """Check a finished run's artifacts for internal consistency.

    Args:
        ws: The finished-run workspace (expects ``report.md`` and finding files).

    Returns:
        Error strings; empty when every check passes. Also writes the audit trail
        ``kb/gates/artifact-gate.json``.
    """
    errors: list[str] = []
    report_md = ws.report_path.read_text() if ws.report_path.exists() else ""
    if not report_md:
        errors.append("artifact-gate: report.md is missing or empty")

    for frag in _BANNED_FRAGMENTS:
        if frag in report_md:
            errors.append(f"artifact-gate: report.md still contains a constant section ({frag!r})")

    for row in _triage_rows(report_md):
        what = row[2] if len(row) > 2 else ""
        if len(what.rstrip("…")) > _TRIAGE_WHAT_MAX:
            errors.append(f"artifact-gate: triage cell exceeds {_TRIAGE_WHAT_MAX} chars: {what!r}")

    findings = read_findings(ws)
    by_id = {f.id: f for f in findings}
    shipping = [f for f in findings if f.status.value in SHIPPING_STATUSES]

    rt_path = ws.reports / "redteam-plan.md"
    rt_text = rt_path.read_text() if rt_path.exists() else ""
    if not rt_text:
        errors.append("artifact-gate: redteam-plan.md is missing — run the red-team phase first")

    for f in shipping:
        if not (ws.findings_dir / f"{f.id}.md").exists():
            errors.append(f"artifact-gate: shipping finding {f.id} has no detail file findings/{f.id}.md")
        has_directive = bool(f.runtime_disposition) or (f.id in rt_text)
        if not has_directive:
            errors.append(f"artifact-gate: shipping finding {f.id} has no red-team directive")

    for row in _triage_rows(report_md):
        fid = row[0] if row else ""
        if fid and fid not in by_id:
            errors.append(f"artifact-gate: triage ID {fid} does not resolve to a finding")

    context_md = ws.kb / "CONTEXT.md"
    if context_md.exists():
        n = _mermaid_node_count(context_md.read_text())
        if n is not None and n > 10:
            errors.append(f"artifact-gate: context diagram has {n} nodes (>10 style cap, ISSUE-022)")

    arc42 = ws.root / "architecture" / "arc42.md"
    tm_doc = ws.root / "threat-model" / "threat-model.md"
    if arc42.exists() and tm_doc.exists():
        errors.extend(check_duplication(arc42.read_text(), tm_doc.read_text()))

    (ws.kb / "gates").mkdir(parents=True, exist_ok=True)
    (ws.kb / "gates" / "artifact-gate.json").write_text(
        json.dumps({"passed": not errors, "errors": errors}, indent=2)
    )
    return errors


def main(argv: list[str] | None = None) -> int:
    """CLI: run the artifact gate on a workspace.

    Args:
        argv: Optional argument vector.

    Returns:
        0 when the gate passes, 1 otherwise.
    """
    import argparse

    parser = argparse.ArgumentParser(prog="sec-overlay-artifact-gate")
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args(argv)
    errors = run_artifact_gate(Workspace(Path(args.workspace)))
    for e in errors:
        print(e)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
