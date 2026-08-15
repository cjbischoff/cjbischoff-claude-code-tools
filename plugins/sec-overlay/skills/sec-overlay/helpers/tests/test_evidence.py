"""Tests for evidence grading + tool-vs-LLM receipt distinction."""

from sec_overlay.evidence import (
    _MECHANICAL,
    RUNTIME_DISPOSITIONS,
    SHIPPING_STATUSES,
    TIER1_RECEIPTS,
    TIER2_RECEIPTS,
    Confidence,
    as_llm_claim,
    confidence_for,
    confirms_alone,
    is_tool_receipt,
    receipt_tier,
)


def test_is_tool_receipt():
    assert is_tool_receipt("codeql:dataflow") is True
    assert is_tool_receipt("ast-grep:sink") is True
    assert is_tool_receipt("structural-index:callers") is True
    assert is_tool_receipt("llm-claimed:codeql") is False   # cannot masquerade
    assert is_tool_receipt("llm-inferred") is False


def test_as_llm_claim_namespaces():
    assert as_llm_claim("codeql") == "llm-claimed:codeql"
    assert as_llm_claim("llm-inferred") == "llm-inferred"    # already llm-prefixed


def test_confidence_ladder():
    assert confidence_for(["codeql:dataflow", "llm-inferred"]) is Confidence.HIGH
    assert confidence_for(["llm-corroborated"]) is Confidence.MEDIUM
    assert confidence_for(["llm-inferred"]) is Confidence.LOW
    assert confidence_for([]) is Confidence.LOW


def test_tiers_partition_mechanical_exactly():
    assert TIER1_RECEIPTS | TIER2_RECEIPTS == _MECHANICAL
    assert TIER1_RECEIPTS.isdisjoint(TIER2_RECEIPTS)


def test_receipt_tier_grades_colon_forms():
    assert receipt_tier("codeql:dataflow") == 1
    assert receipt_tier("semgrep:rule-x") == 1
    assert receipt_tier("ripgrep") == 2
    assert receipt_tier("ast-grep:pattern") == 2
    assert receipt_tier("llm-claimed:codeql") is None
    assert receipt_tier("nonsense") is None


def test_confirms_alone_requires_tier1():
    assert confirms_alone(["codeql:dataflow"]) is True
    assert confirms_alone(["ripgrep", "structural-index"]) is False
    assert confirms_alone(["ripgrep", "semgrep:x"]) is True
    assert confirms_alone(["llm-claimed:codeql"]) is False


def test_shipping_and_disposition_sets():
    assert SHIPPING_STATUSES == {"confirmed", "fixed", "needs-deployment-testing"}
    assert RUNTIME_DISPOSITIONS == {"needs-runtime", "static-settled", "unassessed"}
