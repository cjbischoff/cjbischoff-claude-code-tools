"""REQ-14: a Go CodeQL database builds without compiling in the target tree."""

from __future__ import annotations

import subprocess
from pathlib import Path

from sec_overlay.codeql import CodeQLError, run_codeql
from sec_overlay.prefilter import run_prefilter
from sec_overlay.profile import ScanProfile
from sec_overlay.workspace import Workspace

_CALLS: list[list[str]] = []


def _runner(argv, **kwargs):
    _CALLS.append(list(argv))
    return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")


def _create_argv(target: Path, language: str, db: Path) -> list[str]:
    _CALLS.clear()
    try:
        run_codeql(str(target), language, str(db), runner=_runner)
    except CodeQLError:
        pass
    return next(a for a in _CALLS if "create" in a)


def _profile(language: str) -> ScanProfile:
    return ScanProfile(
        languages=[language], frameworks=[], entrypoints=[], runnable=True,
        attack_surface=["ssrf"],
        sast_plan={"codeql": {"run": True, "languages": [language]}},
        agents_to_spawn=["ssrf"], budget_hint={},
    )


def _failing_prefilter(tmp_path: Path, language: str) -> dict:
    ws = Workspace(tmp_path / "ws")
    ws.ensure()

    def boom(*a, **k):
        raise CodeQLError("codeql database create failed (exit 32): build error")

    return run_prefilter(
        ws, "tgt", _profile(language), semgrep=lambda *a, **k: [], codeql=boom,
        has_tool=lambda n: "/x", qlpack_fn=lambda lang: True, strict=False,
    )


def test_go_create_passes_build_mode_none(tmp_path: Path) -> None:
    argv = _create_argv(tmp_path, "go", tmp_path / "db")
    assert "--build-mode=none" in argv


def test_python_create_does_not_pass_build_mode(tmp_path: Path) -> None:
    argv = _create_argv(tmp_path, "python", tmp_path / "db")
    assert not any(a.startswith("--build-mode") for a in argv)


def test_go_create_still_names_the_source_root(tmp_path: Path) -> None:
    argv = _create_argv(tmp_path, "go", tmp_path / "db")
    assert f"--source-root={tmp_path}" in argv


def test_go_build_failure_records_a_reason(tmp_path: Path) -> None:
    res = _failing_prefilter(tmp_path, "go")
    assert res["skipped_reasons"]["codeql-go"] == "build-unfenceable"
    assert res["failed"][0]["backend"] == "codeql"


def test_a_python_build_failure_records_no_go_reason(tmp_path: Path) -> None:
    res = _failing_prefilter(tmp_path, "python")
    assert "codeql-go" not in res["skipped_reasons"]


def test_the_go_reason_is_not_a_backend(tmp_path: Path) -> None:
    res = _failing_prefilter(tmp_path, "go")
    assert "codeql-go" not in res["backends_run"]
