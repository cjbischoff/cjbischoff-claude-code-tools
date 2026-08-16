"""Tests for sec_overlay.stage_validate — per-stage output validation routing."""

from __future__ import annotations

import pytest


def test_discovery_ledger_stage_is_validated():
    from sec_overlay.discovery_ledger import new_ledger
    from sec_overlay.stage_validate import validate_stage
    assert validate_stage("discovery-ledger", new_ledger()) == []
    bad = new_ledger(); bad["terminal_reason"] = "nope"
    assert validate_stage("discovery-ledger", bad)


def test_coverage_ledger_stage_is_validated():
    from sec_overlay.stage_validate import validate_stage
    good = {"completeness": "partial", "surfaces": [{"id": "a", "disposition": "reported"}]}
    assert validate_stage("coverage-ledger", good) == []
    bad = {"completeness": "complete", "surfaces": [], "deferred": ["x"]}
    assert validate_stage("coverage-ledger", bad)


def test_context_validator_flags_cited_doc_missing_from_docs_read():
    from sec_overlay.stage_validate import validate_stage
    obj = {"items": [{"kind": "claimed_control", "text": "t", "where": "a.py:1",
                      "source_doc": "SECURITY.md"}],
           "provenance": {"docs_read": [], "docs_discovered": ["SECURITY.md"], "sha": "x"}}
    errs = validate_stage("context", obj)
    assert any("SECURITY.md" in e and "docs_read" in e for e in errs)


def test_context_validator_ok_when_cited_doc_present():
    from sec_overlay.stage_validate import validate_stage
    obj = {"items": [{"kind": "claimed_control", "text": "t", "where": "a.py:1",
                      "source_doc": "SECURITY.md"}],
           "provenance": {"docs_read": ["SECURITY.md"], "docs_discovered": ["SECURITY.md"],
                          "sha": "x"}}
    assert not any("docs_read" in e for e in validate_stage("context", obj))


def test_unknown_stage_raises():
    from sec_overlay.stage_validate import validate_stage
    with pytest.raises(ValueError):
        validate_stage("no-such-stage", {})
