"""REQ-16: the prefilter receipt lands before the stage is recorded."""

from __future__ import annotations

import json

import pytest

from sec_overlay.exclusions import Exclusions
from sec_overlay.prefilter import run_prefilter
from sec_overlay.state import load_state
from sec_overlay.workspace import Workspace


def _profile():
    from sec_overlay.profile import ScanProfile

    return ScanProfile(
        languages=["python"],
        frameworks=[],
        entrypoints=[],
        runnable=False,
        attack_surface=[],
        sast_plan={"semgrep": {"run": True, "rulesets": ["r/python"], "security_only": False}},
        agents_to_spawn=[],
        budget_hint={},
        notes={},
        subsystems=[],
        attack_surface_evidence={},
        scan_options={},
    )


def test_prefilter_writes_its_receipt(tmp_path):
    target = tmp_path / "repo"
    target.mkdir()
    ws = Workspace(root=tmp_path / "ws")
    ws.ensure()
    run_prefilter(
        ws,
        str(target),
        _profile(),
        semgrep=lambda t, cfg: [],
        has_tool=lambda name: name == "semgrep",
        exclusions_fn=lambda w: Exclusions(set(), [], set()),
    )
    rcpt = ws.kb / "receipts" / "prefilter.json"
    assert rcpt.exists(), "no prefilter receipt on disk"
    assert json.loads(rcpt.read_text())["counts"]["findings_in"] == 0


def test_prefilter_backend_abort_leaves_the_stage_not_done(tmp_path):
    """A planned backend that never ran raises, and the stage stays unrecorded."""
    target = tmp_path / "repo"
    target.mkdir()
    ws = Workspace(root=tmp_path / "ws")
    ws.ensure()
    with pytest.raises(RuntimeError):
        run_prefilter(
            ws,
            str(target),
            _profile(),
            semgrep=lambda t, cfg: [],
            has_tool=lambda name: False,
            exclusions_fn=lambda w: Exclusions(set(), [], set()),
        )
    assert "prefilter" not in load_state(ws).stages
