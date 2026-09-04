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


def test_path_matches_rejects_an_empty_path():
    """An empty path names no file: the suffix test must not treat it as a wildcard."""
    assert not V._path_matches("", "a/util.py", "/repo")
    assert not V._path_matches("/repo/a/util.py", "", "/repo")
    assert not V._path_matches("", "", "/repo")


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
    monkeypatch.setattr(V.shutil, "copytree", lambda *a, **k: None)
    out = V.verify_patch("/repo", _CROSS_FILE_DIFF, "cfg", "src/PackageSetup.ts", "path-traversal")
    assert out == "rule-no-target-file"


def test_a_cross_file_fix_with_a_clean_re_scan_is_verified(monkeypatch):
    """P5-9: the cross-file guard may only downgrade a surviving hit.

    A cross-file backend (``codeql:dataflow``, or an ``sca`` finding whose file is
    the lockfile while the patch edits the manifest) can prove such a patch clean.
    Returning before the copy, the apply, and the re-scan denies it that proof.
    """
    calls = {"n": 0}

    def fake_hit(*a, **k):
        calls["n"] += 1
        return calls["n"] == 1

    monkeypatch.setattr(V, "_file_has_hit", fake_hit)
    monkeypatch.setattr(V, "apply_patch", lambda d, p, **k: True)
    monkeypatch.setattr(V.shutil, "copytree", lambda *a, **k: None)
    out = V.verify_patch(
        "/repo", _CROSS_FILE_DIFF, "cfg", "src/PackageSetup.ts", "path-traversal",
        ["codeql:dataflow"],
    )
    assert calls["n"] == 2, "the post-patch scan never ran"
    assert out == "verified-static"


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


def test_detail_accumulates_across_every_planned_ruleset(monkeypatch):
    """A detail request must run every config, not stop at the first that hits.

    One ruleset firing pre-patch only and another firing on both sides otherwise
    yields disjoint pre/post evidence drawn from different rulesets, which
    ``_post_verdict`` reads as ``rule-no-discriminate``. The truth is
    ``not-fixed``: the second ruleset's construction survives byte-identical.
    """
    def fake_hit(target_dir, config, file_path, cls, rules, *, detail=None, **kw):
        pre_phase = target_dir == "/repo"
        if config == "c1.yaml" and not pre_phase:
            return False
        text = "c1-pre-only" if config == "c1.yaml" else "c2-survives"
        if detail is not None:
            detail.append(_evidence_hit("app.py", 10, text))
        return True

    monkeypatch.setattr(V, "_file_has_hit", fake_hit)
    monkeypatch.setattr(V, "apply_patch", lambda d, p, **k: True)
    monkeypatch.setattr(V.shutil, "copytree", lambda *a, **k: None)
    out = V.verify_patch(
        "/repo", _INSERTING_DIFF, ["c1.yaml", "c2.yaml"], "app.py", "path-traversal"
    )
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


def test_unquote_path_decodes_an_octal_escaped_utf8_path():
    """REQ-69: git escapes each non-ASCII byte in octal inside a quoted path."""
    assert V._unquote_path('"src/caf\\303\\251.py"') == "src/café.py"


def test_unquote_path_leaves_an_unquoted_path_alone():
    assert V._unquote_path("src/app.py") == "src/app.py"


def test_unquote_path_keeps_a_quoted_path_with_a_space():
    assert V._unquote_path('"src/my file.py"') == "src/my file.py"


def test_unquote_path_falls_back_to_stripping_the_quotes():
    """A body that does not decode still loses its quotes, so the path stays usable."""
    assert V._unquote_path('"src/bad\\"') == "src/bad\\"


def test_patch_files_reads_a_quoted_post_image_path():
    diff = '--- a/src/caf\\303\\251.py\n+++ "b/src/caf\\303\\251.py"\n'
    assert V._patch_files(diff) == {"src/café.py"}
