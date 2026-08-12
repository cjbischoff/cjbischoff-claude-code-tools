"""Emit findings as a minimal, valid SARIF 2.1.0 document."""

from __future__ import annotations

from sec_overlay.models import Finding, Severity

_SCHEMA = (
    "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json"
)


def _level(sev: Severity) -> str:
    """Map a normalized severity to a SARIF result level.

    Args:
        sev: Severity enum value.

    Returns:
        A SARIF level string: "error", "warning", or "note".
    """
    if sev in (Severity.HIGH, Severity.CRITICAL):
        return "error"
    if sev is Severity.MEDIUM:
        return "warning"
    return "note"


def _rules(findings: list[Finding]) -> list[dict]:
    """Build a de-duplicated SARIF rule array from the finding set.

    Args:
        findings: Findings to derive rules from.

    Returns:
        One rule per distinct ``rule_id``, carrying ``cls`` as the name and
        ASVS/CodeGuard ids as properties. First occurrence of a ``rule_id`` wins.
    """
    by_id: dict[str, dict] = {}
    for f in findings:
        if f.rule_id in by_id:
            continue
        by_id[f.rule_id] = {
            "id": f.rule_id,
            "name": f.cls,
            "properties": {"asvs_ids": list(f.asvs_ids), "codeguard_ids": list(f.codeguard_ids)},
        }
    return list(by_id.values())


def to_sarif(
    findings: list[Finding], tool_name: str = "sec-overlay", suppressed: list[Finding] | None = None
) -> dict:
    """Convert findings to a SARIF 2.1.0 document.

    Args:
        findings: Findings to serialize.
        tool_name: Name recorded as the SARIF tool driver.
        suppressed: Findings that should carry an ``inSource`` suppression
            entry (e.g. needs-deployment-testing) so downstream gates see
            them without treating them as blocking.

    Returns:
        A SARIF 2.1.0 document as a dict.
    """
    suppressed_ids = {f.id for f in (suppressed or [])}
    results = []
    for f in findings:
        result = {
            "ruleId": f.rule_id,
            "level": _level(f.severity),
            "message": {"text": f.message},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": f.file},
                        "region": {"startLine": f.line},
                    }
                }
            ],
        }
        if f.id in suppressed_ids:
            result["suppressions"] = [{"kind": "inSource", "justification": "needs runtime proof"}]
        results.append(result)
    return {
        "version": "2.1.0",
        "$schema": _SCHEMA,
        "runs": [
            {"tool": {"driver": {"name": tool_name, "rules": _rules(findings)}}, "results": results}
        ],
    }
