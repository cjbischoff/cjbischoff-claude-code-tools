"""Evidence grading: mechanical tool receipts outrank LLM assertions.

A finding's confidence is the strongest evidence in its chain: a real tool
receipt (semgrep/codeql/ast-grep/tree-sitter/ripgrep) yields HIGH; an LLM
assertion corroborated by nothing yields LOW. LLM-asserted evidence is
namespaced ``llm-claimed:`` so it can never be counted as a tool receipt.
Adapted from raptor's evidence_grade.
"""

from __future__ import annotations

from enum import Enum

_MECHANICAL = {"semgrep", "codeql", "ast-grep", "tree-sitter", "ripgrep",
               "structural-index", "secrets", "sca"}

TIER1_RECEIPTS = frozenset({"codeql", "semgrep", "sca", "secrets"})
TIER2_RECEIPTS = frozenset({"ripgrep", "structural-index", "ast-grep", "tree-sitter"})
SHIPPING_STATUSES = frozenset({"confirmed", "fixed", "needs-deployment-testing"})
RUNTIME_DISPOSITIONS = frozenset({"needs-runtime", "static-settled", "unassessed"})

assert TIER1_RECEIPTS | TIER2_RECEIPTS == _MECHANICAL, "receipt tiers must partition _MECHANICAL"


class Confidence(str, Enum):
    """Confidence tier for a finding, from its strongest evidence."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


def is_tool_receipt(source: str) -> bool:
    """Return True if ``source`` is a genuine mechanical-tool receipt.

    Args:
        source: An evidence source string (e.g. ``codeql:dataflow``).

    Returns:
        True only for mechanical-tool sources not namespaced ``llm-claimed:``.
    """
    if source.startswith(("llm-claimed:", "llm")):
        return False
    return source.split(":", 1)[0] in _MECHANICAL


def as_llm_claim(source: str) -> str:
    """Namespace an LLM-asserted source so it cannot masquerade as a receipt.

    Args:
        source: The raw source the LLM claims.

    Returns:
        The source unchanged if already ``llm``-prefixed, else ``llm-claimed:<source>``.
    """
    return source if source.startswith("llm") else f"llm-claimed:{source}"


def receipt_tier(source: str) -> int | None:
    """Return the receipt tier (1 or 2) of an evidence source, or None.

    Tier 1 sources confirm a finding alone (a dataflow path, a vulnerable
    version, a live secret). Tier 2 sources only locate code. An LLM-claimed
    or unknown source has no tier.

    Args:
        source: An evidence source string (e.g. ``codeql:dataflow``).

    Returns:
        ``1`` for a Tier-1 receipt, ``2`` for a Tier-2 receipt, ``None`` for
        an ``llm-claimed:*`` or non-mechanical source.
    """
    if not is_tool_receipt(source):
        return None
    head = source.split(":", 1)[0]
    if head in TIER1_RECEIPTS:
        return 1
    return 2


def confirms_alone(sources: list[str]) -> bool:
    """Return True iff at least one source is a Tier-1 receipt.

    Args:
        sources: Evidence source strings.

    Returns:
        True when a Tier-1 receipt is present — the only ground on which a
        finding may reach ``confirmed``/``fixed``.
    """
    return any(receipt_tier(s) == 1 for s in sources)


def confidence_for(sources: list[str]) -> Confidence:
    """Grade a finding's confidence from its evidence sources (strongest link).

    Args:
        sources: Evidence source strings.

    Returns:
        HIGH if any real tool receipt; else MEDIUM if any ``llm-corroborated``;
        else LOW.
    """
    if any(is_tool_receipt(s) for s in sources):
        return Confidence.HIGH
    if any(s == "llm-corroborated" or s.startswith("llm-corroborated") for s in sources):
        return Confidence.MEDIUM
    return Confidence.LOW
