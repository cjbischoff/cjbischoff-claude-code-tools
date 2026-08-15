"""Tests for the findings validation gate."""

import json

from sec_overlay.findings_gate import validate_findings
from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.workspace import Workspace, write_findings


def _good():
    return Finding(id="F-0002", rule_id="r", cls="sqli", status=FindingStatus.RAW,
                   severity=Severity.HIGH, file="app.py", line=18, message="m",
                   dataflow=["a -> b"], evidence="e")


def test_validate_findings_accepts_good(tmp_path):
    ws = Workspace(tmp_path / "workspace"); ws.ensure()
    write_findings(ws, [_good()])
    assert validate_findings(ws) == []


def test_validate_findings_flags_bad_line_and_file(tmp_path):
    ws = Workspace(tmp_path / "workspace"); ws.ensure()
    bad = _good().to_dict(); bad["line"] = 0; bad["file"] = ""
    (ws.findings_dir / "F-0002.json").write_text(json.dumps(bad))
    errs = validate_findings(ws)
    assert any("F-0002" in e for e in errs)


def test_validate_findings_flags_unparseable(tmp_path):
    ws = Workspace(tmp_path / "workspace"); ws.ensure()
    (ws.findings_dir / "F-9999.json").write_text('{"id": "F-9999"}')  # missing required fields
    errs = validate_findings(ws)
    assert any("F-9999" in e for e in errs)


def test_golden_raw_finding_valid(tmp_path):
    from pathlib import Path

    golden = Path(__file__).parent.parent / "fixtures" / "golden_raw_finding.json"
    ws = Workspace(tmp_path / "workspace"); ws.ensure()
    (ws.findings_dir / "F-0002.json").write_text(golden.read_text())
    assert validate_findings(ws) == []


def test_validate_flags_raw_with_duplicate_of(tmp_path):
    ws = Workspace(tmp_path / "workspace"); ws.ensure()
    bad = _good(); bad.duplicate_of = "C-0089"  # raw + duplicate_of is inconsistent
    write_findings(ws, [bad])
    errs = validate_findings(ws)
    assert any("duplicate_of" in e for e in errs)


def test_validate_allows_duplicate_status_with_duplicate_of(tmp_path):
    ws = Workspace(tmp_path / "workspace"); ws.ensure()
    ok = _good(); ok.status = FindingStatus.DUPLICATE; ok.duplicate_of = "C-0089"
    write_findings(ws, [ok])
    assert validate_findings(ws) == []


def test_confirmed_requires_tool_receipt(tmp_path):
    ws = Workspace(tmp_path / "workspace"); ws.ensure()
    f = _good()
    f.status = FindingStatus.CONFIRMED
    f.evidence_sources = ["llm-claimed:reasoning", "read:sanity"]  # no mechanical receipt
    write_findings(ws, [f])
    errs = validate_findings(ws)
    assert any("tool receipt" in e for e in errs)


def test_confirmed_with_ripgrep_only_receipt_is_rejected(tmp_path):
    # Tier-2 (ripgrep/ast-grep/structural-index/tree-sitter) locates code but does not
    # prove reachability; a Tier-1 receipt is required to reach confirmed/fixed.
    ws = Workspace(tmp_path / "workspace"); ws.ensure()
    f = _good()
    f.status = FindingStatus.CONFIRMED
    f.evidence_sources = ["ripgrep:unescaped {{x}} @ a.liquid:5", "llm-claimed:no-autoescape"]
    write_findings(ws, [f])
    errs = validate_findings(ws)
    assert any("Tier-1" in e for e in errs)


def test_raw_without_receipt_still_allowed(tmp_path):
    # the receipt gate applies at confirmed/fixed, not raw (raw is pre-validation)
    ws = Workspace(tmp_path / "workspace"); ws.ensure()
    f = _good()  # status RAW, dataflow set
    f.evidence_sources = ["llm-claimed:reasoning"]
    write_findings(ws, [f])
    assert validate_findings(ws) == []


def test_gate_accepts_needs_deployment_without_receipt(tmp_path):
    ws = Workspace(tmp_path / "workspace"); ws.ensure()
    f = _good(); f.status = FindingStatus.NEEDS_DEPLOYMENT_TESTING
    f.evidence_sources = ["llm-claimed:reasoning"]   # no mechanical receipt is OK here
    write_findings(ws, [f])
    assert validate_findings(ws) == []


def test_schema_violation_is_flagged_with_finding_id(tmp_path):
    ws = Workspace(tmp_path / "workspace"); ws.ensure()
    bad = _good().to_dict()
    bad["severity"] = "not-a-real-severity"
    (ws.findings_dir / f"{bad['id']}.json").write_text(json.dumps(bad))
    errs = validate_findings(ws)
    assert any(bad["id"] in e and "severity" in e for e in errs)


def test_schema_valid_finding_produces_no_schema_errors(tmp_path):
    ws = Workspace(tmp_path / "workspace"); ws.ensure()
    good = _good().to_dict()
    (ws.findings_dir / f"{good['id']}.json").write_text(json.dumps(good))
    errs = validate_findings(ws)
    assert errs == []


def test_validate_findings_records_stage(tmp_path):
    from sec_overlay.state import load_state

    ws = Workspace(tmp_path / "workspace"); ws.ensure()
    write_findings(ws, [_good()])
    validate_findings(ws)
    assert "findings-gate" in load_state(ws).stages


def _write_raw(ws: Workspace, fid: str, **over) -> None:
    data = {"id": fid, "rule_id": "r", "cls": "injection", "status": "confirmed",
            "severity": "high", "file": "a.py", "line": 3, "message": "m",
            "dataflow": [], "evidence_sources": ["ripgrep"]}
    data.update(over)
    (ws.findings_dir / f"{fid}.json").write_text(json.dumps(data))


def _ws_raw(tmp_path):
    ws = Workspace(tmp_path / "workspace")
    ws.findings_dir.mkdir(parents=True, exist_ok=True)
    (ws.root / "a.py").write_text("x = 1\ny = 2\nz = 3\n")
    return ws


def test_tier2_only_confirmed_is_rejected(tmp_path):
    ws = _ws_raw(tmp_path)
    _write_raw(ws, "F-1", evidence_sources=["ripgrep", "structural-index"])
    errors = validate_findings(ws)
    assert any("F-1" in e and "confirm" in e.lower() for e in errors)


def test_tier1_confirmed_passes(tmp_path):
    ws = _ws_raw(tmp_path)
    _write_raw(ws, "F-2", evidence_sources=["codeql:dataflow"])
    errors = validate_findings(ws)
    assert not any("F-2" in e for e in errors)


def test_out_of_vocab_disposition_rejected(tmp_path):
    ws = _ws_raw(tmp_path)
    _write_raw(ws, "F-3", evidence_sources=["codeql:dataflow"],
               runtime_disposition="neither")
    errors = validate_findings(ws)
    assert any("F-3" in e and "runtime_disposition" in e for e in errors)


def test_receipt_tier_is_stamped(tmp_path):
    ws = _ws_raw(tmp_path)
    _write_raw(ws, "F-4", evidence_sources=["codeql:dataflow"])
    validate_findings(ws)
    stamped = json.loads((ws.findings_dir / "F-4.json").read_text())
    assert stamped["receipt_tier"] == 1
