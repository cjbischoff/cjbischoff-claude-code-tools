"""Terminal artifact-consistency gate (REQ-31).

Runs after artifact-review and before AUDIT COMPLETE. It reconciles a finished
run's own artifacts against each other: every cross-reference resolves, every
next-action names a section that contains its finding, the coverage claim
matches the ledger, the self-score does not contradict the report, no
"(measured)" header sits above an empty body, and no rendered title cuts its
source message inside a word.

It never judges a finding and never deletes one. A missing artifact is not a
contradiction — an incomplete workspace degrades to a silent pass.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from sec_overlay.models import FindingStatus
from sec_overlay.report import triage_what
from sec_overlay.state import load_state
from sec_overlay.workspace import Workspace, read_findings

_DETAIL_LINK = re.compile(r"\]\(findings/([^)]+)\)")
_SECTION_ID = re.compile(r"^### (\S+) — ", re.MULTILINE)

# Task 1 emits exactly these phrases; each names one redteam-plan heading.
_ACTION_SECTIONS = {
    "run redteam-plan directive": "## Manual test directives",
    "see redteam-plan preconditions": "## Unrunnable preconditions",
    "see redteam-plan gaps": "## Runtime-validation gaps",
}

# Statuses write_report(confirmed_only=True) puts into SARIF (report.py's _REPORTABLE).
_SARIF_REPORTABLE = {FindingStatus.CONFIRMED, FindingStatus.FIXED}


def _section(md: str, heading: str) -> str:
    """Return the body under the first heading that starts with ``heading``."""
    out: list[str] = []
    inside = False
    for line in md.splitlines():
        if line.startswith("## "):
            if inside:
                break
            inside = line.startswith(heading)
            continue
        if inside:
            out.append(line)
    return "\n".join(out)


def _triage_rows(md: str) -> list[list[str]]:
    """Return the report's triage data rows as lists of stripped cells."""
    rows: list[list[str]] = []
    for line in _section(md, "## Triage").splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells[0] == "ID" or set("".join(cells)) <= set("-| "):
            continue
        rows.append(cells)
    return rows


def _enabled(ws: Workspace) -> bool:
    """True unless ``scan_options.consistency_gate`` is set to false."""
    path = ws.kb / "scan-profile.json"
    if not path.exists():
        return True
    try:
        options = json.loads(path.read_text()).get("scan_options") or {}
    except (json.JSONDecodeError, AttributeError):
        return True
    return options.get("consistency_gate", True) is not False


def _check_cross_references(ws: Workspace, report_md: str) -> list[str]:
    """Check (a): every ``findings/<id>.md`` link resolves to a file on disk."""
    return [
        f"artifact-consistency: report links findings/{name} but the file does not exist"
        for name in sorted(set(_DETAIL_LINK.findall(report_md)))
        if not (ws.findings_dir / name).exists()
    ]


def _check_next_actions(ws: Workspace, report_md: str) -> list[str]:
    """Check (b): every next-action names a plan section that holds the finding."""
    plan = ws.reports / "redteam-plan.md"
    if not plan.exists():
        return []
    plan_md = plan.read_text()
    errors: list[str] = []
    for row in _triage_rows(report_md):
        heading = _ACTION_SECTIONS.get(row[-1])
        if heading and row[0] not in _section(plan_md, heading):
            errors.append(
                f"artifact-consistency: next action for {row[0]} names "
                f"{heading!r}, which does not contain it"
            )
    return errors


def _check_coverage_claim(ws: Workspace, report_md: str) -> list[str]:
    """Check (c): the rendered completeness matches the coverage ledger."""
    path = ws.kb / "coverage-ledger.json"
    match = re.search(r"^Completeness: \*\*(.+?)\*\*$", report_md, re.MULTILINE)
    if not path.exists() or match is None:
        return []
    claimed = match.group(1)
    actual = json.loads(path.read_text()).get("completeness", "unknown")
    if claimed != actual:
        return [
            (
                f"artifact-consistency: report claims completeness {claimed!r} "
                f"but the ledger records {actual!r}"
            )
        ]
    return []


def _check_self_score(ws: Workspace, report_md: str) -> list[str]:
    """Check (d): the self-score does not contradict the report's own counts.

    Both sides collapse clusters (REQ-54), so the two counts must be equal.
    Runs only when the score carries ``needs_runtime_collapsed``; a legacy
    score written before REQ-54 carries only the uncollapsed count and
    degrades to a pass, mirroring check (h). A missing score is a
    contradiction; a report with no count line is not.
    """
    score = load_state(ws).budget.get("self_score")
    if not isinstance(score, dict):
        return ["artifact-consistency: report exists but state.budget.self_score is missing"]
    scored = score.get("needs_runtime_collapsed")
    if not isinstance(scored, int):
        return []
    match = re.search(r"^Needs runtime proof: (\d+)$", report_md, re.MULTILINE)
    if match is None:
        return []
    reported = int(match.group(1))
    if reported != scored:
        return [
            (
                f"artifact-consistency: report shows {reported} needs-runtime "
                f"finding(s) but self_score.needs_runtime is {scored}"
            )
        ]
    return []


def _check_self_score_partition(ws: Workspace) -> list[str]:
    """Check (h): the self-score's buckets cover every finding on disk.

    Runs only when the score carries ``total`` and ``by_status``. A score
    written before REQ-54 carries neither and degrades to a pass.

    Args:
        ws: The finished-run workspace.

    Returns:
        Contradiction strings; empty when the buckets partition the population.
    """
    score = load_state(ws).budget.get("self_score")
    if not isinstance(score, dict):
        return []
    by_status = score.get("by_status")
    total = score.get("total")
    if not isinstance(by_status, dict) or not isinstance(total, int):
        return []
    errors: list[str] = []
    on_disk = len(read_findings(ws))
    if total != on_disk:
        errors.append(
            f"artifact-consistency: self_score.total is {total} but "
            f"{on_disk} finding(s) are on disk"
        )
    bucketed = sum(by_status.values())
    if bucketed != total:
        errors.append(
            f"artifact-consistency: self_score.by_status covers {bucketed} "
            f"finding(s) against a total of {total}"
        )
    return errors


