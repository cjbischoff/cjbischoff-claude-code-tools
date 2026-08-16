import json
import subprocess

import pytest

from sec_overlay.correlate.manifest import validate_manifest
from sec_overlay.profile import ScanProfile
from sec_overlay.run import (
    WorkingTreeFenceError,
    fence,
    infer_role,
    receipt,
    synthesize_manifest,
    write_env,
)
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


def test_synthesize_manifest_is_valid_and_keys_distinct():
    members = [
        {"slug": "app", "repo_root": "/repos/app", "scan_scope": "svc-a", "role": "service-enforcer"},
        {"slug": "app", "repo_root": "/repos/app", "scan_scope": "svc-b", "role": "infra"},
    ]
    manifest = synthesize_manifest("product-x", members)
    assert validate_manifest(manifest) == []
    keys = {f'{m["slug"]}#{m["scan_scope"]}' for m in manifest["members"]}
    assert keys == {"app#svc-a", "app#svc-b"}


def test_synthesize_manifest_rejects_bad_role():
    with pytest.raises(ValueError):
        synthesize_manifest(
            "p", [{"slug": "a", "repo_root": "/a", "scan_scope": ".", "role": "nonsense"}]
        )


def test_drive_writes_receipt_and_env_and_fences(tmp_path, monkeypatch):
    import subprocess

    from sec_overlay import run as run_mod

    target = tmp_path / "repo"
    target.mkdir()
    ws_root = tmp_path / "ws"

    # git status --porcelain returns clean both at baseline and per phase
    def fake_git(cmd, *a, **k):
        if cmd[:2] == ["git", "-C"] and "status" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if "rev-parse" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout="deadbeef\n", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    from sec_overlay.driver import DETERMINISTIC_ACTIONS
    from sec_overlay.phases import PhaseSpec

    DETERMINISTIC_ACTIONS["noop"] = lambda ctx: None
    table = (PhaseSpec("noop", "deterministic", (), ()),)
    monkeypatch.setattr(run_mod, "_PHASE_TABLE", table, raising=False)

    result = run_mod.drive(
        str(target), config="", workspace=str(ws_root), runner=fake_git, table=table
    )
    assert result == "AUDIT COMPLETE"
    assert (ws_root / "run.env").exists()
    assert (ws_root / "kb" / "receipts" / "noop.json").exists()
