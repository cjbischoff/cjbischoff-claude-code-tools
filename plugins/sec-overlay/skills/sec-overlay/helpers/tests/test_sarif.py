"""Tests for SARIF emission."""

from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.sarif import FINGERPRINT_KEY, to_sarif


def _f(sev):
    return Finding(
        id="F-0001",
        rule_id="r",
        cls="sqli",
        status=FindingStatus.CONFIRMED,
        severity=sev,
        file="app.py",
        line=18,
        message="SQLi",
    )


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
        Finding(
            id="F-1",
            rule_id="authz-owner",
            cls="authz",
            status=FindingStatus.CONFIRMED,
            severity=Severity.HIGH,
            file="a.py",
            line=1,
            message="m",
            asvs_ids=["4.2.1"],
            codeguard_ids=["CG-12"],
        ),
        Finding(
            id="F-2",
            rule_id="authz-owner",
            cls="authz",
            status=FindingStatus.CONFIRMED,
            severity=Severity.HIGH,
            file="b.py",
            line=2,
            message="m",
        ),
    ]
    doc = to_sarif(findings)
    rules = doc["runs"][0]["tool"]["driver"]["rules"]
    assert len(rules) == 1  # deduped by rule_id
    rule = rules[0]
    assert rule["id"] == "authz-owner"
    assert rule["properties"]["asvs_ids"] == ["4.2.1"]
    assert rule["properties"]["codeguard_ids"] == ["CG-12"]


