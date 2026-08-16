import json

from sec_overlay.artifact_gate import run_artifact_gate
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
