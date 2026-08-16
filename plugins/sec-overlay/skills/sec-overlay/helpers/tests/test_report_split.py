import json

from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.report import write_report
from sec_overlay.workspace import Workspace


def _conf(fid, risk):
    return Finding(
        id=fid,
        rule_id="r",
        cls="sqli",
        status=FindingStatus.CONFIRMED,
        severity=Severity.HIGH,
        file="a.py",
        line=1,
        message=f"msg {fid}",
        impact="db read",
        risk_score=risk,
        evidence_sources=["semgrep:sqli"],
    )


def _seed(ws, findings):
    ws.ensure()
    for f in findings:
        (ws.findings_dir / f"{f.id}.json").write_text(json.dumps(f.to_dict()))


def test_write_report_creates_per_finding_detail_files(tmp_path):
    ws = Workspace(tmp_path)
    _seed(ws, [_conf("F-1", 9), _conf("F-2", 5)])
    write_report(ws)
    assert (ws.findings_dir / "F-1.md").exists()
    assert (ws.findings_dir / "F-2.md").exists()


def test_short_report_links_details_and_omits_full_body(tmp_path):
    ws = Workspace(tmp_path)
    _seed(ws, [_conf("F-1", 9)])
    write_report(ws)
    md = ws.report_path.read_text()
    assert "findings/F-1.md" in md
    assert "## Triage" in md
    assert "**4. Impact.**" not in md


def test_body_is_risk_ordered(tmp_path):
    ws = Workspace(tmp_path)
    _seed(ws, [_conf("F-lo", 3), _conf("F-hi", 9)])
    write_report(ws)
    md = ws.report_path.read_text()
    assert md.index("F-hi") < md.index("F-lo")
