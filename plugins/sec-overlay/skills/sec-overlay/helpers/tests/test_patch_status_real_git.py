"""REQ-01: an additive patch whose lines are absent is NOT_APPLIED, not APPLIED."""

from __future__ import annotations

import shutil
import subprocess

import pytest

from sec_overlay.patch_status import PatchStatus, check_patch_applied

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")

_ADDITIVE = """--- a/app.py
+++ b/app.py
@@ -1,2 +1,3 @@
 import os
+SAFE = True
 x = 1
"""


def _repo(tmp_path, body):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text(body)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "app.py"], cwd=repo, check=True)
    return str(repo)


@needs_git
def test_absent_added_line_is_not_applied(tmp_path):
    target = _repo(tmp_path, "import os\nx = 1\n")
    assert check_patch_applied(target, _ADDITIVE) is PatchStatus.NOT_APPLIED


@needs_git
def test_present_added_line_is_applied(tmp_path):
    target = _repo(tmp_path, "import os\nSAFE = True\nx = 1\n")
    assert check_patch_applied(target, _ADDITIVE) is PatchStatus.APPLIED
