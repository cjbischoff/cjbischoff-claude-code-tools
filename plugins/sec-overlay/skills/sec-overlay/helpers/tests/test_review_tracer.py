"""Tests for the review tracer: one changed file, one hunk, end to end."""

import json
import subprocess

from sec_overlay import reflection, rule_glob
from sec_overlay.cli import main, run_review
from sec_overlay.diffhunks import added_line_numbers, parse_hunks
from sec_overlay.diffscope import changed_file_records, validate_ref
from sec_overlay.phase_gate import review_position_gate
from sec_overlay.positioning import resolve_position

_BASE_SHA = "a" * 40
_HEAD_SHA = "b" * 40

_DIFF = (
    "diff --git a/app.py b/app.py\n"
    "index 1111111..2222222 100644\n"
    "--- a/app.py\n"
    "+++ b/app.py\n"
    "@@ -1,2 +1,3 @@\n"
    " import os\n"
    "+os.system(cmd)\n"
    " print('hi')\n"
)


def _fake_run(cmd, capture_output, text, check):
    class R:
        returncode = 0

    r = R()
    if "--verify" in cmd:
        r.stdout = f"{cmd[-1]}\n"
    elif "--name-status" in cmd:
        r.stdout = "M\tapp.py\n"
    elif "--unified=3" in cmd:
        r.stdout = _DIFF
    else:
        r.stdout = ""
    return r


def _make_diff(path: str) -> str:
    """Build a one-hunk unified diff adding one line to `path` (fake-runner fixture)."""
    return (
        f"diff --git a/{path} b/{path}\n"
        "index 1111111..2222222 100644\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        "@@ -1,2 +1,3 @@\n"
        " import os\n"
        "+os.system(cmd)\n"
        " print('hi')\n"
    )


def _make_fake_run(path: str, diff: str):
    """Fake-runner factory for a single-file diff at an arbitrary path (fixture)."""

    def fake(cmd, capture_output, text, check):
        class R:
            returncode = 0

        r = R()
        if "--verify" in cmd:
            r.stdout = f"{cmd[-1]}\n"
        elif "--name-status" in cmd:
            r.stdout = f"M\t{path}\n"
        elif "--unified=3" in cmd:
            r.stdout = diff
        else:
            r.stdout = ""
        return r

    return fake


class _FakeFinding:
    def __init__(self, file: str, line: int, evidence: str = "os.system(cmd)"):
        self.id = "F-1"
        self.file = file
        self.line = line
        self.evidence = evidence


class _ReflectionFinding:
    def __init__(self, id: str, line: int, rule_id: str, cls: str):
        self.id = id
        self.line = line
        self.rule_id = rule_id
        self.cls = cls


def test_review_one_changed_file_exits_zero_and_seals_complete(tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run)
    rc = main(["review", "--base", _BASE_SHA, "--head", _HEAD_SHA, "--root", str(tmp_path)])
    assert rc == 0

    manifest_path = tmp_path / "artifacts" / "coverage_manifest.json"
    data = json.loads(manifest_path.read_text())
    assert data["base_sha"] == _BASE_SHA
    assert data["head_sha"] == _HEAD_SHA
    assert data["seal"] == "complete"
    assert len(data["files"]) == 1
    assert data["files"][0]["state"] == "done"


def test_validate_ref_accepts_sha_and_rejects_leading_dash():
    assert validate_ref(_BASE_SHA) == _BASE_SHA
    try:
        validate_ref("-rf")
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "-rf" in str(exc)


def test_parse_hunks_and_added_line_numbers():
    hunks = parse_hunks(_DIFF)
    assert len(hunks) == 1
    assert added_line_numbers(hunks) == {2}


def test_resolve_position_exact_for_added_line():
    hunks_by_path = {"app.py": parse_hunks(_DIFF)}
    result = resolve_position("app.py", 2, "os.system(cmd)", hunks_by_path, {})
    assert result.decision == "exact"


def test_review_position_gate_keeps_finding_on_added_line():
    hunks_by_path = {"app.py": parse_hunks(_DIFF)}
    finding = _FakeFinding("app.py", 2)
    kept, dropped, declines = review_position_gate([finding], hunks_by_path)
    assert kept == [finding]
    assert dropped == []
    assert declines == []


