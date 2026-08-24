"""REQ-08: every token an audit-lane prompt uses is in the dispatch substitution map."""

from __future__ import annotations

import re
from pathlib import Path

from sec_overlay.driver import DISPATCH_TOKENS, render_dispatch
from sec_overlay.phases import PHASE_TABLE
from sec_overlay.workspace import Workspace

AGENTS = Path(__file__).resolve().parents[2] / "agents"
TOKEN = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def _dispatched_prompts() -> list[Path]:
    """Every prompt the audit-dispatch lane renders, per PHASE_TABLE (Ruling 36)."""
    return sorted({AGENTS / p.prompt for p in PHASE_TABLE if p.prompt})


def _ctx(tmp_path):
    from sec_overlay.driver import AuditContext

    ws = Workspace(root=tmp_path / "ws")
    ws.ensure()
    return AuditContext(target=str(tmp_path / "repo"), ws=ws, config="", sha="deadbeef")


def test_every_dispatched_prompt_token_is_substitutable():
    gaps: dict[str, list[str]] = {}
    for p in _dispatched_prompts():
        assert p.exists(), f"PHASE_TABLE names a missing prompt: {p.name}"
        for token in sorted(set(TOKEN.findall(p.read_text()))):
            if token in DISPATCH_TOKENS:
                continue
            gaps.setdefault(token, []).append(p.name)
    assert not gaps, f"prompts use tokens the dispatch map cannot fill: {gaps}"


def test_fp_feedback_token_names_a_written_file(tmp_path):
    """The token carries a path, and the file exists by the time the block is printed."""
    ctx = _ctx(tmp_path)
    block = render_dispatch(_dispatch_phase(), ctx)
    m = re.search(r"\{\{FP_FEEDBACK\}\}=(\S+)", block)
    assert m, f"no FP_FEEDBACK token in:\n{block}"
    path = Path(m.group(1))
    assert path == ctx.ws.kb / "fp-feedback.md"
    assert path.read_text().strip(), "the fp-feedback file is empty"


def _dispatch_phase():
    return next(p for p in PHASE_TABLE if p.prompt == "critic.md")
