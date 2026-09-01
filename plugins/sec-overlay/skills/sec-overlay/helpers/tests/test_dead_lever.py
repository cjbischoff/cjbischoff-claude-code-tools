"""Group 2 acceptance tests: every declared lever has a caller (RC-14)."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from types import SimpleNamespace

from sec_overlay.context import Context, ContextItem, prior_context_path
from sec_overlay.postflight import run_postflight
from sec_overlay.workspace import Workspace


def _ws_with_prior(tmp_path: Path, where: str) -> Workspace:
    """A workspace whose prior context holds one settled non-finding at ``where``."""
    ws = Workspace(tmp_path / "ws")
    ws.ensure()
    old = Context(
        items=[ContextItem(
            kind="note", trust="prior-scan", cls="xss",
            text="settled non-finding (xss): sanitized at the sink",
            where=where, source_doc="scan@aaa")],
        provenance={"sha": "aaa", "kind": "postflight"},
    )
    prior_context_path(ws).write_text(json.dumps(old.to_dict()))
    return ws


def _fake_git(stdout: str, seen: list[dict]):
    """A runner that records every call and returns ``stdout`` for the diff."""
    def run(cmd, **kwargs):
        seen.append({"cmd": cmd, "cwd": kwargs.get("cwd")})
        return SimpleNamespace(returncode=0, stdout=stdout, stderr="")
    return run


def test_postflight_drops_prior_items_on_changed_files(tmp_path: Path):
    ws = _ws_with_prior(tmp_path, "src/a.ts:9")
    seen: list[dict] = []
    total = run_postflight(
        ws, "bbb", target="/repo", runner=_fake_git("src/a.ts\n", seen))
    merged = Context.from_dict(json.loads(prior_context_path(ws).read_text()))
    assert total == 0
    assert merged.items == []
    assert seen and seen[0]["cwd"] == "/repo"
    assert seen[0]["cmd"][:4] == ["git", "diff", "--name-only", "aaa"]


def test_postflight_keeps_prior_items_on_unchanged_files(tmp_path: Path):
    ws = _ws_with_prior(tmp_path, "src/a.ts:9")
    total = run_postflight(
        ws, "bbb", target="/repo", runner=_fake_git("src/other.ts\n", []))
    assert total == 1


def test_postflight_merge_key_ignores_a_leading_dot_slash(tmp_path: Path):
    ws = _ws_with_prior(tmp_path, "./src/a.ts:9")
    total = run_postflight(
        ws, "bbb", target="/repo", runner=_fake_git("src/a.ts\n", []))
    assert total == 0


def test_postflight_without_a_target_keeps_every_prior_item(tmp_path: Path):
    ws = _ws_with_prior(tmp_path, "src/a.ts:9")
    assert run_postflight(ws, "bbb") == 1


def test_cost_module_exposes_only_timing_helpers():
    import sec_overlay.cost as cost

    public = {
        k
        for k, v in vars(cost).items()
        if not k.startswith("_")
        and inspect.isfunction(v)
        and v.__module__ == "sec_overlay.cost"
    }
    assert public == {"record_timing", "aggregate_timings_by_phase"}


def test_report_renders_no_token_or_usd_line(tmp_path: Path):
    from sec_overlay.report import write_report

    ws = Workspace(tmp_path / "ws")
    ws.ensure()
    write_report(ws)
    md = (ws.reports / "report.md").read_text()
    assert "Tokens by" not in md
    assert "Estimated cost" not in md


def test_skill_md_never_names_record_agent():
    skill = Path(__file__).resolve().parents[2] / "SKILL.md"
    assert "record_agent(" not in skill.read_text()
