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


def test_dependency_catalog_is_a_tier_two_receipt():
    from sec_overlay.evidence import TIER1_RECEIPTS, TIER2_RECEIPTS, is_tool_receipt, receipt_tier

    assert "dependency-catalog" in TIER2_RECEIPTS
    assert "dependency-catalog" not in TIER1_RECEIPTS
    assert is_tool_receipt("dependency-catalog:opa-rego-http-send")
    assert receipt_tier("dependency-catalog:opa-rego-http-send") == 2


def test_dependency_catalog_alone_cannot_confirm():
    """A manifest match proves the dependency is declared, not that the sink is reached."""
    from sec_overlay.evidence import confirms_alone

    assert confirms_alone(["dependency-catalog:opa-rego-http-send"]) is False
    assert confirms_alone(["dependency-catalog:opa-rego-http-send",
                           "semgrep:sec-overlay.absence.go-rego-new-missing-capabilities"]) is True


def test_validate_dependency_catalog_receipt_accepts_valid_entry():
    from sec_overlay.evidence import validate_dependency_catalog_receipt
    catalog_ids = frozenset({"opa-rego-http-send", "jinja2-sandbox-escape"})
    assert validate_dependency_catalog_receipt(
        "dependency-catalog:opa-rego-http-send", catalog_ids=catalog_ids) is None
    assert validate_dependency_catalog_receipt(
        "dependency-catalog:opa-rego-http-send@1.0.0", catalog_ids=catalog_ids) is None


def test_validate_dependency_catalog_receipt_rejects_unknown_entry():
    from sec_overlay.evidence import validate_dependency_catalog_receipt
    err = validate_dependency_catalog_receipt(
        "dependency-catalog:nonexistent-id", catalog_ids=frozenset({"real-id"}))
    assert err is not None
    assert "nonexistent-id" in err


def test_validate_dependency_catalog_receipt_rejects_non_catalog_source():
    from sec_overlay.evidence import validate_dependency_catalog_receipt
    err = validate_dependency_catalog_receipt(
        "semgrep:rule-x", catalog_ids=frozenset({"real-id"}))
    assert err is not None
    assert "not a dependency-catalog receipt" in err
