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


_INSERTING_DIFF = (
    "--- a/app.py\n"
    "+++ b/app.py\n"
    "@@ -1,2 +1,5 @@\n"
    "+import os\n"
    "+import posixpath\n"
    "+\n"
    "-p = path.join(base, name)\n"
    "+p = path.resolve(base, name)\n"
)


def _evidence_hit(path: str, line: int, text: str) -> Finding:
    f = _hit(path)
    f.line = line
    f.evidence = text
    return f


def test_a_rule_that_matches_both_constructions_reports_no_discriminate(monkeypatch):
    pre = _evidence_hit("app.py", 177, "p = path.join(base, name)")
    post = _evidence_hit("app.py", 180, "p = path.resolve(base, name)")
    seen = {"n": 0}

    def fake_hit(target_dir, config, file_path, cls, rules, *, detail=None, **kw):
        seen["n"] += 1
        if detail is not None:
            detail.append(pre if seen["n"] == 1 else post)
        return True

    monkeypatch.setattr(V, "_file_has_hit", fake_hit)
    monkeypatch.setattr(V, "apply_patch", lambda d, p, **k: True)
    monkeypatch.setattr(V.shutil, "copytree", lambda *a, **k: None)
    out = V.verify_patch("/repo", _INSERTING_DIFF, "cfg", "app.py", "path-traversal")
    assert out == "rule-no-discriminate"


def test_a_surviving_construction_still_reports_not_fixed(monkeypatch):
    same = _evidence_hit("app.py", 177, "p = path.join(base, name)")

    def fake_hit(target_dir, config, file_path, cls, rules, *, detail=None, **kw):
        if detail is not None:
            detail.append(same)
        return True

    monkeypatch.setattr(V, "_file_has_hit", fake_hit)
    monkeypatch.setattr(V, "apply_patch", lambda d, p, **k: True)
    monkeypatch.setattr(V.shutil, "copytree", lambda *a, **k: None)
    out = V.verify_patch("/repo", _INSERTING_DIFF, "cfg", "app.py", "path-traversal")
    assert out == "not-fixed"


def test_the_history_reason_names_both_lines(monkeypatch, tmp_path):
    from sec_overlay.workspace import Workspace, write_findings

    pre = _evidence_hit("app.py", 177, "p = path.join(base, name)")
    post = _evidence_hit("app.py", 180, "p = path.resolve(base, name)")
    seen = {"n": 0}

    def fake_hit(target_dir, config, file_path, cls, rules, *, detail=None, **kw):
        seen["n"] += 1
        if detail is not None:
            detail.append(pre if seen["n"] == 1 else post)
        return True

    monkeypatch.setattr(V, "_file_has_hit", fake_hit)
    monkeypatch.setattr(V, "apply_patch", lambda d, p, **k: True)
    monkeypatch.setattr(V.shutil, "copytree", lambda *a, **k: None)
    ws = Workspace(root=tmp_path / "ws")
    ws.ensure()
    f = _hit("app.py")
    f.status = FindingStatus.CONFIRMED
    f.patch_diff = _INSERTING_DIFF
    write_findings(ws, [f])
    V.verify_findings(ws, "/repo", "cfg")
    entry = next(
        h for h in V.read_findings(ws)[0].history
        if h.get("event") == "verify:cause:rule-no-discriminate"
    )
    assert entry["reason"] == "pre line 177, post line 180"


def test_a_stale_last_lines_record_does_not_leak_into_the_next_verification(
    monkeypatch, tmp_path
):
    """A stubbed verifier that never populates evidence must never inherit a
    prior call's ``_LAST_LINES`` record — a module-level dict must be scoped
    per :func:`~sec_overlay.verify.verify_findings` invocation, not per process.
    """
    from sec_overlay.workspace import Workspace, write_findings

    pre = _evidence_hit("app.py", 177, "p = path.join(base, name)")
    post = _evidence_hit("app.py", 180, "p = path.resolve(base, name)")
    seen = {"n": 0}

    def fake_hit(target_dir, config, file_path, cls, rules, *, detail=None, **kw):
        seen["n"] += 1
        if detail is not None:
            detail.append(pre if seen["n"] == 1 else post)
        return True

    monkeypatch.setattr(V, "_file_has_hit", fake_hit)
    monkeypatch.setattr(V, "apply_patch", lambda d, p, **k: True)
    monkeypatch.setattr(V.shutil, "copytree", lambda *a, **k: None)

    ws1 = Workspace(root=tmp_path / "ws1")
    ws1.ensure()
    f1 = _hit("app.py")
    f1.status = FindingStatus.CONFIRMED
    f1.patch_diff = _INSERTING_DIFF
    write_findings(ws1, [f1])
    V.verify_findings(ws1, "/repo", "cfg")
    assert V._LAST_LINES  # sanity: the first call did populate the record

    ws2 = Workspace(root=tmp_path / "ws2")
    ws2.ensure()
    f2 = _hit("app.py")
    f2.status = FindingStatus.CONFIRMED
    f2.patch_diff = _INSERTING_DIFF
    write_findings(ws2, [f2])
    V.verify_findings(ws2, "/repo", "cfg", verifier=lambda *a, **kw: "not-fixed")
    entry = next(
        h for h in V.read_findings(ws2)[0].history
        if h.get("event") == "verify:cause:not-fixed"
    )
    assert entry == {"event": "verify:cause:not-fixed"}
