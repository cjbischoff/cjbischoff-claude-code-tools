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


def test_pack_flags_the_construction_that_omits_the_safe_option():
    hits = {(Path(r["path"]).name, r["check_id"].rsplit(".", 1)[-1]) for r in _scan()}
    assert ("vulnerable.go", "go-rego-new-missing-capabilities") in hits
    assert ("render.py", "python-jinja2-environment-missing-sandbox") in hits


def test_pack_stays_silent_on_the_construction_that_carries_the_safe_option():
    """The whole value of an absence rule is that the fixed site produces no finding."""
    flagged = {Path(r["path"]).name for r in _scan()}
    assert "safe.go" not in flagged


def test_every_absence_rule_declares_its_class_in_metadata():
    """The prefilter routes a semgrep hit by metadata.cls; a rule without one routes nowhere."""
    import re

    for path in sorted(_PACK.glob("*.yaml")):
        text = path.read_text()
        ids = re.findall(r"^\s*-?\s*id:\s*(\S+)", text, re.MULTILINE)
        assert ids, f"{path.name}: no rule ids"
        assert text.count("cls:") >= len(ids), f"{path.name}: a rule is missing metadata.cls"
