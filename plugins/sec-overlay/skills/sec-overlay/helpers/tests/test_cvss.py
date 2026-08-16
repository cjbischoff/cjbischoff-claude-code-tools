"""Tests for the deterministic CVSS v4.0 base scoring engine + OffensivePriority.

Reference scores are ``(vector, expected_score)`` pairs pulled verbatim from
the National Vulnerability Database's public REST API
(``https://services.nvd.nist.gov/rest/json/cves/2.0``), a batch of CVEs
published 2026-01-01..2026-02-15, fetched 2026-08-16. Each entry is restricted
to a published ``cvssMetricV40`` record whose vector string carries ``E:X``
(and ``CR:X``/``IR:X``/``AR:X``, which held for every record sampled): with no
Threat or Environmental metric supplied, NVD's single ``baseScore`` field is
unambiguously the CVSS-B (base-only) score this engine computes — there is no
separate base/overall score in CVSS v4.0's model, so any non-``E:X`` record's
``baseScore`` would reflect the supplied Threat metric and cannot be trusted
as a base-only reference. The vector below drops the ``/E:X/...`` suffix
NVD appends (CR/IR/AR/M*/S/AU/R/V/RE all ``X``) since this engine parses base
metrics only. CVE IDs are recorded per row for provenance/re-verification.

The macrovector/interpolation algorithm itself was ported from FIRST's
official calculator (https://github.com/FIRSTdotorg/cvss-v4-calculator,
BSD-2-Clause, files ``cvss_score.js`` / ``cvss_lookup.js`` / ``max_composed.js``
/ ``max_severity.js``, read directly, never executed).
"""

import pytest

from sec_overlay.cvss import (
    MACROVECTOR_LOOKUP,
    _macrovector,
    _parse,
    cvss40_base,
    offensive_priority,
)

# (CVE ID, vector, expected_score) — scores copied verbatim from NVD's cvssMetricV40 baseScore.
REFERENCE = [
    ("CVE-2025-64121", "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:H/SI:H/SA:H", 10.0),
    ("CVE-2025-64120", "CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:H/VA:H/SC:H/SI:H/SA:H", 9.4),
    ("CVE-2025-64125", "CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:P/VC:H/VI:H/VA:H/SC:H/SI:H/SA:H", 9.4),
    ("CVE-2025-64119", "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N", 9.3),
    ("CVE-2026-21440", "CVSS:4.0/AV:N/AC:L/AT:P/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N", 9.2),
    ("CVE-2026-22194", "CVSS:4.0/AV:N/AC:L/AT:P/PR:N/UI:P/VC:H/VI:H/VA:H/SC:L/SI:H/SA:H", 8.9),
    ("CVE-2025-68455", "CVSS:4.0/AV:N/AC:L/AT:N/PR:H/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N", 8.6),
    ("CVE-2026-22610", "CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:A/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N", 8.5),
    ("CVE-2025-9427", "CVSS:4.0/AV:N/AC:L/AT:N/PR:H/UI:A/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N", 8.4),
    ("CVE-2025-13744", "CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:P/VC:H/VI:L/VA:N/SC:H/SI:H/SA:N", 8.4),
    ("CVE-2026-21857", "CVSS:4.0/AV:N/AC:L/AT:N/PR:H/UI:N/VC:H/VI:N/VA:N/SC:H/SI:H/SA:N", 8.3),
    ("CVE-2025-64123", "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:N/VI:N/VA:N/SC:H/SI:H/SA:H", 7.9),
    ("CVE-2025-68954", "CVSS:4.0/AV:N/AC:L/AT:P/PR:H/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N", 7.5),
    ("CVE-2025-40942", "CVSS:4.0/AV:L/AC:L/AT:P/PR:L/UI:P/VC:H/VI:H/VA:H/SC:H/SI:H/SA:H", 7.3),
    ("CVE-2025-69275", "CVSS:4.0/AV:N/AC:H/AT:N/PR:L/UI:N/VC:H/VI:L/VA:N/SC:H/SI:L/SA:N", 7.1),
    ("CVE-2025-66023", "CVSS:4.0/AV:N/AC:H/AT:P/PR:H/UI:N/VC:N/VI:N/VA:H/SC:N/SI:N/SA:H", 6.9),
    ("CVE-2026-22214", "CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:A/VC:N/VI:N/VA:H/SC:N/SI:N/SA:N", 6.8),
    ("CVE-2025-69224", "CVSS:4.0/AV:N/AC:L/AT:P/PR:N/UI:N/VC:L/VI:L/VA:N/SC:N/SI:N/SA:N", 6.3),
    ("CVE-2026-21896", "CVSS:4.0/AV:N/AC:L/AT:P/PR:L/UI:A/VC:N/VI:H/VA:L/SC:N/SI:N/SA:N", 5.8),
    ("CVE-2026-22027", "CVSS:4.0/AV:L/AC:L/AT:P/PR:H/UI:N/VC:N/VI:H/VA:H/SC:N/SI:N/SA:N", 5.7),
    ("CVE-2026-22597", "CVSS:4.0/AV:N/AC:L/AT:N/PR:H/UI:N/VC:N/VI:N/VA:N/SC:L/SI:N/SA:N", 5.1),
    ("CVE-2026-22231", "CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:A/VC:L/VI:L/VA:L/SC:N/SI:N/SA:N", 4.8),
    ("CVE-2026-22213", "CVSS:4.0/AV:L/AC:L/AT:N/PR:L/UI:A/VC:N/VI:N/VA:L/SC:N/SI:N/SA:N", 2.4),
    ("CVE-2026-22805", "CVSS:4.0/AV:N/AC:H/AT:P/PR:H/UI:N/VC:N/VI:N/VA:N/SC:L/SI:N/SA:N", 2.1),
    ("CVE-2025-12776", "CVSS:4.0/AV:N/AC:L/AT:P/PR:H/UI:A/VC:L/VI:L/VA:N/SC:N/SI:N/SA:N", 1.8),
]