def test_suppressed_findings_carry_an_external_suppression():
    """REQ-57: a needs-runtime suppression is external, not inSource.

    The prior contract emitted ``inSource``, which asserts an annotation in the
    reviewed file. No such annotation exists; the reason is out-of-repo.
    """
    confirmed = Finding(
        id="F-1",
        rule_id="r",
        cls="authz",
        status=FindingStatus.CONFIRMED,
        severity=Severity.HIGH,
        file="a.py",
        line=1,
        message="m",
    )
    ndt = Finding(
        id="F-2",
        rule_id="r",
        cls="authz",
        status=FindingStatus.NEEDS_DEPLOYMENT_TESTING,
        severity=Severity.MEDIUM,
        file="b.py",
        line=2,
        message="m",
    )
    doc = to_sarif([confirmed, ndt], suppressed=[ndt])
    by_id = {
        r["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]: r
        for r in doc["runs"][0]["results"]
    }
    assert "suppressions" not in by_id["a.py"]
    assert by_id["b.py"]["suppressions"][0]["kind"] == "external"


def test_a_cluster_emits_one_related_location_per_affected_site():
    """REQ-57: a systemic cluster must not shrink to one location in SARIF."""
    f = _f(Severity.HIGH)
    f.cluster_id = "C-1"
    f.affected_sites = [
        {"id": "F-0002", "file": "a.py", "line": 18},
        {"id": "F-0003", "file": "b.py", "line": 42},
        {"id": "F-0004", "file": "c.py", "line": 7},
    ]
    result = to_sarif([f])["runs"][0]["results"][0]
    related = result["relatedLocations"]
    assert len(related) == 3
    uris = [r["physicalLocation"]["artifactLocation"]["uri"] for r in related]
    assert uris == ["a.py", "b.py", "c.py"]
    assert related[1]["physicalLocation"]["region"]["startLine"] == 42


def test_a_singleton_finding_has_no_related_locations():
    """REQ-57: the key appears only when the finding carries sites."""
    assert "relatedLocations" not in to_sarif([_f(Severity.LOW)])["runs"][0]["results"][0]


def test_every_result_carries_its_finding_id():
    """REQ-57: a SARIF consumer must be able to name the finding."""
    result = to_sarif([_f(Severity.HIGH)])["runs"][0]["results"][0]
    assert result["properties"]["findingId"] == "F-0001"


# --- partialFingerprints (OUT-02) ----------------------------------------------


def _finding(
    id="F-0001",
    file="app.py",
    cls="sqli",
    message="SQLi",
    evidence="cursor.execute(query)",
):
    return Finding(
        id=id,
        rule_id="r",
        cls=cls,
        status=FindingStatus.CONFIRMED,
        severity=Severity.HIGH,
        file=file,
        line=18,
        message=message,
        evidence=evidence,
    )


def test_two_findings_differing_only_in_message_share_fingerprint():
    doc = to_sarif([_finding(message="first wording"), _finding(id="F-0002", message="second wording")])
    fp1, fp2 = (r["partialFingerprints"][FINGERPRINT_KEY] for r in doc["runs"][0]["results"])
    assert fp1 == fp2


def test_findings_differing_in_file_produce_different_fingerprints():
    doc = to_sarif([_finding(file="app.py"), _finding(id="F-0002", file="other.py")])
    fp1, fp2 = (r["partialFingerprints"][FINGERPRINT_KEY] for r in doc["runs"][0]["results"])
    assert fp1 != fp2


def test_findings_differing_in_cls_produce_different_fingerprints():
    doc = to_sarif([_finding(cls="sqli"), _finding(id="F-0002", cls="xss")])
    fp1, fp2 = (r["partialFingerprints"][FINGERPRINT_KEY] for r in doc["runs"][0]["results"])
    assert fp1 != fp2


def test_findings_differing_in_evidence_produce_different_fingerprints():
    doc = to_sarif([_finding(evidence="a"), _finding(id="F-0002", evidence="b")])
    fp1, fp2 = (r["partialFingerprints"][FINGERPRINT_KEY] for r in doc["runs"][0]["results"])
    assert fp1 != fp2


def test_to_sarif_empty_list_has_no_results_and_no_fingerprint_key_anywhere():
    doc = to_sarif([])
    assert doc["runs"][0]["results"] == []
    assert "partialFingerprints" not in json_dumps_for_scan(doc)


def json_dumps_for_scan(doc: dict) -> str:
    """Serialize `doc` for a substring scan, so a fingerprint key hiding in a
    nested location the test author didn't think to check is still caught."""
    import json

    return json.dumps(doc)


def test_a_single_finding_produces_exactly_one_fingerprint():
    doc = to_sarif([_finding()])
    results = doc["runs"][0]["results"]
    assert len(results) == 1
    assert len(results[0]["partialFingerprints"][FINGERPRINT_KEY]) == 16


def test_whitespace_only_evidence_still_receives_a_fingerprint():
    doc = to_sarif([_finding(evidence="   \n\t  ")])
    fp = doc["runs"][0]["results"][0]["partialFingerprints"][FINGERPRINT_KEY]
    assert len(fp) == 16


def test_unicode_normalized_equivalent_evidence_produces_different_fingerprints():
    # "é" (e + combining acute accent) and "é" (é, precomposed) are
    # Unicode-equivalent under NFC but not byte-identical. The fingerprint is a
    # deliberate byte-equality contract (no unicodedata normalization pass) —
    # this test records that decision rather than leaving it an accident.
    combining = _finding(evidence="café")
    precomposed = _finding(id="F-0002", evidence="café")
    doc = to_sarif([combining, precomposed])
    fp1, fp2 = (r["partialFingerprints"][FINGERPRINT_KEY] for r in doc["runs"][0]["results"])
    assert fp1 != fp2


def test_related_locations_skip_the_findings_own_site():
    """REQ-66: the primary location must not repeat as a related location."""
    from sec_overlay.sarif import _related_locations

    f = _f(Severity.HIGH)
    f.affected_sites = [
        {"id": "F-0001", "file": "app.py", "line": 18},
        {"id": "F-0002", "file": "other.py", "line": 4},
        {"file": "nameless.py", "line": 9},
    ]

    uris = [loc["physicalLocation"]["artifactLocation"]["uri"] for loc in _related_locations(f)]
    assert uris == ["other.py", "nameless.py"]
