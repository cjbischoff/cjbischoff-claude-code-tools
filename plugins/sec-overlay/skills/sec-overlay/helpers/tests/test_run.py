import json
import subprocess

import pytest

from sec_overlay.run import WorkingTreeFenceError, fence, receipt, write_env
from sec_overlay.workspace import Workspace


def _fake_runner(stdout: str):
    def run(cmd, *a, **k):
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")
    return run


def test_fence_passes_when_tree_matches_baseline(tmp_path):
    baseline = "?? untracked.txt\n"
    fence(tmp_path, baseline, runner=_fake_runner("?? untracked.txt\n"))


def test_fence_raises_and_names_new_delta(tmp_path):
    baseline = ""
    with pytest.raises(WorkingTreeFenceError) as exc:
        fence(tmp_path, baseline, runner=_fake_runner(" M src/app.go\n"))
    assert "src/app.go" in str(exc.value)


def test_receipt_writes_counts_even_when_stdout_empty(tmp_path):
    ws = Workspace(root=tmp_path)
    ws.ensure()
    path = receipt(ws, "findings-gate", stdout="", counts={"findings": 3})
    assert path == ws.kb / "receipts" / "findings-gate.json"
    body = json.loads(path.read_text())
    assert body["phase"] == "findings-gate"
    assert body["stdout"] == ""
    assert body["counts"] == {"findings": 3}


def test_write_env_writes_all_tokens(tmp_path):
    ws = Workspace(root=tmp_path / "ws")
    ws.ensure()
    path = write_env(ws, target="/repos/app", scope=".", sha="abc123")
    assert path == ws.root / "run.env"
    lines = dict(
        line.split("=", 1) for line in path.read_text().splitlines() if "=" in line
    )
    assert lines["TARGET"] == "/repos/app"
    assert lines["WORKSPACE"] == str(ws.root)
    assert lines["SHA"] == "abc123"
    assert lines["SCAN_SCOPE"] == "."
    assert lines["REPO_ROOT"] == "/repos/app"
