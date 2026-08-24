"""REQ-17: the attack-class fan-out list round-trips through the dispatch block."""

from __future__ import annotations

import json
import re

from sec_overlay.driver import render_dispatch


def _substitute_line(block: str) -> str:
    line = next(ln for ln in block.splitlines() if ln.strip().startswith("substitute:"))
    return line.split("substitute:", 1)[1].strip()


def _attack_class_value(block: str) -> str:
    m = re.search(r"\{\{ATTACK_CLASS\}\}=(\S+)", block)
    assert m, f"no ATTACK_CLASS token in:\n{block}"
    return m.group(1)


def _agent_phase():
    from sec_overlay.phases import PHASE_TABLE

    return next(p for p in PHASE_TABLE if p.prompt == "investigate.md")


def _ctx(tmp_path):
    from sec_overlay.driver import AuditContext
    from sec_overlay.workspace import Workspace

    ws = Workspace(root=tmp_path / "ws")
    ws.ensure()
    return AuditContext(target=str(tmp_path / "repo"), ws=ws, config="", sha="deadbeef")


def test_attack_class_round_trips_as_json(tmp_path):
    classes = ["ssrf", "path-traversal", "cmdi"]
    block = render_dispatch(_agent_phase(), _ctx(tmp_path), classes=classes)
    assert json.loads(_attack_class_value(block)) == classes


def test_attack_class_value_carries_no_space(tmp_path):
    """The substitute line is space-joined, so the JSON must be compact."""
    block = render_dispatch(_agent_phase(), _ctx(tmp_path), classes=["ssrf", "cmdi"])
    value = _attack_class_value(block)
    assert " " not in value
    assert _substitute_line(block).count("{{") == 4


def test_a_single_class_still_renders_a_list(tmp_path):
    block = render_dispatch(_agent_phase(), _ctx(tmp_path), classes=["ssrf"])
    assert json.loads(_attack_class_value(block)) == ["ssrf"]


def test_no_classes_omits_the_token(tmp_path):
    block = render_dispatch(_agent_phase(), _ctx(tmp_path), classes=None)
    assert "ATTACK_CLASS" not in block
