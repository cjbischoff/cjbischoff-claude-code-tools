import json
import subprocess

import pytest

from sec_overlay.profile import ScanProfile
from sec_overlay.run import WorkingTreeFenceError, fence, infer_role, receipt, write_env
from sec_overlay.workspace import Workspace


def _profile(**kw) -> ScanProfile:
    base = {
        "languages": [],
        "frameworks": [],
        "entrypoints": [],
        "runnable": False,
        "attack_surface": [],
        "sast_plan": {},
        "agents_to_spawn": [],
        "budget_hint": {},
        "notes": {},
        "subsystems": [],
        "attack_surface_evidence": {},
        "scan_options": {},
    }
    base.update(kw)
    return ScanProfile(**base)


def test_infer_role_rbac_source_from_auth_subsystem():
    p = _profile(
        subsystems=[
            {"name": "identity", "paths": [], "why": ""},
            {"name": "rbac-policy", "paths": [], "why": ""},
        ]
    )
    assert infer_role(p) == "rbac-source"


def test_infer_role_service_enforcer_from_network_surface():
    p = _profile(attack_surface=["gRPC service", "HTTP handler"])
    assert infer_role(p) == "service-enforcer"


def test_infer_role_defaults_to_infra_when_ambiguous():
    p = _profile(
        subsystems=[{"name": "batch-jobs", "paths": [], "why": ""}],
        attack_surface=["config files"],
    )
    assert infer_role(p) == "infra"


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
