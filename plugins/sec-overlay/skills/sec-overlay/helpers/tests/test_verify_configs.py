"""REQ-22: the verify verdict reads the planned rulesets, not the caller's scalar."""

from __future__ import annotations

from sec_overlay import kb
from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.profile import ScanProfile
from sec_overlay.verify import resolve_configs, verify_findings
from sec_overlay.workspace import Workspace, write_findings


def _ws(tmp_path):
    ws = Workspace(tmp_path / "workspace")
    ws.ensure()
    return ws


def _confirmed():
    return Finding(id="F-1", rule_id="r", cls="sqli", status=FindingStatus.CONFIRMED,
                   severity=Severity.HIGH, file="app.py", line=1, message="m",
                   patch_diff="--- a/app.py\n+++ b/app.py\n")


def test_resolve_configs_reads_the_planned_rulesets(tmp_path):
    ws = _ws(tmp_path)
    kb.write_profile(ws, ScanProfile(sast_plan={"semgrep": {"rulesets": ["profile-rules.yaml"]}}))
    assert resolve_configs(ws, "caller.yaml") == ["profile-rules.yaml"]


def test_resolve_configs_falls_back_without_a_profile(tmp_path):
    assert resolve_configs(_ws(tmp_path), "caller.yaml") == ["caller.yaml"]


def test_resolve_configs_falls_back_on_an_empty_plan(tmp_path):
    ws = _ws(tmp_path)
    kb.write_profile(ws, ScanProfile(sast_plan={"semgrep": {"rulesets": []}}))
    assert resolve_configs(ws, "caller.yaml") == ["caller.yaml"]


def test_resolve_configs_falls_back_on_a_malformed_plan(tmp_path):
    ws = _ws(tmp_path)
    kb.write_profile(ws, ScanProfile(sast_plan={"semgrep": "not-a-dict"}))
    assert resolve_configs(ws, "caller.yaml") == ["caller.yaml"]


def test_the_verdict_ignores_the_caller_scalar(tmp_path):
    """Two different caller scalars must produce the same config the verifier sees."""
    seen = []

    def spy(target, diff, config, file, cls, sources, **kwargs):
        seen.append(config)
        return "rule-no-match"

    for scalar in ("a.yaml", "b.yaml"):
        ws = _ws(tmp_path / scalar)
        kb.write_profile(ws, ScanProfile(sast_plan={"semgrep": {"rulesets": ["planned.yaml"]}}))
        write_findings(ws, [_confirmed()])
        verify_findings(ws, "t", scalar, verifier=spy)

    assert seen == [["planned.yaml"], ["planned.yaml"]]
