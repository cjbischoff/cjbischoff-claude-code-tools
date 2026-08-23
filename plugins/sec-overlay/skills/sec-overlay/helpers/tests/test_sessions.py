"""Tests for read-only sessions list/show rendering (REQ-S2)."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from sec_overlay import sessions


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


@pytest.fixture
def sessions_root(tmp_path: Path) -> Path:
    root = tmp_path / ".sec-overlay"
    a = root / "repoA-1111"
    _write(a / "state.json", {"pass_number": 2, "active_sha": "abc123", "stages": {"recon": "done", "report": "done"}, "budget": {}})
    _write(
        a / "artifacts" / "review_result.json",
        {"findings": [
            {"id": "F-1", "severity": "critical", "rule_id": "sqli", "path": "a.py", "line": 1},
            {"id": "F-2", "severity": "low", "rule_id": "verbose", "path": "b.py", "line": 2},
        ]},
    )
    _write(
        a / "artifacts" / "review_ledger.json",
        {"position_reviews": [{"state": "needs-position-review"}], "dropped": [{"id": "D-1"}, {"id": "D-2"}], "reflection_retractions": [], "review_findings": [{"id": "F-1"}]},
    )
    b = root / "repoB-2222"
    _write(b / "state.json", {"pass_number": 1, "active_sha": "def456", "stages": {}, "budget": {}})
    return root


def test_session_rows_lists_each_slug(sessions_root: Path):
    rows = sessions.session_rows(sessions_root)
    assert [r["id"] for r in rows] == ["repoA-1111", "repoB-2222"]
    a = rows[0]
    assert a["pass"] == 2
    assert a["sha"] == "abc123"
    assert a["findings"]["total"] == 2
    assert a["findings"]["critical"] == 1


def test_session_rows_finding_counts_zero_without_result(sessions_root: Path):
    rows = sessions.session_rows(sessions_root)
    b = rows[1]
    assert b["findings"]["total"] == 0


def test_resolve_session_latest_picks_newest_mtime(sessions_root: Path):
    os.utime(sessions_root / "repoA-1111" / "state.json", (1000, 1000))
    os.utime(sessions_root / "repoB-2222" / "state.json", (2000, 2000))
    assert sessions.resolve_session(sessions_root, "latest").name == "repoB-2222"


def test_resolve_session_by_slug(sessions_root: Path):
    assert sessions.resolve_session(sessions_root, "repoA-1111").name == "repoA-1111"


def test_resolve_session_unknown_raises(sessions_root: Path):
    with pytest.raises(KeyError):
        sessions.resolve_session(sessions_root, "nope-9999")


def test_session_detail_includes_stages_and_ledger_summary(sessions_root: Path):
    detail = sessions.session_detail(sessions_root / "repoA-1111", severity=None)
    assert detail["sha"] == "abc123"
    assert detail["stages"] == {"recon": "done", "report": "done"}
    assert detail["ledger"]["position_reviews"] == 1
    assert detail["ledger"]["dropped"] == 2
    assert len(detail["findings"]) == 2


def test_session_detail_severity_filter(sessions_root: Path):
    detail = sessions.session_detail(sessions_root / "repoA-1111", severity="critical")
    assert [f["id"] for f in detail["findings"]] == ["F-1"]


def test_render_detail_contains_sha_and_phase(sessions_root: Path):
    detail = sessions.session_detail(sessions_root / "repoA-1111", severity=None)
    text = sessions.render_detail(detail)
    assert "abc123" in text
    assert "recon" in text


def test_render_rows_contains_ids(sessions_root: Path):
    text = sessions.render_rows(sessions.session_rows(sessions_root))
    assert "repoA-1111" in text
    assert "repoB-2222" in text
