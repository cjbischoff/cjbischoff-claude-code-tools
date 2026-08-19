"""Tests for the four-layer rule resolver, the exclude filter, and the safety gate.

RULE-02: per-path layer fallthrough (custom > project > global > built-in) and
whole-layer first-non-empty file-filter selection are two structurally different
algorithms, tested separately here so they cannot collapse into one wrong one.
RULE-03: the rule-file safety gate (symlink resolution, extension allowlist,
repo-root containment, 512 KB cap). RULE-04: merge_system_rule concatenation.
"""

from __future__ import annotations

import json

import pytest

from sec_overlay import rule_glob
from sec_overlay.repo_memory import RepoMemory
from sec_overlay.rule_glob import (
    ProjectRule,
    ProjectRuleEntry,
    RuleResolution,
    merge_with_system_rule,
    resolve_rule_doc,
)


def _entry(path: str, rule: str, merge: bool = False) -> ProjectRuleEntry:
    return ProjectRuleEntry(path=path, rule=rule, merge_system_rule=merge)


# --- Task 1: per-path layer fallthrough + merge_system_rule ---------------------


def test_resolve_rule_doc_custom_layer_wins_over_project_layer(tmp_path):
    custom = ProjectRule([_entry("**/*.py", "custom text")], [], [])
    project = ProjectRule([_entry("**/*.py", "project text")], [], [])
    resolution = RuleResolution(layers=[custom, project, None], file_filter=None, repo_root=tmp_path)
    assert resolve_rule_doc("src/a.py", resolution) == "custom text"


def test_resolve_rule_doc_global_layer_only_match(tmp_path):
    global_layer = ProjectRule([_entry("**/*.py", "global text")], [], [])
    resolution = RuleResolution(layers=[None, None, global_layer], file_filter=None, repo_root=tmp_path)
    assert resolve_rule_doc("src/a.py", resolution) == "global text"


def test_resolve_rule_doc_falls_through_to_builtin_when_no_layer_matches(tmp_path, monkeypatch):
    monkeypatch.setattr(rule_glob, "BUILTIN_PATH_RULE_MAP", {"**/*.py": "python.md"})
    unrelated = ProjectRule([_entry("**/*.rb", "ruby text")], [], [])
    resolution = RuleResolution(layers=[unrelated, None, None], file_filter=None, repo_root=tmp_path)
    expected = (rule_glob.builtin_rule_docs_dir() / "python.md").read_text()
    assert resolve_rule_doc("src/a.py", resolution) == expected


def test_resolve_rule_doc_falls_through_to_default_when_all_layers_empty(tmp_path):
    resolution = RuleResolution(layers=[None, None, None], file_filter=None, repo_root=tmp_path)
    expected = (rule_glob.builtin_rule_docs_dir() / "default.md").read_text()
    assert resolve_rule_doc("src/a.unknownext", resolution) == expected


def test_merge_system_rule_entry_returns_system_and_user_headers(tmp_path, monkeypatch):
    monkeypatch.setattr(rule_glob, "BUILTIN_PATH_RULE_MAP", {"**/*.py": "python.md"})
    builtin_text = (rule_glob.builtin_rule_docs_dir() / "python.md").read_text()
    custom = ProjectRule([_entry("**/*.py", "user text", merge=True)], [], [])
    resolution = RuleResolution(layers=[custom, None, None], file_filter=None, repo_root=tmp_path)
    result = resolve_rule_doc("a.py", resolution)
    assert result == merge_with_system_rule(builtin_text, "user text")
    assert rule_glob.SYSTEM_RULE_HEADER in result
    assert rule_glob.USER_RULE_HEADER in result
    assert result.index(rule_glob.SYSTEM_RULE_HEADER) < result.index(rule_glob.USER_RULE_HEADER)


def test_merge_with_system_rule_empty_cases():
    assert merge_with_system_rule("", "user") == "user"
    assert merge_with_system_rule("builtin", "") == "builtin"
    assert merge_with_system_rule("", "") == ""


