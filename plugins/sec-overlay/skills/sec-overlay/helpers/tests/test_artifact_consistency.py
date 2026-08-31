"""Tests for the terminal artifact-consistency gate (REQ-31)."""

import json
from pathlib import Path

from sec_overlay.artifact_consistency import run_artifact_consistency
from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.state import load_state, save_state
from sec_overlay.workspace import Workspace, write_findings

_REPORT_HEAD = "# sec-overlay Report\n\nConfirmed: 0\nNeeds runtime proof: 1\n\n"


def _ws(tmp_path: Path) -> Workspace:
    ws = Workspace(tmp_path / "wsp")
    ws.ensure()
    return ws


def _ndt(fid="N-1", message="owner check may be advisory"):
    return Finding(
        id=fid,
        rule_id="investigation:authz",
        cls="authz",
        status=FindingStatus.NEEDS_DEPLOYMENT_TESTING,
        severity=Severity.LOW,
        file="a.js",
        line=1,
        risk_score=3,
        message=message,
    )


def _triage(fid: str, what: str, action: str) -> str:
    return (
        "## Triage\n\n"
        "| ID | Risk | What | Location | Status | Next action |\n"
        "|----|------|------|----------|--------|-------------|\n"
        f"| {fid} | 3 | {what} | a.js:1 | needs-runtime | {action} |\n\n"
    )


def _selfscore(ws: Workspace, score) -> None:
    state = load_state(ws)
    state.budget["self_score"] = score
    save_state(ws, state)


def test_missing_report_degrades_to_no_op(tmp_path):
    """A workspace with no report is not a contradiction — the gate stays silent."""
    assert run_artifact_consistency(_ws(tmp_path)) == []


def test_gate_flags_a_detail_link_with_no_file(tmp_path):
    """Check (a): every findings/<id>.md cross-reference must resolve."""
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt()])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 1})
    ws.report_path.write_text(_REPORT_HEAD + "## Detail\n\n- [N-1](findings/N-1.md) — risk 3\n")
    errors = run_artifact_consistency(ws)
    assert any("findings/N-1.md" in e for e in errors)


def test_gate_flags_a_next_action_whose_section_lacks_the_finding(tmp_path):
    """Check (b): 'run redteam-plan directive' must resolve to a real directive."""
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt()])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 1})
    ws.report_path.write_text(
        _REPORT_HEAD + _triage("N-1", "owner check may be advisory", "run redteam-plan directive")
    )
    (ws.reports / "redteam-plan.md").write_text(
        "## Manual test directives\n\n_none_\n\n## Runtime-validation gaps\n\n- `N-1` (authz)\n"
    )
    errors = run_artifact_consistency(ws)
    assert any("N-1" in e and "Manual test directives" in e for e in errors)


def test_gate_passes_when_the_next_action_names_the_right_section(tmp_path):
    """Check (b): the matching artifacts pass."""
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt()])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 1})
    ws.report_path.write_text(
        _REPORT_HEAD + _triage("N-1", "owner check may be advisory", "see redteam-plan gaps")
    )
    (ws.reports / "redteam-plan.md").write_text(
        "## Manual test directives\n\n_none_\n\n## Runtime-validation gaps\n\n- `N-1` (authz)\n"
    )
    assert run_artifact_consistency(ws) == []


def test_gate_flags_a_coverage_claim_the_ledger_denies(tmp_path):
    """Check (c): the report's completeness line must match the ledger."""
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt()])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 1})
    ws.report_path.write_text(
        _REPORT_HEAD + "## Coverage completeness\n\nCompleteness: **complete**\n"
    )
    (ws.kb / "coverage-ledger.json").write_text(json.dumps({"completeness": "partial"}))
    errors = run_artifact_consistency(ws)
    assert any("completeness" in e.lower() for e in errors)


def test_gate_flags_a_null_self_score(tmp_path):
    """Check (d): a report exists but selfscore never landed — N-2."""
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt()])
    ws.report_path.write_text(_REPORT_HEAD)
    errors = run_artifact_consistency(ws)
    assert any("self_score" in e for e in errors)


def test_gate_flags_a_zero_self_score_against_a_reported_finding(tmp_path):
    """Check (d): selfscore says zero needs-runtime, the report renders one."""
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt()])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 0})
    ws.report_path.write_text(_REPORT_HEAD)
    errors = run_artifact_consistency(ws)
    assert any("needs_runtime" in e for e in errors)


def test_gate_flags_a_measured_header_with_an_empty_body(tmp_path):
    """Check (e): a '(measured):' header must be followed by data."""
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt()])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 1})
    ws.report_path.write_text(
        _REPORT_HEAD + "## Run economics\n\n**Tokens by phase** (measured):\n\n## Detail\n"
    )
    errors = run_artifact_consistency(ws)
    assert any("measured" in e for e in errors)


def test_gate_flags_a_title_truncated_mid_word(tmp_path):
    """Check (f): a triage title must not cut its source message inside a word."""
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt(message="owner check may be advisory")])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 1})
    ws.report_path.write_text(
        _REPORT_HEAD + _triage("N-1", "owner check may be advi…", "see redteam-plan gaps")
    )
    errors = run_artifact_consistency(ws)
    assert any("mid-word" in e for e in errors)


def test_gate_writes_its_audit_trail(tmp_path):
    """The gate records its verdict under kb/gates/ like every other gate."""
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt()])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 1})
    ws.report_path.write_text(_REPORT_HEAD)
    run_artifact_consistency(ws)
    payload = json.loads((ws.kb / "gates" / "artifact-consistency.json").read_text())
    assert payload["passed"] is True
    assert payload["errors"] == []


def test_gate_is_skippable_through_scan_options(tmp_path):
    """The lane ships behind a profile flag; a target can opt out."""
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt()])
    ws.report_path.write_text(_REPORT_HEAD + "## Detail\n\n- [N-1](findings/N-1.md) — risk 3\n")
    (ws.kb / "scan-profile.json").write_text(
        json.dumps({"scan_options": {"consistency_gate": False}})
    )
    assert run_artifact_consistency(ws) == []


def test_phase_table_runs_the_gate_before_postflight():
    """The gate is terminal: after artifact-review, before AUDIT COMPLETE."""
    from sec_overlay.phases import PHASE_TABLE

    names = [p.name for p in PHASE_TABLE]
    assert names.index("artifact-consistency") > names.index("artifact-review")
    assert names.index("artifact-consistency") < names.index("postflight")
