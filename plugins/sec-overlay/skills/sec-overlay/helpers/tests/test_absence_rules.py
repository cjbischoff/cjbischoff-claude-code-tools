"""The absence pack must fire on the missing-option site and stay silent on the safe one."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

_HELPERS = Path(__file__).resolve().parents[1]
_PACK = _HELPERS / "rules" / "absence"
_FIXTURE = _HELPERS / "fixtures" / "absence_repo"

pytestmark = pytest.mark.skipif(shutil.which("semgrep") is None, reason="semgrep not installed")


def _scan() -> list[dict]:
    completed = subprocess.run(
        ["semgrep", "scan", "--config", str(_PACK), "--json", "--quiet",
         "--no-git-ignore", str(_FIXTURE)],
        capture_output=True, text=True, check=False,
    )
    return json.loads(completed.stdout)["results"]


def _hits() -> set[tuple[str, str, int]]:
    """Return one (file name, rule id, line) tuple per hit in the fixture repo."""
    return {
        (Path(r["path"]).name, r["check_id"].rsplit(".", 1)[-1], r["start"]["line"])
        for r in _scan()
    }


def test_pack_flags_the_construction_that_omits_the_safe_option():
    hits = {(name, rule) for name, rule, _ in _hits()}
    assert ("vulnerable.go", "go-rego-new-missing-capabilities") in hits
    assert ("render.py", "python-jinja2-environment-missing-sandbox") in hits


def test_pack_stays_silent_on_the_construction_that_carries_the_safe_option():
    """The whole value of an absence rule is that the fixed site produces no finding."""
    flagged = {Path(r["path"]).name for r in _scan()}
    assert "safe.go" not in flagged


def test_cel_env_rule_finds_the_undeclared_environment_and_ignores_the_declared_one():
    """cel.NewEnv with no declaration list inherits every host function."""
    hits = _hits()
    rule = "go-cel-env-missing-declarations"
    assert ("engines_unsafe.go", rule, 11) in hits
    assert not [h for h in hits if h[0] == "engines_safe.go" and h[1] == rule]


def test_lua_state_rule_finds_the_default_library_state_and_ignores_the_skipping_one():
    """gopher-lua takes Options by value; a pointer-literal negation fires on fixed code."""
    hits = _hits()
    rule = "go-lua-state-missing-skipopenlibs"
    assert ("engines_unsafe.go", rule, 17) in hits
    assert not [h for h in hits if h[0] == "engines_safe.go" and h[1] == rule]


def test_requests_rule_finds_the_untimed_call_and_ignores_the_timed_one():
    """The timed call sits in the same file, so this pair is keyed by line."""
    hits = _hits()
    rule = "python-requests-missing-timeout"
    assert ("fetch.py", rule, 8) in hits
    assert ("fetch.py", rule, 13) not in hits


def test_every_absence_rule_declares_its_class_in_metadata():
    """The prefilter routes a semgrep hit by metadata.cls; a rule without one routes nowhere.

    Checks placement, not just a raw count: each rule's own block must contain a
    `metadata:` line followed by a `cls:` line, so a `cls:` that belongs to an
    unrelated rule or sits outside `metadata:` cannot pass this guard.
    """
    import re

    id_re = re.compile(r"^\s*-?\s*id:\s*(\S+)")
    for path in sorted(_PACK.glob("*.yaml")):
        lines = path.read_text().splitlines()
        starts = [i for i, line in enumerate(lines) if id_re.match(line)]
        assert starts, f"{path.name}: no rule ids"
        for start, end in zip(starts, starts[1:] + [len(lines)]):
            block = lines[start:end]
            id_match = id_re.match(block[0])
            assert id_match is not None
            rule_id = id_match.group(1)
            meta_at = next((i for i, l in enumerate(block) if "metadata:" in l), None)
            assert meta_at is not None, f"{path.name}: {rule_id} has no metadata block"
            assert any("cls:" in l for l in block[meta_at + 1 :]), (
                f"{path.name}: {rule_id} is missing metadata.cls"
            )
