"""Tests for the terminal artifact-consistency gate (REQ-31)."""

import json
from pathlib import Path

from sec_overlay.artifact_consistency import run_artifact_consistency
from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.report import triage_what, write_report
from sec_overlay.selfscore import write_self_score
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


def test_gate_flags_any_self_score_mismatch_against_the_report(tmp_path):
    """Check (d), reversed by REQ-54: the counts must be equal, not bounded.

    The old check tolerated a report count below the score, because the report
    collapsed clusters and the score did not. REQ-54 collapses both sides, so
    a difference in either direction is a contradiction. Uses a modern score
    (``needs_runtime_collapsed`` present) — a legacy score without that key
    degrades to a pass instead (see the P4-15 test below).
    """
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt()])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 0, "needs_runtime_collapsed": 0})
    ws.report_path.write_text(_REPORT_HEAD)
    errors = run_artifact_consistency(ws)
    assert any("needs_runtime" in e for e in errors)
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 2, "needs_runtime_collapsed": 2})
    errors = run_artifact_consistency(ws)
    assert any("needs_runtime" in e for e in errors)


def test_gate_degrades_a_legacy_score_missing_the_collapsed_key(tmp_path):
    """Check (d): a legacy score with no needs_runtime_collapsed key degrades to a pass.

    P4-15. A state.json written before REQ-54 (a resumed campaign, a
    standalone module run, an upgraded plugin) supplies only the uncollapsed
    ``needs_runtime`` count. A collapsed cluster then skews the report's count
    against it with no way to tell drift from a real contradiction, so the
    clause must not halt — mirroring check (h)'s legacy degrade.
    """
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt()])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 2})
    ws.report_path.write_text(_REPORT_HEAD)  # states 1, legacy score says 2
    assert run_artifact_consistency(ws) == []


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


def test_gate_flags_a_hand_edited_truncated_title(tmp_path):
    """REQ-68: a truncated cell that is not a prefix of its message is a stale report."""
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt(message="owner check may be advisory")])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 1})
    ws.report_path.write_text(
        _REPORT_HEAD + _triage("N-1", "something nobody rendered…", "see redteam-plan gaps")
    )

    errors = run_artifact_consistency(ws)

    assert any("not a prefix" in e for e in errors), errors


def test_gate_accepts_a_title_truncated_at_a_word_boundary(tmp_path):
    """REQ-68: the renderer's own word-boundary cut is not a contradiction."""
    ws = _ws(tmp_path)
    long_message = "the owner check is advisory " * 4
    write_findings(ws, [_ndt(message=long_message)])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 1})
    ws.report_path.write_text(
        _REPORT_HEAD
        + _triage("N-1", triage_what(_ndt(message=long_message)), "see redteam-plan gaps")
    )

    assert not any("N-1" in e for e in run_artifact_consistency(ws))


def test_gate_accepts_a_single_long_word_cut_mid_word(tmp_path):
    """REQ-68: _short_title's no-space fallback cuts inside the only word — allowed."""
    ws = _ws(tmp_path)
    word = "A" * 90
    write_findings(ws, [_ndt(message=word)])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 1})
    ws.report_path.write_text(
        _REPORT_HEAD + _triage("N-1", word[:72] + "…", "see redteam-plan gaps")
    )

    assert not any("N-1" in e for e in run_artifact_consistency(ws))


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


def _external(fid="X-1"):
    return Finding(
        id=fid,
        rule_id="investigation:ssrf",
        cls="ssrf",
        status=FindingStatus.NEEDS_DEPLOYMENT_TESTING,
        severity=Severity.MEDIUM,
        file="b.js",
        line=2,
        risk_score=4,
        message="sink crosses into an un-ingested package",
        completeness_tier="external-unverifiable",
    )


def test_gate_flags_a_stated_ndt_count_below_the_rendered_count(tmp_path):
    """Check (g): the report renders two needs-runtime findings and states one."""
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt(), _external()])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 2})
    ws.report_path.write_text(
        "# sec-overlay Report\n\nConfirmed: 0\nNeeds runtime proof: 1\n\n"
        + _triage("N-1", "owner check may be advisory", "see redteam-plan gaps")
        + "## Leads — pending external-dependency verification\n\n"
        "### X-1 — ssrf — Medium · needs runtime proof\n\n"
    )
    errors = run_artifact_consistency(ws)
    assert any("needs-runtime" in e and "renders" in e for e in errors)


