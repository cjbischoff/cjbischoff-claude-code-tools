import json

from sec_overlay.artifact_gate import check_duplication, run_artifact_gate
from sec_overlay.workspace import Workspace


def _finding(fid, status="confirmed", disp="static-settled"):
    return {"id": fid, "rule_id": "r", "cls": "sqli", "status": status, "severity": "high",
            "file": "a.py", "line": 1, "message": "m", "impact": "x",
            "runtime_disposition": disp, "evidence_sources": ["semgrep:sqli"]}


def _good_ws(tmp_path):
    ws = Workspace(tmp_path); ws.ensure()
    (ws.findings_dir / "F-1.json").write_text(json.dumps(_finding("F-1")))
    (ws.findings_dir / "F-1.md").write_text("detail\n")
    ws.report_path.write_text(
        "# sec-overlay Report\n\n## Triage\n"
        "| ID | Risk | What | Location | Status | Next action |\n"
        "|----|------|------|----------|--------|-------------|\n"
        "| F-1 | 9 | short clean title | a.py:1 | confirmed | fix |\n\n"
        "## Detail\n- [F-1](findings/F-1.md) — risk 9 — confirmed — t\n")
    (ws.reports / "redteam-plan.md").write_text("directive for F-1\n")
    return ws


def test_clean_artifacts_pass(tmp_path):
    assert run_artifact_gate(_good_ws(tmp_path)) == []


def test_constant_section_fails(tmp_path):
    ws = _good_ws(tmp_path)
    ws.report_path.write_text(ws.report_path.read_text()
        + "\n**6. Confirmed Attack Scenario** (theoretical — not dynamically confirmed)\n")
    assert any("constant" in e.lower() or "attack scenario" in e.lower()
               for e in run_artifact_gate(ws))


def test_missing_detail_file_fails(tmp_path):
    ws = _good_ws(tmp_path)
    (ws.findings_dir / "F-1.md").unlink()
    assert any("F-1" in e and "detail" in e.lower() for e in run_artifact_gate(ws))


def test_missing_redteam_directive_fails(tmp_path):
    ws = _good_ws(tmp_path)
    (ws.findings_dir / "F-1.json").write_text(json.dumps(_finding("F-1", disp=None)))
    (ws.reports / "redteam-plan.md").write_text("nothing here\n")
    assert any("F-1" in e and "directive" in e.lower() for e in run_artifact_gate(ws))


def test_triage_id_without_finding_fails(tmp_path):
    ws = _good_ws(tmp_path)
    md = ws.report_path.read_text().replace("| F-1 |", "| F-99 |")
    ws.report_path.write_text(md)
    assert any("F-99" in e for e in run_artifact_gate(ws))


def test_writes_audit_trail(tmp_path):
    ws = _good_ws(tmp_path)
    run_artifact_gate(ws)
    assert (ws.kb / "gates" / "artifact-gate.json").exists()


def test_duplicated_heading_fails():
    arc = "## Building Block View\n\nContent.\n"
    tm = "## Building Block View\n\nRestated content.\n"
    errs = check_duplication(arc, tm)
    assert any("building block view" in e.lower() for e in errs)


def test_banned_structure_heading_in_threat_model_fails():
    errs = check_duplication("## Something\n", "## Deployment View\n")
    assert any("deployment view" in e.lower() for e in errs)


def test_distinct_headings_pass():
    arc = "## Building Block View\n## Runtime View\n"
    tm = "## Trust Boundaries\n## Findings\n## Glossary\n"
    assert check_duplication(arc, tm) == []


def test_gate_skips_when_trees_absent(tmp_path):
    ws = _good_ws(tmp_path)
    assert run_artifact_gate(ws) == []
