"""Evidence grading: mechanical tool receipts outrank LLM assertions.

A finding's confidence is the strongest evidence in its chain: a real tool
receipt (semgrep/codeql/ast-grep/tree-sitter/ripgrep) yields HIGH; an LLM
assertion corroborated by nothing yields LOW. LLM-asserted evidence is
namespaced ``llm-claimed:`` so it can never be counted as a tool receipt.
Adapted from raptor's evidence_grade.
"""

from __future__ import annotations

from enum import Enum

TIER1_RECEIPTS = frozenset({"codeql", "semgrep", "sca", "secrets"})
# Tier 2 locates a sink; it never confirms alone. `dependency-catalog` proves a
# dependency is declared and names the sink inside it, which is location, not reach.
TIER2_RECEIPTS = frozenset({"ripgrep", "structural-index", "ast-grep", "tree-sitter",
                             "dependency-catalog"})
SHIPPING_STATUSES = frozenset({"confirmed", "fixed", "needs-deployment-testing"})
RUNTIME_DISPOSITIONS = frozenset({"needs-runtime", "static-settled", "unassessed"})
VERIFICATION_VALUES = frozenset(
    {"verified-static", "static-only", "not-fixed", "verify-error"}
)

# `prove.py`'s reproduction receipt: a real tool receipt (the harness drove a live
# entrypoint) that names no tier prefix, because it proves by execution, not by
# static match. Defined here — not in `prove.py` — so `unknown_receipts` below has
# one place to check it without `evidence.py` importing `prove.py` (which imports
# `workspace.py`, which imports this module; that path would be circular).
# `prove.py` imports both names from here to keep a single definition.
REPRODUCTION_RECEIPT = "reproduction"

_MECHANICAL = TIER1_RECEIPTS | TIER2_RECEIPTS


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


def is_reproduction_receipt(source: str) -> bool:
    """Report whether an evidence source is a reproduction receipt.

    Args:
        source: One entry of a finding's ``evidence_sources``.

    Returns:
        True for ``reproduction`` and for its colon form ``reproduction:<tool>``.

    Example:
        >>> is_reproduction_receipt("reproduction")
        True
    """
    return source == REPRODUCTION_RECEIPT or source.startswith(REPRODUCTION_RECEIPT + ":")


def unknown_receipts(sources: list[str]) -> list[str]:
    """Return the sources that claim a receipt prefix outside the closed set.

    An ``llm``-namespaced source claims no receipt and never appears here. A
    reproduction receipt (``prove.py``) is a genuine receipt outside both tiers —
    it proves by execution, not by static match — so it is exempt too. Every
    other source names a tool, so a prefix in neither receipt tier is a contract
    violation — a typo or an undeclared tool — not a source with no tier. Callers
    report the result; this function raises nothing, because ``receipt_tier`` runs
    inside comprehensions that an exception would abort.

    Args:
        sources: Evidence source strings, each ``<prefix>:<detail>`` or a bare prefix.

    Returns:
        The offending sources, in input order. Empty when every source is declared.

    Example:
        >>> unknown_receipts(["semgrp:a.py:1", "llm-claimed:reasoning"])
        ['semgrp:a.py:1']
    """
    return [
        s
        for s in sources
        if not s.startswith(("llm-claimed:", "llm"))
        and not is_reproduction_receipt(s)
        and s.split(":", 1)[0] not in _MECHANICAL
    ]


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
