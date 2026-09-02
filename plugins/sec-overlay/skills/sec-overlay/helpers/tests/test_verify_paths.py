"""REQ-59: the verify oracle matches a scanner hit by path, not by base filename."""

from __future__ import annotations

from sec_overlay import verify as V
from sec_overlay.models import Finding, FindingStatus, Severity


def _hit(path: str) -> Finding:
    return Finding(
        id="C-0001",
        rule_id="r.sqli",
        cls="sqli",
        status=FindingStatus.CANDIDATE,
        severity=Severity.HIGH,
        file=path,
        line=7,
        message="m",
    )


def test_rel_path_strips_the_scan_root():
    assert V._rel_path("/repo/src/app.py", "/repo") == "src/app.py"
    assert V._rel_path("src/app.py", "src") == "app.py"
    assert V._rel_path("src/app.py", "") == "src/app.py"


def test_rel_path_leaves_an_unprefixed_path_alone():
    assert V._rel_path("src/app.py", "/other") == "src/app.py"


def test_path_matches_accepts_the_same_file():
    assert V._path_matches("/repo/a/util.py", "a/util.py", "/repo")


def test_path_matches_accepts_a_repo_relative_finding_under_a_scoped_target():
    assert V._path_matches("/repo/src/a/util.py", "src/a/util.py", "/repo/src")


def test_path_matches_rejects_a_same_named_file_in_another_directory():
    assert not V._path_matches("/repo/b/util.py", "a/util.py", "/repo")


def test_file_has_hit_rejects_an_aliased_same_named_file(monkeypatch):
    monkeypatch.setattr(V, "run_semgrep", lambda t, c: [_hit("/repo/b/util.py")])
    assert V._file_has_hit("/repo", "cfg", "a/util.py", "sqli", set()) is False
    monkeypatch.setattr(V, "run_semgrep", lambda t, c: [_hit("/repo/a/util.py")])
    assert V._file_has_hit("/repo", "cfg", "a/util.py", "sqli", set()) is True


_CROSS_FILE_DIFF = (
    "--- a/src/file-name-sanitize.ts\n"
    "+++ b/src/file-name-sanitize.ts\n"
    "@@ -1 +1,2 @@\n"
    "+export const sanitize = (s: string) => s.replace(/\\.\\./g, '');\n"
)


def test_patch_files_reads_the_post_image_paths():
    assert V._patch_files(_CROSS_FILE_DIFF) == {"src/file-name-sanitize.ts"}
    assert V._patch_files("--- a/app.py\n+++ b/app.py\n") == {"app.py"}
    assert V._patch_files("no diff here") == set()


def test_a_cross_file_fix_is_not_reported_as_not_fixed(monkeypatch):
    monkeypatch.setattr(V, "_file_has_hit", lambda *a, **k: True)
    monkeypatch.setattr(V, "apply_patch", lambda d, p, **k: True)
    out = V.verify_patch("/repo", _CROSS_FILE_DIFF, "cfg", "src/PackageSetup.ts", "path-traversal")
    assert out == "rule-no-target-file"


def test_the_new_cause_maps_to_a_legal_verification():
    assert "rule-no-target-file" in V.VERIFY_CAUSES
    assert V._CAUSE_TO_VERIFICATION["rule-no-target-file"] == "static-only"
