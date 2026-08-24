"""REQ-20: receipt tier, verification strength, and reachability move the derived score."""

from __future__ import annotations

from dataclasses import replace

from sec_overlay.calibrate import calibrate_score
from sec_overlay.models import Finding, FindingStatus, Severity


def _f(**kwargs):
    base = Finding(
        id="F-1", rule_id="r", cls="xss", status=FindingStatus.CONFIRMED,
        severity=Severity.MEDIUM, file="app.py", line=1, message="m", dataflow=[],
    )
    return replace(base, **kwargs)


def test_tier_one_receipt_outranks_tier_two():
    assert calibrate_score(_f(receipt_tier=1)) > calibrate_score(_f(receipt_tier=2))


def test_tier_two_receipt_outranks_no_receipt():
    assert calibrate_score(_f(receipt_tier=2)) > calibrate_score(_f())


def test_verified_static_outranks_static_only():
    assert calibrate_score(_f(verification="verified-static")) > calibrate_score(
        _f(verification="static-only")
    )


def test_an_assessed_reachable_finding_outranks_an_unreachable_one():
    reachable = _f(reachability={"reachable": True})
    unreachable = _f(reachability={"reachable": False})
    assert calibrate_score(reachable) > calibrate_score(unreachable)


def test_an_unassessed_finding_scores_as_it_did_before():
    """Reachability is reward-only: no assessment must not cost a point."""
    assert calibrate_score(_f()) == calibrate_score(_f(reachability={"reachable": False}))


def test_the_score_stays_in_range():
    top = _f(severity=Severity.CRITICAL, cls="sqli", dataflow=["a", "b", "c"],
             receipt_tier=1, verification="verified-static", reachability={"reachable": True})
    assert 1 <= calibrate_score(top) <= 10
