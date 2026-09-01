"""Unified CWE / semgrep-metadata -> attack-class mapping.

Single source of truth so semgrep and CodeQL classify findings identically.
Third-party semgrep rules carry a `cwe` field (not our `cls`); CodeQL carries
`external/cwe/cwe-NNN` tags. Both resolve here. Adapted from raptor's CWE
handling.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

# leading-zero-stripped CWE number -> attack-class key (attack-classes.md keys,
# plus log-injection / clear-text-logging surfaced by CodeQL security-extended).
CWE_CLS: dict[str, str] = {
    "89": "sqli", "78": "cmdi", "918": "ssrf", "22": "path-traversal",
    "285": "authz", "287": "authn", "502": "deserialization", "79": "xss",
    "798": "secrets", "327": "crypto", "1336": "ssti", "611": "xxe",
    "601": "open-redirect", "117": "log-injection", "312": "clear-text-logging",
    # F2: domain-specific classes (see references/hunting/*.md)
    "347": "jwt", "444": "request-smuggling", "1321": "prototype-pollution",
    "1385": "cswsh", "441": "excessive-agency", "384": "authn",
    "840": "business-logic", "639": "authz", "352": "authz",
    # resource-exhaustion / DoS (classes/resource.md) — otherwise these fall to
    # "unknown" and demote_noise silently drops them (dogfood ISSUE-011).
    "400": "resource", "770": "resource", "834": "resource", "674": "resource",
}

_CWE_RE = re.compile(r"cwe-0*(\d+)")

# High-confidence rule-id substrings -> attack-class, for vendored semgrep
# `lang.security.*` rules that carry neither our `cls` field nor a mapped CWE
# (they would otherwise fall to "security-other"/"unknown" and be orphaned from
# the class investigate agents). Keep this list conservative: only rules whose
# name unambiguously names the sink class.
_RULE_ID_CLS: dict[str, str] = {
    # vendored semgrep lang.security.* (no cls/CWE in metadata)
    "exec-use": "cmdi",
    "backticks-use": "cmdi",
    "mcrypt-use": "crypto",
    "weak-crypto": "crypto",
    # CodeQL js/*, py/* rule ids that carry no mapped CWE tag and would otherwise
    # orphan to "unknown" (observed across every JS/TS/Python target). Substring
    # match, so both js/ and py/ variants resolve. Conservative — only rules whose
    # id unambiguously names the class.
    "user-controlled-bypass": "authn",
    "url-substring-sanitization": "ssrf",
    "incomplete-sanitization": "xss",
    "reflected-xss": "xss",
    "stored-xss": "xss",
    "insecure-randomness": "crypto",
    "insecure-hash": "crypto",
    "clear-text-logging": "clear-text-logging",
    "clear-text-storage": "clear-text-logging",
    "stack-trace-exposure": "clear-text-logging",
    "tainted-path": "path-traversal",
    "path-injection": "path-traversal",
    # resource-exhaustion / DoS CodeQL rules (dogfood ISSUE-011) — route to the
    # `resource` class (classes/resource.md) instead of orphaning to "unknown".
    "loop-bound-injection": "resource",
    "missing-rate-limiting": "resource",
    "polynomial-redos": "resource",
    "redos": "resource",
    "resource-exhaustion": "resource",
}


# Low-value vendored-rule classes: real code smells but not exploitable findings on their own
# (O-030: xss/log-injection vendored rules ~100% FP on a real backend). Demoted to `informational`
# rather than promoted to `raw`, so they don't flood the FP ladder. `unknown` = a hit with no CWE.
NOISE_CLASSES: frozenset[str] = frozenset({"log-injection", "clear-text-logging", "unknown"})


_ATTACK_CLASSES_PATH = Path(__file__).resolve().parents[2] / "references" / "attack-classes.md"
_CLASS_PROMPT_DIR = Path(__file__).resolve().parents[2] / "agents" / "classes"

# The universal table's key is the whole first cell. The `vs` rows of the
# disambiguation table and the `hunting/*.md` first column do not match.
_UNIVERSAL_KEY_RE = re.compile(r"^\| `([a-z][a-z0-9-]*)` \|", re.MULTILINE)
# The F2 companion table publishes its keys in the second cell.
_COMPANION_ROW_RE = re.compile(r"^\| `hunting/[^`]+` \|(.*)\|\s*$", re.MULTILINE)
_KEY_RE = re.compile(r"`([a-z][a-z0-9-]*)`")

# context.py:303 emits this pseudo-class for a recorded attack lead.
_HARNESS_CLASSES: frozenset[str] = frozenset({"manual-review"})


@lru_cache(maxsize=1)
def canonical_classes() -> frozenset[str]:
    """Return every attack-class key a finding may legitimately carry.

    The set is derived from every publisher rather than enumerated, so it
    cannot drift from its emitters: the two key tables in
    ``references/attack-classes.md``, this module's own CWE and rule-id
    tables, the review lane's general-defect classes, the class-extension
    prompts under ``agents/classes/``, and the harness's own pseudo-classes.
    Cached, so the files are read once per process and never at import time.

    Returns:
        The canonical key set.

    Raises:
        FileNotFoundError: ``references/attack-classes.md`` is missing.

    Example:
        >>> "ssrf" in canonical_classes()
        True
    """
    # local: keep clsmap a leaf at import time
    from sec_overlay.review_findings import GENERAL_DEFECT_CLASSES

    doc = _ATTACK_CLASSES_PATH.read_text()
    keys = set(_UNIVERSAL_KEY_RE.findall(doc))
    for cell in _COMPANION_ROW_RE.findall(doc):
        keys |= set(_KEY_RE.findall(cell))
    keys |= set(CWE_CLS.values()) | set(_RULE_ID_CLS.values())
    keys |= {"security-other", "unknown"}  # cls_from_semgrep_meta / cls_from_cwe fall-backs
    keys |= set(GENERAL_DEFECT_CLASSES)
    keys |= {p.stem for p in _CLASS_PROMPT_DIR.glob("*.md") if p.name != "README.md"}
    return frozenset(keys | _HARNESS_CLASSES)


def is_noise_class(cls: str) -> bool:
    """True if ``cls`` is a low-value vendored-rule class that should not enter the FP ladder as raw."""
    return cls in NOISE_CLASSES


def cls_from_rule_id(rule_id: str | None) -> str:
    """Map a rule id to an attack-class by high-confidence name substrings.

    Fallback router for vendored rules whose metadata carries no ``cls`` and no
    mapped CWE. Only unambiguous sink-naming substrings are mapped (see
    ``_RULE_ID_CLS``).

    Args:
        rule_id: The detector's rule/check id, or ``None``.

    Returns:
        The mapped attack-class key, or ``""`` if nothing matches.
    """
    if not rule_id:
        return ""
    for needle, cls in _RULE_ID_CLS.items():
        if needle in rule_id:
            return cls
    return ""


def cls_from_cwe(tags: list[str]) -> str:
    """Map the first recognizable CWE tag to an attack-class key.

    Args:
        tags: Strings that may embed a ``cwe-<n>`` token in any form
            (``external/cwe/cwe-089``, ``CWE-89: SQL Injection``).

    Returns:
        The mapped attack-class key, or ``"unknown"``.
    """
    for tag in tags:
        m = _CWE_RE.search(tag.lower())
        if m and m.group(1) in CWE_CLS:
            return CWE_CLS[m.group(1)]
    return "unknown"


def cls_from_semgrep_meta(metadata: dict, rule_id: str | None = None) -> str:
    """Derive an attack-class from a semgrep rule's ``metadata``.

    Preference: our own ``cls`` field, then any mapped ``cwe`` field (str or
    list), then a high-confidence ``rule_id`` name substring
    (:func:`cls_from_rule_id`) for vendored rules that carry neither, then
    ``"security-other"`` (security category, unmapped) or ``"unknown"``.

    Args:
        metadata: A semgrep result's ``extra.metadata`` dict.
        rule_id: The result's ``check_id`` — a fallback router so vendored
            ``lang.security.*`` rules (no ``cls``/CWE) still reach the right
            class instead of being orphaned in ``security-other``.

    Returns:
        An attack-class key.
    """
    cls = metadata.get("cls")
    if cls:
        return cls
    cwe = metadata.get("cwe")
    if cwe:
        tags = cwe if isinstance(cwe, list) else [cwe]
        mapped = cls_from_cwe([str(t) for t in tags])
        if mapped != "unknown":
            return mapped
        return cls_from_rule_id(rule_id) or "security-other"
    by_rule = cls_from_rule_id(rule_id)
    if by_rule:
        return by_rule
    if metadata.get("category") == "security":
        return "security-other"
    return "unknown"
