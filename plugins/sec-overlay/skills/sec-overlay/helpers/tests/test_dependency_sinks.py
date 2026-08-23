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