def test_gate_flags_a_sarif_result_the_report_never_renders(tmp_path):
    """Check (g): a finding reaches SARIF and no report section."""
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt(), _external()])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 2})
    ws.report_path.write_text(
        "# sec-overlay Report\n\nConfirmed: 0\nNeeds runtime proof: 1\n\n"
        + _triage("N-1", "owner check may be advisory", "see redteam-plan gaps")
    )
    ws.sarif_path.parent.mkdir(parents=True, exist_ok=True)
    ws.sarif_path.write_text(
        json.dumps({"runs": [{"results": [{"ruleId": "r"}, {"ruleId": "r"}]}]})
    )
    errors = run_artifact_consistency(ws)
    assert any("SARIF" in e for e in errors)


def test_gate_passes_when_the_report_states_the_external_split(tmp_path):
    """Check (g): a report that names both buckets reconciles against SARIF."""
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt(), _external()])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 2})
    ws.report_path.write_text(
        "# sec-overlay Report\n\nConfirmed: 0\nNeeds runtime proof: 2\n"
        "Leads pending external verification: 1\n\n"
        + _triage("N-1", "owner check may be advisory", "see redteam-plan gaps")
        + "## Leads — pending external-dependency verification\n\n"
        "### X-1 — ssrf — Medium · needs runtime proof\n\n"
    )
    ws.sarif_path.parent.mkdir(parents=True, exist_ok=True)
    ws.sarif_path.write_text(
        json.dumps({"runs": [{"results": [{"ruleId": "r"}, {"ruleId": "r"}]}]})
    )
    assert run_artifact_consistency(ws) == []


def test_confirmed_only_report_does_not_halt_the_gate(tmp_path):
    """Check (g) part two: a correct confirmed-only run must not trip the gate.

    P4-15. write_report(confirmed_only=True) writes SARIF from the reportable
    set only but still renders needs-runtime rows into the markdown, so a
    naive count comparison halts a run that did nothing wrong. Exercises the
    real write_report + write_self_score pipeline end to end.
    """
    ws = _ws(tmp_path)
    write_findings(
        ws,
        [
            Finding(
                id="F-1",
                rule_id="r",
                cls="authz",
                status=FindingStatus.CONFIRMED,
                severity=Severity.HIGH,
                file="a.py",
                line=1,
                message="m",
                risk_score=7,
            ),
            _ndt("N-2"),
        ],
    )
    write_report(ws, confirmed_only=True)
    write_self_score(ws)
    assert run_artifact_consistency(ws) == []


def test_gate_flags_a_triage_heading_with_no_rows_against_a_stated_count(tmp_path):
    """Check (g): a `## Triage` heading with no data rows is a render bug, not a missing artifact."""
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt()])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 1})
    ws.report_path.write_text(
        "# sec-overlay Report\n\nConfirmed: 0\nNeeds runtime proof: 1\n\n"
        "## Triage\n\n"
        "| ID | Risk | What | Location | Status | Next action |\n"
        "|----|------|------|----------|--------|-------------|\n\n"
    )
    errors = run_artifact_consistency(ws)
    assert any("needs-runtime" in e and "renders" in e for e in errors)


def test_gate_flags_a_self_score_that_loses_findings(tmp_path):
    """Check (h): the score's buckets must cover every finding on disk."""
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt(), _ndt("N-2")])
    _selfscore(
        ws,
        {
            "confirmed": 0,
            "needs_runtime": 2,
            "duplicate": 0,
            "total": 2,
            "by_status": {"needs-deployment-testing": 1},
        },
    )
    ws.report_path.write_text(
        "# sec-overlay Report\n\nConfirmed: 0\nNeeds runtime proof: 2\n\n"
        + _triage("N-1", "owner check may be advisory", "see redteam-plan gaps")
        + "### N-2 — authz — Low · needs runtime proof\n\n"
    )
    errors = run_artifact_consistency(ws)
    assert any("by_status" in e for e in errors)
