"""Tests for the findings validation gate."""

import json

from sec_overlay.findings_gate import validate_citations, validate_findings
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


def _shipping(fid: str, file: str, line: int) -> Finding:
    return Finding(
        id=fid, rule_id="r", cls="authz", status=FindingStatus.CONFIRMED,
        severity=Severity.MEDIUM, file=file, line=line, message="m",
        evidence_sources=["semgrep:r"],
    )


def test_unresolved_citation_rejected(tmp_path):
    root = tmp_path / "target"
    root.mkdir()
    (root / "app.py").write_text("import os\nx = 1\n")
    ws = Workspace(tmp_path / "ws")
    write_findings(ws, [_shipping("F-1", "app.py", 999)])  # line 999 does not exist
    errs = validate_citations(ws, root)
    assert any("F-1" in e for e in errs)


def test_resolvable_line_one_survives(tmp_path):
    root = tmp_path / "target"
    root.mkdir()
    (root / "app.py").write_text("import os\n")  # line 1 is real code
    ws = Workspace(tmp_path / "ws")
    write_findings(ws, [_shipping("F-2", "app.py", 1)])
    assert validate_citations(ws, root) == []


def test_placeholder_line_one_unresolved_rejected(tmp_path):
    root = tmp_path / "target"
    root.mkdir()  # no app.py at all → line 1 does not resolve
    ws = Workspace(tmp_path / "ws")
    write_findings(ws, [_shipping("F-3", "app.py", 1)])
    assert any("F-3" in e for e in validate_citations(ws, root))


def test_candidate_not_gated(tmp_path):
    root = tmp_path / "target"
    root.mkdir()
    ws = Workspace(tmp_path / "ws")
    f = _shipping("F-4", "missing.py", 1)
    f.status = FindingStatus.CANDIDATE
    write_findings(ws, [f])
    assert validate_citations(ws, root) == []  # only shipping statuses gated


def test_control_finding_placeholder_anchor_rejected(tmp_path):
    from sec_overlay.context import Context, ContextItem, control_findings

    root = tmp_path / "target"
    root.mkdir()  # no doc-cited file exists → bare-path anchor resolves to line 1, unresolved
    ws = Workspace(tmp_path / "ws")
    ctx = Context(items=[ContextItem(
        kind="claimed_control", text="auth required", cls="authz",
        where="docs/SECURITY.md", verify_status="MISSING")])
    cf = control_findings(ctx)
    for f in cf:
        f.status = FindingStatus.CONFIRMED  # force shipping status to exercise the gate
    write_findings(ws, cf)
    assert validate_citations(ws, root)  # non-empty: the placeholder anchor is rejected