def test_load_project_rule_preserves_json_array_order_first_match_wins(tmp_path):
    (tmp_path / "a.md").write_text("A text")
    (tmp_path / "b.md").write_text("B text")
    rule_json = tmp_path / "rule.json"
    rule_json.write_text(
        json.dumps(
            {
                "rules": [
                    {"path": "**/*.py", "rule": "a.md"},
                    {"path": "**/*.py", "rule": "b.md"},
                ]
            }
        )
    )
    layer = rule_glob.load_project_rule(rule_json, tmp_path)
    assert layer is not None
    assert layer.entries[0].rule == "A text"
    resolution = RuleResolution(layers=[layer, None, None], file_filter=None, repo_root=tmp_path)
    assert resolve_rule_doc("x.py", resolution) == "A text"


def test_resolve_rule_doc_idempotent_across_repeated_calls(tmp_path):
    custom = ProjectRule([_entry("**/*.py", "stable text")], [], [])
    resolution = RuleResolution(layers=[custom, None, None], file_filter=None, repo_root=tmp_path)
    first = resolve_rule_doc("a.py", resolution)
    second = resolve_rule_doc("a.py", resolution)
    assert first == second == "stable text"
    stable_layer = resolution.layers[0]
    assert stable_layer is not None
    assert stable_layer.entries[0].rule == "stable text"


def test_load_project_rule_returns_none_when_file_absent(tmp_path):
    assert rule_glob.load_project_rule(tmp_path / "missing.json", tmp_path) is None


def test_match_project_rule_entry_returns_none_for_none_layer():
    assert rule_glob.match_project_rule_entry(None, "a.py") is None


# --- Task 2: whole-layer first-non-empty file filter + --rule/--exclude -----------------


def _review_runner(paths: list[str]):
    """Fake ``runner`` answering rev-parse/name-status/unified diff for ``paths``.

    Duplicated from ``test_cli.py``'s ``_make_review_runner`` (not imported) so this
    file stays a self-contained fixture of the resolver + CLI wiring it tests.
    """

    class _FakeResult:
        def __init__(self, stdout="", returncode=0):
            self.stdout = stdout
            self.returncode = returncode

    def runner(cmd, capture_output, text, check):
        if cmd[1] == "rev-parse":
            return _FakeResult(f"sha-{cmd[-1]}\n")
        if cmd[1] == "diff" and "--name-status" in cmd:
            return _FakeResult("".join(f"M\t{p}\n" for p in paths))
        if cmd[1] == "diff" and "--unified=3" in cmd:
            path = cmd[-1]
            return _FakeResult(f"diff --git a/{path} b/{path}\n@@ -1 +1 @@\n-old\n+new\n")
        return _FakeResult("")

    return runner


def test_build_file_filter_skips_empty_layer_and_uses_first_non_empty():
    empty = ProjectRule([], [], [])
    project = ProjectRule([], [], ["vendor/**"])
    result = rule_glob.build_file_filter([empty, project])
    assert result is not None
    assert result.exclude == ["vendor/**"]
    assert result.include == []


def test_build_file_filter_does_not_merge_across_layers():
    custom = ProjectRule([], [], ["a/**"])
    project = ProjectRule([], [], ["b/**"])
    result = rule_glob.build_file_filter([custom, project])
    assert result is not None
    assert result.exclude == ["a/**"]


def test_build_file_filter_returns_none_when_all_layers_empty():
    assert rule_glob.build_file_filter([ProjectRule([], [], []), None]) is None
    assert rule_glob.build_file_filter([]) is None


def test_build_file_filter_lower_cases_patterns_at_build_time():
    layer = ProjectRule([], [], ["VENDOR/**"])
    result = rule_glob.build_file_filter([layer])
    assert result is not None
    assert result.exclude == ["vendor/**"]
    assert rule_glob.glob_match(result.exclude[0], "vendor/lib.py")


