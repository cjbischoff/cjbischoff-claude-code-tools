"""REQ-09: a finding's class must be a canonical key; a missing class file is a gap."""

from __future__ import annotations

import pytest

from sec_overlay.clsmap import canonical_classes
from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.workspace import Workspace, write_findings


def _finding(cls: str) -> Finding:
    return Finding(
        id="C-0001",
        rule_id="semgrep:test.rule",
        cls=cls,
        status=FindingStatus.CANDIDATE,
        severity=Severity.LOW,
        file="src/app.py",
        line=1,
        message="test finding",
        evidence_sources=["semgrep:test.rule"],
    )


@pytest.mark.parametrize(
    "key",
    [
        "ssrf",  # universal table
        "xxe",  # universal table
        "oauth-oidc",  # F2 companion table
        "graphql",  # F2 companion table
        "jwt",  # clsmap CWE_CLS
        "excessive-agency",  # clsmap CWE_CLS, absent from the addendum's list
        "business-logic",  # clsmap CWE_CLS, absent from the addendum's list
        "resource",  # clsmap CWE_CLS and _RULE_ID_CLS, absent from the addendum's list
        "security-other",  # clsmap literal return
        "unknown",  # clsmap literal return
        "thread-safety",  # GENERAL_DEFECT_CLASSES, emitted by the review lane
        "null-dereference",  # GENERAL_DEFECT_CLASSES
        "config",  # agents/classes/config.md, published by no table
        "manual-review",  # context.py:303, production
    ],
)
def test_canonical_classes_holds_every_published_key(key):
    assert key in canonical_classes(), f"a publisher emits {key} but the canonical set omits it"


def test_canonical_classes_rejects_an_unpublished_key():
    keys = canonical_classes()
    assert "bogus" not in keys
    assert "README" not in keys  # agents/classes/README.md is not a class


def test_findings_gate_rejects_a_class_outside_the_canonical_set(tmp_path):
    from sec_overlay.findings_gate import validate_findings

    ws = Workspace(root=tmp_path / "ws")
    ws.ensure()
    write_findings(ws, [_finding("bogus")])
    errors = validate_findings(ws)
    assert any("bogus" in e for e in errors), errors


def test_findings_gate_accepts_a_canonical_class_with_no_class_file(tmp_path):
    """``xxe`` is canonical. A missing agents/classes file is a gap, not a rejection."""
    from sec_overlay.findings_gate import validate_findings

    ws = Workspace(root=tmp_path / "ws")
    ws.ensure()
    write_findings(ws, [_finding("xxe")])
    assert not [e for e in validate_findings(ws) if "xxe" in e]


def test_a_missing_class_file_stays_a_gap(tmp_path):
    """REQ-09 is validity, not coverage: class_ext still records, never rejects."""
    from sec_overlay.class_ext import class_extension_status

    out = class_extension_status(["xxe"], tmp_path)
    assert out["gaps"][0]["id"] == "xxe"
    assert out["gaps"][0]["disposition"] == "needs_follow_up"
