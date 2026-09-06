from __future__ import annotations

import json
from pathlib import Path

import pytest

from sec_overlay.dependency_sinks import (
    CATALOG_PATH,
    SinkEntry,
    catalog_ids,
    load_catalog,
    match_manifests,
    matched_classes,
    validate_catalog,
)


def test_shipped_catalog_loads_and_validates():
    raw = json.loads(CATALOG_PATH.read_text())
    assert validate_catalog(raw) == []
    entries = load_catalog()
    assert entries, "shipped catalog must not be empty"
    assert all(isinstance(e, SinkEntry) for e in entries)


def test_shipped_catalog_covers_the_opa_rego_case():
    """The gap this feature closes: OPA's own code holds the outbound-request sink."""
    entry = next(e for e in load_catalog() if e.id == "opa-rego-http-send")
    assert entry.cls == "ssrf"
    assert entry.package == "github.com/open-policy-agent/opa"
    assert "go.mod" in entry.manifests
    assert entry.sink == "http.send"
    assert entry.safe_option


def test_catalog_ids_are_unique():
    ids = [e.id for e in load_catalog()]
    assert len(ids) == len(set(ids))
    assert catalog_ids() == frozenset(ids)


@pytest.mark.parametrize(
    ("raw", "fragment"),
    [
        ({"version": 1}, "entries"),
        ({"version": 1, "entries": [{"id": "x"}]}, "package"),
        (
            {
                "version": 1,
                "entries": [
                    {
                        "id": "dup",
                        "package": "p",
                        "ecosystem": "go",
                        "manifests": ["go.mod"],
                        "cls": "ssrf",
                        "sink": "s",
                        "why": "w",
                        "safe_option": "o",
                        "indicators": ["i"],
                    }
                ]
                * 2,
            },
            "duplicate",
        ),
    ],
)
def test_validate_catalog_reports_defects(raw, fragment):
    errors = validate_catalog(raw)
    assert any(fragment in e for e in errors), errors


_DEP_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "dep_sink_repo"


def test_match_manifests_finds_the_declared_opa_dependency():
    matched = match_manifests(_DEP_FIXTURE)
    assert [e.id for e in matched] == ["opa-rego-http-send"]


def test_matched_classes_returns_sorted_unique_classes():
    assert matched_classes(_DEP_FIXTURE) == ["ssrf"]


def test_match_manifests_ignores_a_repo_with_no_catalogued_dependency(tmp_path):
    (tmp_path / "go.mod").write_text("module example.com/x\n\ngo 1.22\n")
    assert match_manifests(tmp_path) == []


def test_match_manifests_skips_vendor_and_node_modules(tmp_path):
    vendored = tmp_path / "node_modules" / "pkg"
    vendored.mkdir(parents=True)
    (vendored / "go.mod").write_text("require github.com/open-policy-agent/opa v0.68.0\n")
    assert match_manifests(tmp_path) == []


def test_indicator_classes_routes_without_a_manifest(tmp_path):
    """A Bazel or vendored target has no manifest but still calls the sink (REQ-25)."""
    from sec_overlay.dependency_sinks import indicator_classes, match_manifests

    (tmp_path / "policy.go").write_text(
        "package main\n\nfunc run() { r := rego.New(rego.Query(\"x\")) ; _ = r }\n"
    )
    assert match_manifests(tmp_path) == []
    assert "ssrf" in indicator_classes(tmp_path)


def test_indicator_classes_is_empty_without_an_indicator(tmp_path):
    """No indicator in source means no extra routing (REQ-25)."""
    from sec_overlay.dependency_sinks import indicator_classes

    (tmp_path / "main.go").write_text("package main\n\nfunc main() {}\n")
    assert indicator_classes(tmp_path) == []


def test_validate_catalog_accepts_match_any_strategy_without_package():
    from sec_overlay.dependency_sinks import validate_catalog
    raw = {
        "entries": [{
            "id": "test-entry", "ecosystem": "npm", "manifests": ["package.json"],
            "strategy": "match-any", "cls": "ssti", "sink": "test sink",
            "why": "test", "safe_option": "none", "indicators": [".template("],
        }]
    }
    assert validate_catalog(raw) == []


def test_validate_catalog_rejects_invalid_strategy():
    from sec_overlay.dependency_sinks import validate_catalog
    raw = {
        "entries": [{
            "id": "test-entry", "package": "dot", "ecosystem": "npm",
            "manifests": ["package.json"], "strategy": "invalid-strategy",
            "cls": "ssti", "sink": "test", "why": "test",
            "safe_option": "none", "indicators": [".template("],
        }]
    }
    errs = validate_catalog(raw)
    assert any("invalid-strategy" in e for e in errs)


def test_validate_catalog_requires_package_for_package_match():
    from sec_overlay.dependency_sinks import validate_catalog
    raw = {
        "entries": [{
            "id": "test-entry", "ecosystem": "npm", "manifests": ["package.json"],
            "strategy": "package-match", "cls": "ssti", "sink": "test",
            "why": "test", "safe_option": "none", "indicators": [".template("],
        }]
    }
    errs = validate_catalog(raw)
    assert any("package" in e for e in errs)


def test_load_catalog_parses_strategy_field():
    from sec_overlay.dependency_sinks import load_catalog
    entries = load_catalog()
    npm_template = [e for e in entries if e.id == "npm-template-injection"]
    assert len(npm_template) == 1
    assert npm_template[0].strategy == "match-any"
    assert npm_template[0].ecosystem == "npm"
    assert npm_template[0].cls == "ssti"
    # Existing entries without strategy default to package-match
    go_entries = [e for e in entries if e.ecosystem == "go"]
    if go_entries:
        assert go_entries[0].strategy == "package-match"
