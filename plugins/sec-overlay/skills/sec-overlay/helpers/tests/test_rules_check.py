"""Tests for `rules check` resolver output and did-you-mean errors (REQ-S4)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sec_overlay import cli
from sec_overlay.rule_glob import build_resolution, resolve_with_layer


@pytest.fixture
def repo_with_rule(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    sidecar = repo / ".sec-overlay"
    sidecar.mkdir(parents=True)
    (sidecar / "myrule.md").write_text("PROJECT RULE BODY")
    (sidecar / "rule.json").write_text(
        json.dumps({"rules": [{"path": "src/**", "rule": "myrule.md"}]})
    )
    return repo


def test_resolve_with_layer_project(repo_with_rule: Path):
    resolution = build_resolution(None, [], repo_with_rule)
    layer, text = resolve_with_layer("src/app.py", resolution)
    assert layer == "project"
    assert text == "PROJECT RULE BODY"


def test_resolve_with_layer_falls_through_to_builtin(repo_with_rule: Path):
    resolution = build_resolution(None, [], repo_with_rule)
    layer, text = resolve_with_layer("docs/readme.md", resolution)
    assert layer == "builtin"
    assert text.strip()


def test_rules_check_cli_prints_layer_and_doc(repo_with_rule: Path, capsys):
    rc = cli.main(["rules", "check", "src/app.py", "--root", str(repo_with_rule)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "project" in out
    assert "PROJECT RULE BODY" in out


def test_unknown_subcommand_suggests_nearest(capsys):
    with pytest.raises(SystemExit):
        cli.main(["revieww", "--base", "HEAD~1"])
    err = capsys.readouterr().err
    assert "review" in err
    assert "Did you mean" in err