def test_build_resolution_appends_cli_excludes_to_layer_filter(tmp_path):
    project_dir = tmp_path / ".sec-overlay"
    project_dir.mkdir()
    (project_dir / "rule.json").write_text(json.dumps({"rules": [], "exclude": ["a/**"]}))
    resolution = rule_glob.build_resolution(None, ["VENDOR/**"], tmp_path)
    assert resolution.file_filter is not None
    assert resolution.file_filter.exclude == ["a/**", "vendor/**"]


def test_build_resolution_excludes_only_filter_when_no_layer_has_one(tmp_path):
    resolution = rule_glob.build_resolution(None, ["vendor/**"], tmp_path)
    assert resolution.file_filter is not None
    assert resolution.file_filter.exclude == ["vendor/**"]
    assert resolution.file_filter.include == []


def test_build_resolution_resolves_custom_and_global_rule_paths_against_their_own_dir(
    tmp_path, monkeypatch
):
    # OCR's loadRuleFile/loadGlobalRule resolve a relative `rule` field against the
    # rule.json's OWN directory, not repo_root — unlike the project layer, which
    # resolves against repo_root (system_rules.go loadProjectRule/loadRuleFile).
    custom_dir = tmp_path / "custom"
    custom_dir.mkdir()
    (custom_dir / "text.md").write_text("custom text")
    custom_rule_json = custom_dir / "custom-rule.json"
    custom_rule_json.write_text(
        json.dumps({"rules": [{"path": "**/*.py", "rule": "text.md"}]})
    )

    global_dir = tmp_path / "home" / ".sec-overlay"
    global_dir.mkdir(parents=True)
    (global_dir / "text.md").write_text("global text")
    (global_dir / "rule.json").write_text(
        json.dumps({"rules": [{"path": "**/*.rb", "rule": "text.md"}]})
    )
    monkeypatch.setattr(rule_glob, "_global_rule_path", lambda: global_dir / "rule.json")

    resolution = rule_glob.build_resolution(str(custom_rule_json), [], tmp_path)
    custom_layer = resolution.layers[0]
    global_layer = resolution.layers[2]
    assert custom_layer is not None
    assert global_layer is not None
    assert custom_layer.entries[0].rule == "custom text"
    assert global_layer.entries[0].rule == "global text"


def test_review_cli_parses_rule_and_exclude_and_reaches_run_review(tmp_path, monkeypatch):
    from sec_overlay import cli

    captured = {}

    def fake_run_review(base, head, root, *, profile="security", rule_path=None,
                         excludes=None, runner=None, prepare=False):
        captured["rule_path"] = rule_path
        captured["excludes"] = excludes
        return 0

    monkeypatch.setattr(cli, "run_review", fake_run_review)
    rule_file = tmp_path / "custom-rule.json"
    rule_file.write_text(json.dumps({"rules": []}))
    rc = cli.main([
        "review", "--base", "main", "--head", "HEAD", "--root", str(tmp_path),
        "--rule", str(rule_file), "--exclude", "a", "--exclude", "b",
    ])
    assert rc == 0
    assert captured["rule_path"] == str(rule_file)
    assert captured["excludes"] == ["a", "b"]


def test_run_review_excludes_filtered_files_from_reviewable_set(tmp_path):
    from sec_overlay import cli

    runner = _review_runner(["vendor/lib.py", "src/a.py"])
    rc = cli.run_review(
        "main", "develop", str(tmp_path), excludes=["vendor/**"], runner=runner
    )
    assert rc == 0
    ws = RepoMemory.for_target(str(tmp_path), runner=runner).workspace
    manifest = json.loads((ws.artifacts / "coverage_manifest.json").read_text())
    paths = [f["path"] for f in manifest["files"]]
    assert "src/a.py" in paths
    assert "vendor/lib.py" not in paths