def test_changed_file_records_parses_name_status():
    class R:
        stdout = "M\tapp.py\n"
        returncode = 0

    def fake(cmd, capture_output, text, check):
        assert "--name-status" in cmd
        return R()

    records = changed_file_records(_BASE_SHA, _HEAD_SHA, runner=fake)
    assert len(records) == 1
    assert records[0].path == "app.py"
    assert records[0].status == "M"


def test_review_python_file_resolves_python_rule_doc(tmp_path, monkeypatch):
    path = "src/App/Handler.PY"
    monkeypatch.setattr(subprocess, "run", _make_fake_run(path, _make_diff(path)))
    rc = run_review(_BASE_SHA, _HEAD_SHA, str(tmp_path), profile="security")
    assert rc == 0

    ledger = json.loads((tmp_path / "artifacts" / "review_ledger.json").read_text())
    expected_text = (rule_glob.builtin_rule_docs_dir() / "python.md").read_text()
    assert ledger["rule_docs"] == [{"path": path, "text": expected_text}]


def test_review_unmatched_file_resolves_default_rule_doc(tmp_path, monkeypatch):
    path = "docs/notes.rst"
    monkeypatch.setattr(subprocess, "run", _make_fake_run(path, _make_diff(path)))
    rc = run_review(_BASE_SHA, _HEAD_SHA, str(tmp_path), profile="security")
    assert rc == 0

    ledger = json.loads((tmp_path / "artifacts" / "review_ledger.json").read_text())
    expected_text = (rule_glob.builtin_rule_docs_dir() / "default.md").read_text()
    assert ledger["rule_docs"] == [{"path": path, "text": expected_text}]


def test_expand_braces_expands_only_first_group():
    assert rule_glob.expand_braces("**/*.{ts,js,tsx}") == ["**/*.ts", "**/*.js", "**/*.tsx"]
    assert rule_glob.expand_braces("*.py") == ["*.py"]
    assert rule_glob.expand_braces("a{b,c}d{e,f}") == ["abd{e,f}", "acd{e,f}"]


def test_glob_match_is_recursive_aware_and_case_insensitive():
    assert rule_glob.glob_match("**/*.py", "a/b/c/handler.py")
    assert not rule_glob.glob_match("*.py", "a/b/handler.py")
    assert rule_glob.glob_match("**/*.PY", "a/handler.py")


def test_resolve_rule_doc_first_matching_entry_wins(monkeypatch):
    monkeypatch.setattr(
        rule_glob, "BUILTIN_PATH_RULE_MAP", {"**/*.py": "python.md", "**/*.*": "default.md"}
    )
    expected_text = (rule_glob.builtin_rule_docs_dir() / "python.md").read_text()
    assert rule_glob.resolve_rule_doc("a/b.py") == expected_text


def test_apply_verdict_retracts_only_the_submitted_id():
    findings = [_ReflectionFinding("F-1", 2, "R1", "xss")]
    kept, retractions = reflection.apply_verdict(findings, {"F-1": "sanitized upstream"}, path="app.py")
    assert kept == []
    assert len(retractions) == 1
    assert retractions[0].path == "app.py"
    assert retractions[0].line == 2
    assert retractions[0].rule_id == "R1"
    assert retractions[0].reason == reflection.RETRACTED_REASON


def test_apply_verdict_ignores_an_id_never_submitted():
    findings = [_ReflectionFinding("F-1", 2, "R1", "xss")]
    kept, retractions = reflection.apply_verdict(findings, {"F-2": "sanitized upstream"}, path="app.py")
    assert kept == findings
    assert retractions == []


def test_apply_verdict_never_retracts_a_protected_subject_class():
    protected_cls = next(iter(reflection.PROTECTED_SUBJECT_CLASSES))
    findings = [_ReflectionFinding("F-1", 2, "R1", protected_cls)]
    kept, retractions = reflection.apply_verdict(findings, {"F-1": "sanitized upstream"}, path="app.py")
    assert kept == findings
    assert retractions == []


def test_review_zero_findings_still_renders_reflection_sections(tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run)
    rc = main(["review", "--base", _BASE_SHA, "--head", _HEAD_SHA, "--root", str(tmp_path)])
    assert rc == 0

    ledger = json.loads((tmp_path / "artifacts" / "review_ledger.json").read_text())
    assert ledger["reflection_retractions"] == []
    assert ledger["reflection_skipped"] == []
    report_text = (tmp_path / "report.md").read_text()
    assert "## Reflection retractions" in report_text
