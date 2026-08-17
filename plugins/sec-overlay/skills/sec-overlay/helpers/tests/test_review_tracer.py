"""Tests for the review tracer: one changed file, one hunk, end to end."""

import json
import subprocess

from sec_overlay.cli import main
from sec_overlay.diffhunks import added_line_numbers, parse_hunks
from sec_overlay.diffscope import changed_file_records, validate_ref
from sec_overlay.phase_gate import review_position_gate
from sec_overlay.positioning import resolve_position

_BASE_SHA = "a" * 40
_HEAD_SHA = "b" * 40

_DIFF = (
    "diff --git a/app.py b/app.py\n"
    "index 1111111..2222222 100644\n"
    "--- a/app.py\n"
    "+++ b/app.py\n"
    "@@ -1,2 +1,3 @@\n"
    " import os\n"
    "+os.system(cmd)\n"
    " print('hi')\n"
)


def _fake_run(cmd, capture_output, text, check):
    class R:
        returncode = 0

    r = R()
    if "--verify" in cmd:
        r.stdout = f"{cmd[-1]}\n"
    elif "--name-status" in cmd:
        r.stdout = "M\tapp.py\n"
    elif "--unified=3" in cmd:
        r.stdout = _DIFF
    else:
        r.stdout = ""
    return r


class _FakeFinding:
    def __init__(self, file: str, line: int, evidence: str = "os.system(cmd)"):
        self.id = "F-1"
        self.file = file
        self.line = line
        self.evidence = evidence


def test_review_one_changed_file_exits_zero_and_seals_complete(tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run)
    rc = main(["review", "--base", _BASE_SHA, "--head", _HEAD_SHA, "--root", str(tmp_path)])
    assert rc == 0

    manifest_path = tmp_path / "artifacts" / "coverage_manifest.json"
    data = json.loads(manifest_path.read_text())
    assert data["base_sha"] == _BASE_SHA
    assert data["head_sha"] == _HEAD_SHA
    assert data["seal"] == "complete"
    assert len(data["files"]) == 1
    assert data["files"][0]["state"] == "done"


def test_validate_ref_accepts_sha_and_rejects_leading_dash():
    assert validate_ref(_BASE_SHA) == _BASE_SHA
    try:
        validate_ref("-rf")
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "-rf" in str(exc)


def test_parse_hunks_and_added_line_numbers():
    hunks = parse_hunks(_DIFF)
    assert len(hunks) == 1
    assert added_line_numbers(hunks) == {2}


def test_resolve_position_exact_for_added_line():
    hunks_by_path = {"app.py": parse_hunks(_DIFF)}
    result = resolve_position("app.py", 2, "os.system(cmd)", hunks_by_path, {})
    assert result.decision == "exact"


def test_review_position_gate_keeps_finding_on_added_line():
    hunks_by_path = {"app.py": parse_hunks(_DIFF)}
    finding = _FakeFinding("app.py", 2)
    kept, dropped = review_position_gate([finding], hunks_by_path)
    assert kept == [finding]
    assert dropped == []


def test_changed_file_records_parses_name_status():
    class R:
        stdout = "M\tapp.py\n"
        returncode = 0

    def fake(cmd, capture_output, text, check):
        assert "--name-status" in cmd
        return R()

    records = changed_file_records(_BASE_SHA, _HEAD_SHA, runner=fake)
    assert len(records) == 1
    assert records[0].path == "app.py"
    assert records[0].status == "M"
