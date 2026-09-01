"""REQ-15: no candidate path survives the prefilter as an absolute path."""

from __future__ import annotations

from pathlib import Path

from sec_overlay.exclusions import Exclusions
from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.prefilter import run_prefilter
from sec_overlay.profile import ScanProfile
from sec_overlay.workspace import Workspace, read_findings


def _profile(target: str) -> ScanProfile:
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


def _absolute_hit(target: Path) -> list[Finding]:
    return [
        Finding(
            id="C-0001",
            rule_id="semgrep:python.ssrf",
            cls="ssrf",
            status=FindingStatus.CANDIDATE,
            severity=Severity.HIGH,
            file=str(target / "src" / "app.py"),
            line=42,
            message="absolute path from the backend",
            evidence_sources=["semgrep:python.ssrf"],
        )
    ]


def test_prefilter_relativizes_an_absolute_backend_path(tmp_path):
    target = tmp_path / "repo"
    (target / "src").mkdir(parents=True)
    (target / "src" / "app.py").write_text("x = 1\n")
    ws = Workspace(root=tmp_path / "ws")
    ws.ensure()
    run_prefilter(
        ws,
        str(target),
        _profile(str(target)),
        semgrep=lambda t, cfg: _absolute_hit(target),
        has_tool=lambda name: name == "semgrep",
        exclusions_fn=lambda w: Exclusions(set(), [], set()),
    )
    files = [f.file for f in read_findings(ws)]
    assert files == ["src/app.py"], files
    assert not any(Path(p).is_absolute() for p in files)


def test_prefilter_leaves_an_already_relative_path_alone(tmp_path):
    target = tmp_path / "repo"
    (target / "src").mkdir(parents=True)
    ws = Workspace(root=tmp_path / "ws")
    ws.ensure()
    hit = _absolute_hit(target)
    hit[0].file = "src/app.py"
    run_prefilter(
        ws,
        str(target),
        _profile(str(target)),
        semgrep=lambda t, cfg: hit,
        has_tool=lambda name: name == "semgrep",
        exclusions_fn=lambda w: Exclusions(set(), [], set()),
    )
    assert [f.file for f in read_findings(ws)] == ["src/app.py"]


def test_prefilter_keeps_an_outside_path_verbatim(tmp_path):
    """A path outside the target is not silently rewritten; it stays visible as-is."""
    target = tmp_path / "repo"
    target.mkdir()
    ws = Workspace(root=tmp_path / "ws")
    ws.ensure()
    hit = _absolute_hit(target)
    hit[0].file = str(tmp_path / "elsewhere" / "vendored.py")
    run_prefilter(
        ws,
        str(target),
        _profile(str(target)),
        semgrep=lambda t, cfg: hit,
        has_tool=lambda name: name == "semgrep",
        exclusions_fn=lambda w: Exclusions(set(), [], set()),
    )
    assert [f.file for f in read_findings(ws)] == [str(tmp_path / "elsewhere" / "vendored.py")]
