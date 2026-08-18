"""Tests for the four-layer rule resolver, the exclude filter, and the safety gate.

RULE-02: per-path layer fallthrough (custom > project > global > built-in) and
whole-layer first-non-empty file-filter selection are two structurally different
algorithms, tested separately here so they cannot collapse into one wrong one.
RULE-03: the rule-file safety gate (symlink resolution, extension allowlist,
repo-root containment, 512 KB cap). RULE-04: merge_system_rule concatenation.
"""

from __future__ import annotations

import json
import subprocess

from sec_overlay import rule_glob
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
    assert layer.entries[0].rule == "A text"
    resolution = RuleResolution(layers=[layer, None, None], file_filter=None, repo_root=tmp_path)
    assert resolve_rule_doc("x.py", resolution) == "A text"


def test_resolve_rule_doc_idempotent_across_repeated_calls(tmp_path):
    custom = ProjectRule([_entry("**/*.py", "stable text")], [], [])
    resolution = RuleResolution(layers=[custom, None, None], file_filter=None, repo_root=tmp_path)
    first = resolve_rule_doc("a.py", resolution)
    second = resolve_rule_doc("a.py", resolution)
    assert first == second == "stable text"
    assert resolution.layers[0].entries[0].rule == "stable text"


def test_load_project_rule_returns_none_when_file_absent(tmp_path):
    assert rule_glob.load_project_rule(tmp_path / "missing.json", tmp_path) is None


def test_match_project_rule_entry_returns_none_for_none_layer():
    assert rule_glob.match_project_rule_entry(None, "a.py") is None
