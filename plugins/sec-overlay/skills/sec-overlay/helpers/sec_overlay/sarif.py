"""Emit findings as a minimal, valid SARIF 2.1.0 document."""

from __future__ import annotations

import hashlib

from sec_overlay.models import Finding, Severity

_SCHEMA = (
    "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json"
)

FINGERPRINT_KEY = "secOverlay/v1"


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


def _sarif_fingerprint(finding: Finding) -> str:
    """Derive a message-independent SARIF result fingerprint.

    Keyed on ``file|cls|evidence`` (evidence stripped), never ``message``, so
    a wording tweak to a finding's message does not churn its identity across
    runs. Does not reuse `fingerprint.fingerprint()` — that module keys on a
    different identity contract (dedup, not SARIF result correlation) — and
    does not Unicode-normalize `evidence`: it is harness-derived real file
    text, not free-form model prose, so byte-identical evidence is the
    correct equality bar.

    Args:
        finding: Finding to fingerprint.

    Returns:
        16 lowercase hex characters.
    """
    key = f"{finding.file}|{finding.cls}|{finding.evidence.strip()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def _related_locations(finding: Finding) -> list[dict]:
    """Return one SARIF location per site of a systemic cluster.

    A cluster representative carries every member's site in ``affected_sites``.
    Without these, a 66-site cluster reaches a SARIF consumer as one location.

    Args:
        finding: The finding to expand.

    Returns:
        One location dict per site, in the order the finding records them. An
        entry missing ``file`` is skipped, and ``line`` defaults to 1. An
        entry whose ``id`` is the finding's own id is skipped, because SARIF
        already carries it as the primary location. An entry with no ``id``
        is kept.
    """
    out: list[dict] = []
    for site in finding.affected_sites or []:
        uri = site.get("file")
        if not uri or site.get("id") == finding.id:
            continue
        out.append(
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": uri},
                    "region": {"startLine": site.get("line") or 1},
                }
            }
        )
    return out


def to_sarif(
    findings: list[Finding], tool_name: str = "sec-overlay", suppressed: list[Finding] | None = None
) -> dict:
    """Convert findings to a SARIF 2.1.0 document.

    Args:
        findings: Findings to serialize.
        tool_name: Name recorded as the SARIF tool driver.
        suppressed: Findings that should carry an ``external`` suppression
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
        related = _related_locations(f)
        if related:
            result["relatedLocations"] = related
        result["properties"] = {"findingId": f.id}
        if f.id in suppressed_ids:
            result["suppressions"] = [{"kind": "external", "justification": "needs runtime proof"}]
        result["partialFingerprints"] = {FINGERPRINT_KEY: _sarif_fingerprint(f)}
        results.append(result)
    return {
        "version": "2.1.0",
        "$schema": _SCHEMA,
        "runs": [
            {"tool": {"driver": {"name": tool_name, "rules": _rules(findings)}}, "results": results}
        ],
    }