def _check_measured_sections(report_md: str) -> list[str]:
    """Check (e): no "(measured)" header stands above an empty body."""
    lines = report_md.splitlines()
    errors: list[str] = []
    for i, line in enumerate(lines):
        if not line.rstrip().endswith("(measured):"):
            continue
        body = next((n for n in lines[i + 1 :] if n.strip()), "")
        if not body.startswith("- "):
            errors.append(
                f"artifact-consistency: measured section {line.strip()!r} has an empty body"
            )
    return errors


def _check_truncated_titles(ws: Workspace, report_md: str) -> list[str]:
    """Check (f): a truncated triage title ends on a word boundary of its source."""
    by_id = {f.id: f for f in read_findings(ws)}
    errors: list[str] = []
    for row in _triage_rows(report_md):
        what = row[2] if len(row) > 2 else ""
        finding = by_id.get(row[0])
        if not what.endswith("…") or finding is None:
            continue
        if what != triage_what(finding):
            errors.append(
                f"artifact-consistency: triage title for {row[0]} is truncated mid-word: {what!r}"
            )
    return errors


def _rendered_ids(ws: Workspace, report_md: str) -> set[str]:
    """Return the finding ids the report renders in any section.

    A finding id reaches the reader through a triage row, a ``## Detail`` link,
    or a ``### <id> — `` section heading. Ids not on disk are dropped, so a
    heading that names something other than a finding cannot inflate the count.

    Args:
        ws: The finished-run workspace.
        report_md: The rendered report text.

    Returns:
        The set of rendered finding ids.
    """
    known = {f.id for f in read_findings(ws)}
    ids = {row[0] for row in _triage_rows(report_md)}
    ids |= {link.removesuffix(".md") for link in _DETAIL_LINK.findall(report_md)}
    ids |= set(_SECTION_ID.findall(report_md))
    return ids & known


def _check_sarif_population(ws: Workspace, report_md: str) -> list[str]:
    """Check (g): SARIF and the report describe one population.

    Part one: the stated ``Needs runtime proof`` count equals the needs-runtime
    findings the report renders. Part two: the SARIF result count equals the
    total finding count the report renders — or, when
    ``state.budget.sarif_confirmed_only`` is set, the confirmed/fixed subset of
    it, matching what ``write_report(confirmed_only=True)`` actually wrote. A
    missing SARIF file degrades part two to a pass.

    Args:
        ws: The finished-run workspace.
        report_md: The rendered report text.

    Returns:
        Contradiction strings; empty when both counts agree.
    """
    rendered = _rendered_ids(ws, report_md)
    by_id = {f.id: f for f in read_findings(ws)}
    errors: list[str] = []
    has_render_surface = "## Triage" in report_md
    match = re.search(r"^Needs runtime proof: (\d+)$", report_md, re.MULTILINE)
    if match is not None and has_render_surface:
        stated = int(match.group(1))
        shown = sum(
            1
            for fid in rendered
            if by_id[fid].status is FindingStatus.NEEDS_DEPLOYMENT_TESTING
        )
        if stated != shown:
            errors.append(
                f"artifact-consistency: report states {stated} needs-runtime "
                f"finding(s) but renders {shown}"
            )
    if ws.sarif_path.exists():
        doc = json.loads(ws.sarif_path.read_text())
        runs = doc.get("runs") or [{}]
        results = runs[0].get("results") or []
        if load_state(ws).budget.get("sarif_confirmed_only"):
            population = {fid for fid in rendered if by_id[fid].status in _SARIF_REPORTABLE}
        else:
            population = rendered
        if len(results) != len(population):
            errors.append(
                f"artifact-consistency: SARIF holds {len(results)} result(s) "
                f"but the report renders {len(population)} finding(s)"
            )
    return errors


def run_artifact_consistency(ws: Workspace) -> list[str]:
    """Reconcile a finished run's artifacts against each other.

    Args:
        ws: The finished-run workspace.

    Returns:
        Contradiction strings; empty when the artifacts agree, when the run
        opted out through ``scan_options.consistency_gate``, or when no report
        was rendered. Also writes ``kb/gates/artifact-consistency.json``.
    """
    if not ws.report_path.exists() or not _enabled(ws):
        return []
    report_md = ws.report_path.read_text()
    errors = (
        _check_cross_references(ws, report_md)
        + _check_next_actions(ws, report_md)
        + _check_coverage_claim(ws, report_md)
        + _check_self_score(ws, report_md)
        + _check_measured_sections(report_md)
        + _check_truncated_titles(ws, report_md)
        + _check_sarif_population(ws, report_md)
        + _check_self_score_partition(ws)
    )
    (ws.kb / "gates").mkdir(parents=True, exist_ok=True)
    (ws.kb / "gates" / "artifact-consistency.json").write_text(
        json.dumps({"passed": not errors, "errors": errors}, indent=2)
    )
    return errors


def main(argv: list[str] | None = None) -> int:
    """CLI: run the artifact-consistency gate on a workspace.

    Args:
        argv: Optional argument vector.

    Returns:
        0 when the artifacts agree, 1 otherwise.
    """
    import argparse

    parser = argparse.ArgumentParser(prog="sec-overlay-artifact-consistency")
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args(argv)
    errors = run_artifact_consistency(Workspace(Path(args.workspace)))
    for e in errors:
        print(e)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
