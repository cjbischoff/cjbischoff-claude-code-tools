"""Tests for reachability verdict and blocker taxonomy."""

from sec_overlay.reachability import (
    BLOCKERS,
    blocker_of,
    is_reachable,
    partition,
    validate_reachability,
)
from sec_overlay.models import Finding, Severity


def _f(blocker: str | None = None, reachable: bool | None = None) -> Finding:
    r = {}
    if reachable is not None:
        r["reachable"] = reachable
    if blocker is not None:
        r["blocker"] = blocker
    return Finding(
        id="T-1", rule_id="r", cls="sqli",
        status="candidate", severity=Severity.MEDIUM,
        file="a.py", line=1, message="test",
        reachability=r if r else None,
    )


def test_blockers_include_caller_out_of_scope():
    assert "caller-out-of-scope" in BLOCKERS


def test_blocker_of_returns_caller_out_of_scope():
    f = _f(blocker="caller-out-of-scope", reachable=False)
    assert blocker_of(f) == "caller-out-of-scope"


def test_blocker_of_returns_none_when_reachable():
    f = _f(reachable=True)
    assert blocker_of(f) is None


def test_blocker_of_returns_none_when_unassessed():
    """Recall-safe default: unassessed findings are treated as reachable."""
    f = _f()
    assert blocker_of(f) is None


def test_blocker_of_falls_back_to_other_for_unknown_blocker():
    f = _f(blocker="made-up-blocker", reachable=False)
    assert blocker_of(f) == "other"


def test_is_reachable_returns_false_for_blocked():
    f = _f(blocker="sanitizer", reachable=False)
    assert is_reachable(f) is False


def test_is_reachable_defaults_to_true_when_unassessed():
    f = _f()
    assert is_reachable(f) is True


def test_validate_reachability_accepts_caller_out_of_scope():
    r = {"blocker": "caller-out-of-scope", "reachable": False}
    assert validate_reachability(r) == []


def test_validate_reachability_accepts_external_boundary_without_reachable():
    r = {"blocker": "external-boundary"}
    assert validate_reachability(r) == []


def test_partition_splits_reachable_and_blocked():
    reachable = _f(reachable=True)
    blocked = _f(blocker="sanitizer", reachable=False)
    result = partition([reachable, blocked])
    assert len(result["reachable"]) == 1
    assert len(result["blocked"]) == 1
    assert result["reachable"][0].id == "T-1"
