"""REQ-13: every receipt records the finding count the phase actually saw."""

from __future__ import annotations

import json
import subprocess

from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.run import advance
from sec_overlay.workspace import Workspace, finding_counts, write_findings


def _fake_runner(stdout: str = ""):
    def run(cmd, *a, **k):
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")

    return run


def _four_findings() -> list[Finding]:
    """Two shipping findings and two that are not, with harness-shaped ids."""
    statuses = (
        FindingStatus.CONFIRMED,
        FindingStatus.FIXED,
        FindingStatus.CANDIDATE,
        FindingStatus.REJECTED,
    )
    return [
        Finding(
            id=f"C-{i:04d}",
            rule_id="semgrep:test.rule",
            cls="ssrf",
            status=status,
            severity=Severity.LOW,
            file="src/app.py",
            line=i,
            message="test finding",
            evidence_sources=["semgrep:test.rule"],
        )
        for i, status in enumerate(statuses, start=1)
    ]


def test_finding_counts_partitions_shipping_from_the_rest(tmp_path):
    ws = Workspace(root=tmp_path / "ws")
    ws.ensure()
    write_findings(ws, _four_findings())
    assert finding_counts(ws) == {"findings": 4, "findings_in": 4, "findings_out": 2}


def test_advance_receipt_counts_four_findings_not_zero(tmp_path):
    """The old glob was ``F-*.json``; every real finding id starts ``C-`` or ``<CLASS>-``."""
    ws = Workspace(root=tmp_path / "ws")
    ws.ensure()
    write_findings(ws, _four_findings())
    path = advance(str(tmp_path), "dedupe", workspace=ws.root, runner=_fake_runner())
    counts = json.loads(path.read_text())["counts"]
    assert counts["findings"] == 4
    assert counts["findings_in"] == 4
    assert counts["findings_out"] == 2


def test_gate_receipts_carry_finding_counts(tmp_path):
    """REQ-23, folded into REQ-13: a gate receipt records counts, not only pass/fail."""
    from sec_overlay.driver import _write_gate

    ws = Workspace(root=tmp_path / "ws")
    ws.ensure()
    write_findings(ws, _four_findings())
    _write_gate(ws, "findings-gate", [], [])
    gate = json.loads((ws.kb / "gates" / "findings-gate.json").read_text())
    assert gate["passed"] is True
    assert gate["findings_in"] == 4
    assert gate["findings_out"] == 2
