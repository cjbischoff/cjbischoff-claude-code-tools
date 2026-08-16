import json
import subprocess

import pytest

from sec_overlay.run import WorkingTreeFenceError, fence, receipt
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
