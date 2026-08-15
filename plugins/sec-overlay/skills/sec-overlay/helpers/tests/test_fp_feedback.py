import re

from sec_overlay.fp_feedback import render_fp_feedback
from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.workspace import Workspace, write_findings


def _rej(fid, msg, reason, line=3):
    f = Finding(id=fid, rule_id="r", cls="ssrf", status=FindingStatus.REJECTED,
                severity=Severity.MEDIUM, file="a.py", line=line, message=msg)
    f.history.append({"event": "validate:rejected", "reason": reason})
    return f


def test_render_fp_feedback_lists_rejected_reasons(tmp_path):
    ws = Workspace(root=tmp_path / "ws"); ws.ensure()
    write_findings(ws, [_rej("F-1", "url built from const", "destination not attacker-controlled")])
    block = render_fp_feedback(ws)
    assert "ssrf" in block
    assert "destination not attacker-controlled" in block
    assert "<untrusted" in block           # envelope-wrapped


def test_render_fp_feedback_empty_when_no_rejects(tmp_path):
    ws = Workspace(root=tmp_path / "ws"); ws.ensure()
    write_findings(ws, [])
    assert render_fp_feedback(ws) == ""


def test_render_fp_feedback_honors_cap(tmp_path):
    ws = Workspace(root=tmp_path / "ws"); ws.ensure()
    write_findings(ws, [_rej(f"F-{i}", f"m{i}", f"reason {i}", line=i) for i in range(60)])
    block = render_fp_feedback(ws, cap=5)
    assert block.count("- class=") == 5


def test_feedback_survives_workspace_rename(tmp_path):
    # wrap_untrusted mints a fresh random nonce per call (envelope.py) — strip it
    # so the comparison targets the fingerprint-keyed body, not per-call randomness.
    strip_nonce = lambda s: re.sub(r'nonce="[0-9a-f]+"', 'nonce="X"', s)

    def rej(fid):
        return Finding(id=fid, rule_id="r", cls="authz", status=FindingStatus.REJECTED,
                       severity=Severity.LOW, file="a.py", line=1, message="m",
                       fingerprint="fp-123")

    ws_a = Workspace(tmp_path / "name-a")
    write_findings(ws_a, [rej("R-1")])
    out_a = render_fp_feedback(ws_a)
    assert out_a  # non-empty — guard against a vacuous "" == "" pass
    ws_b = Workspace(tmp_path / "renamed-b")
    write_findings(ws_b, [rej("R-1")])
    assert strip_nonce(render_fp_feedback(ws_b)) == strip_nonce(out_a)
