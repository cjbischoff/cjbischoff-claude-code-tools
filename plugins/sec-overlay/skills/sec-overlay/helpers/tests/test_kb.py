"""Tests for KB file plumbing."""

from sec_overlay.kb import (
    arc42_path,
    arch_dir,
    container_diagram_path,
    dfd_path,
    kb_status,
    profile_path,
    read_profile,
    threat_dir,
    threat_model_path,
    write_profile,
)
from sec_overlay.profile import ScanProfile
from sec_overlay.workspace import Workspace


def _profile():
    return ScanProfile(
        languages=["python"], frameworks=["flask"], entrypoints=["app.py:get_user"],
        runnable=False, attack_surface=["sqli"], sast_plan={"semgrep": {"run": True}},
        agents_to_spawn=["sqli"], budget_hint={"max_candidates": 200},
    )


def test_profile_write_read_roundtrip(tmp_path):
    ws = Workspace(tmp_path / "workspace"); ws.ensure()
    write_profile(ws, _profile())
    assert profile_path(ws).exists()
    assert read_profile(ws).frameworks == ["flask"]


def test_kb_status_reflects_presence(tmp_path):
    ws = Workspace(tmp_path / "workspace"); ws.ensure()
    assert kb_status(ws) == {"profile": False, "architecture": False, "threat_model": False}
    write_profile(ws, _profile())
    threat_model_path(ws).write_text("# threats")
    st = kb_status(ws)
    assert st["profile"] is True and st["threat_model"] is True and st["architecture"] is False


def test_new_tree_paths(tmp_path):
    ws = Workspace(tmp_path)
    assert arch_dir(ws) == tmp_path / "architecture"
    assert arc42_path(ws) == tmp_path / "architecture" / "arc42.md"
    assert container_diagram_path(ws) == tmp_path / "architecture" / "container-diagram.mmd"
    assert threat_dir(ws) == tmp_path / "threat-model"
    assert threat_model_path(ws) == tmp_path / "threat-model" / "threat-model.md"
    assert dfd_path(ws) == tmp_path / "threat-model" / "dfd.mmd"
