"""Tests for SARIF emission."""

from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.sarif import to_sarif


def _f(sev):
    return Finding(id="F-0001", rule_id="r", cls="sqli", status=FindingStatus.CONFIRMED,
                   severity=sev, file="app.py", line=18, message="SQLi")


def test_sarif_shape_and_level_mapping():
    doc = to_sarif([_f(Severity.HIGH)])
    assert doc["version"] == "2.1.0"
    run = doc["runs"][0]
    assert run["tool"]["driver"]["name"] == "sec-overlay"
    res = run["results"][0]
    assert res["ruleId"] == "r"
    assert res["level"] == "error"
    loc = res["locations"][0]["physicalLocation"]
    assert loc["artifactLocation"]["uri"] == "app.py"
    assert loc["region"]["startLine"] == 18


def test_sarif_level_for_medium_and_low():
    assert to_sarif([_f(Severity.MEDIUM)])["runs"][0]["results"][0]["level"] == "warning"
    assert to_sarif([_f(Severity.LOW)])["runs"][0]["results"][0]["level"] == "note"


def test_driver_rules_populated_from_findings():
    findings = [
        Finding(id="F-1", rule_id="authz-owner", cls="authz", status=FindingStatus.CONFIRMED,
                severity=Severity.HIGH, file="a.py", line=1, message="m",
                asvs_ids=["4.2.1"], codeguard_ids=["CG-12"]),
        Finding(id="F-2", rule_id="authz-owner", cls="authz", status=FindingStatus.CONFIRMED,
                severity=Severity.HIGH, file="b.py", line=2, message="m"),
    ]
    doc = to_sarif(findings)
    rules = doc["runs"][0]["tool"]["driver"]["rules"]
    assert len(rules) == 1                              # deduped by rule_id
    rule = rules[0]
    assert rule["id"] == "authz-owner"
    assert rule["properties"]["asvs_ids"] == ["4.2.1"]
    assert rule["properties"]["codeguard_ids"] == ["CG-12"]
