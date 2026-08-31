"""REQ-33: the eight Part D elements render from the finding overflow."""

from __future__ import annotations

from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.report import render_finding
from sec_overlay.workspace import _OVERFLOW_ATTR

_EXTRA = {
    "attacker": "an unauthenticated internet client",
    "privilege": "none",
    "exact_request": "POST /api/fetch HTTP/1.1\nHost: t\n\nurl=http://169.254.169.254/",
    "exfil_channels": ["response body", "DNS resolution"],
    "library_version": "requests 2.31.0",
    "refutation": "checked for an allowlist on the host component; none present",
    "negative_results": ["no egress filter in the deployment manifest"],
    "baseline": "the same call in v1.2 used a fixed host",
}


def _finding(severity: str = "high") -> Finding:
    f = Finding(
        id="F-001",
        rule_id="semgrep:ssrf",
        cls="ssrf",
        status=FindingStatus.CONFIRMED,
        severity=Severity(severity),
        file="app/fetch.py",
        line=12,
        message="User-controlled URL reaches an HTTP client.",
        evidence_sources=["semgrep:ssrf"],
    )
    setattr(f, _OVERFLOW_ATTR, dict(_EXTRA))
    return f


def test_every_optional_section_renders() -> None:
    md = render_finding(_finding())
    for label in (
        "Attacker",
        "Privilege required",
        "Exact request",
        "Exfiltration channels",
        "Library version",
        "Refutation attempted",
        "Negative results",
        "Baseline",
    ):
        assert f"**{label}.**" in md, label


def test_list_values_render_as_bullets() -> None:
    md = render_finding(_finding())
    assert "- response body" in md
    assert "- DNS resolution" in md


def test_exact_request_renders_in_an_http_fence() -> None:
    md = render_finding(_finding())
    assert "```http" in md
    assert "POST /api/fetch HTTP/1.1" in md


def test_absent_fields_render_nothing() -> None:
    f = _finding()
    setattr(f, _OVERFLOW_ATTR, {})
    md = render_finding(f)
    assert "**Attacker.**" not in md
    assert "**Baseline.**" not in md


def test_condensed_tier_still_renders_the_sections() -> None:
    md = render_finding(_finding("medium"))
    assert "**Attacker.**" in md
    assert "**Baseline.**" in md