# --- Task 3: rule-file safety gate (RULE-03) --------------------------------------


def test_rule_safety_gate_accepts_cap_rejects_one_byte_over(tmp_path):
    ok_file = tmp_path / "ok.md"
    ok_file.write_bytes(b"a" * rule_glob.MAX_RULE_FILE_BYTES)
    assert rule_glob.read_rule_file_safe(ok_file, tmp_path) == "a" * rule_glob.MAX_RULE_FILE_BYTES

    big_file = tmp_path / "big.md"
    big_file.write_bytes(b"a" * (rule_glob.MAX_RULE_FILE_BYTES + 1))
    with pytest.raises(rule_glob.RuleSafetyError) as exc_info:
        rule_glob.read_rule_file_safe(big_file, tmp_path)
    message = str(exc_info.value)
    assert str(big_file.resolve()) in message
    assert str(rule_glob.MAX_RULE_FILE_BYTES) in message
    assert str(rule_glob.MAX_RULE_FILE_BYTES + 1) in message


def test_rule_safety_gate_rejects_symlink_escaping_repo_root(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("secret")
    link = repo / "link.md"
    link.symlink_to(outside)

    with pytest.raises(rule_glob.RuleSafetyError) as exc_info:
        rule_glob.read_rule_file_safe(link, repo)
    assert str(outside.resolve()) in str(exc_info.value)


def test_rule_safety_gate_rejects_disallowed_extension_on_resolved_path(tmp_path):
    yaml_file = tmp_path / "rule.yaml"
    yaml_file.write_text("text: value")
    with pytest.raises(rule_glob.RuleSafetyError):
        rule_glob.read_rule_file_safe(yaml_file, tmp_path)

    target = tmp_path / "target.yaml"
    target.write_text("text: value")
    link = tmp_path / "alias.md"
    link.symlink_to(target)
    with pytest.raises(rule_glob.RuleSafetyError):
        rule_glob.read_rule_file_safe(link, tmp_path)


def test_rule_safety_gate_strips_trailing_newlines_preserves_inner_blanks(tmp_path):
    rule_file = tmp_path / "rule.md"
    rule_file.write_text("first\n\nsecond\n\n\n")
    assert rule_glob.read_rule_file_safe(rule_file, tmp_path) == "first\n\nsecond"


def test_rule_safety_gate_measures_size_in_bytes_not_characters(tmp_path):
    # "e-acute" is 1 char but 2 bytes in UTF-8; 300000 chars = 600000 bytes, over cap.
    over_cap_text = "é" * 300000
    over_cap_file = tmp_path / "over.md"
    over_cap_file.write_text(over_cap_text, encoding="utf-8")
    with pytest.raises(rule_glob.RuleSafetyError):
        rule_glob.read_rule_file_safe(over_cap_file, tmp_path)

    under_cap_text = "é" * 100
    under_cap_file = tmp_path / "under.md"
    under_cap_file.write_text(under_cap_text, encoding="utf-8")
    assert rule_glob.read_rule_file_safe(under_cap_file, tmp_path) == under_cap_text


def test_run_review_exits_2_on_rule_safety_error_with_no_fallback(tmp_path, capsys):
    from sec_overlay import cli

    project_dir = tmp_path / ".sec-overlay"
    project_dir.mkdir()
    bad_rule = tmp_path / "bad.yaml"
    bad_rule.write_text("nope")
    (project_dir / "rule.json").write_text(
        json.dumps({"rules": [{"path": "**/*.py", "rule": str(bad_rule)}]})
    )
    runner = _review_runner(["src/a.py"])

    rc = cli.run_review("main", "develop", str(tmp_path), runner=runner)

    assert rc == 2
    captured = capsys.readouterr()
    assert str(bad_rule.resolve()) in captured.err
    ws = RepoMemory.for_target(str(tmp_path), runner=runner).workspace
    assert not (ws.artifacts / "coverage_manifest.json").exists()