@pytest.mark.parametrize("cve,vector,expected", REFERENCE, ids=[r[0] for r in REFERENCE])
def test_reference_scores(cve, vector, expected):
    score, _ = cvss40_base(vector)
    assert score == expected


def test_at_least_three_reference_vectors_are_interpolation_sensitive():
    """Guard the REFERENCE set's own diversity: not every score is a bare lookup hit."""
    interpolated = 0
    for _cve, vector, expected in REFERENCE:
        m = _parse(vector)
        raw = MACROVECTOR_LOOKUP[_macrovector(m)]
        if raw != expected:
            interpolated += 1
    assert interpolated >= 3


def test_bounds_and_bands():
    score, rating = cvss40_base(
        "CVSS:4.0/AV:P/AC:H/AT:P/PR:H/UI:A/VC:N/VI:N/VA:N/SC:N/SI:N/SA:N"
    )
    assert score == 0.0 and rating == "None"


def test_rating_band_boundaries():
    # bands per the v4.0 spec: 0.0 None, 0.1-3.9 Low, 4.0-6.9 Medium, 7.0-8.9 High, 9.0-10.0 Critical
    from sec_overlay.cvss import _rating

    assert _rating(0.0) == "None"
    assert _rating(3.9) == "Low"
    assert _rating(4.0) == "Medium"
    assert _rating(6.9) == "Medium"
    assert _rating(7.0) == "High"
    assert _rating(9.0) == "Critical"


def test_v31_vector_rejected_with_migration_message():
    with pytest.raises(ValueError, match="4.0"):
        cvss40_base("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N")


def test_malformed_vector_rejected():
    with pytest.raises(ValueError):
        cvss40_base("CVSS:4.0/AV:N/AC:L")  # missing required metrics


def test_invalid_metric_value_rejected():
    with pytest.raises(ValueError):
        cvss40_base("CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:X/VI:H/VA:H/SC:N/SI:N/SA:N")


def test_threat_metric_rejected():
    with pytest.raises(ValueError, match="base metrics only"):
        cvss40_base(
            "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N/E:U"
        )


def test_environmental_metric_rejected():
    with pytest.raises(ValueError, match="base metrics only"):
        cvss40_base(
            "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N/CR:L"
        )


def test_not_defined_threat_and_environmental_suffix_parses():
    base = "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N"
    nvd_shaped = base + "/E:X/CR:X/IR:X/AR:X"
    assert cvss40_base(nvd_shaped) == cvss40_base(base)


def test_offensive_priority_v4():
    p1 = "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N"
    assert offensive_priority(p1) == "P1"
    p2 = "CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N"
    assert offensive_priority(p2) == "P2"
    local = "CVSS:4.0/AV:L/AC:L/AT:N/PR:N/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N"
    assert offensive_priority(local) == "P3"
    # externally_facing + PR!=H promotes to P2 before the AV-based P3 demotion (3.1 branch order kept).
    assert offensive_priority(local, externally_facing=True) == "P2"
