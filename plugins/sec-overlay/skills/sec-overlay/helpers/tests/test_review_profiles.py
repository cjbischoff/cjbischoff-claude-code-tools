"""Tests for review profile gating (REV-01): security vs general, no regression."""

import json
from pathlib import Path

import pytest

from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.phase_gate import DroppedFinding
from sec_overlay.review_findings import (
    EXCLUSION_BLOCK_BY_PROFILE,
    GENERAL_DEFECT_CLASSES,
    NEEDS_DEPLOYMENT_TESTING_DISPOSITION,
    UNCONFIRMED_DISPOSITION,
    GatedFinding,
    ReviewFinding,
    apply_profile,
    classify,
)

_FIXTURE_DIR = Path(__file__).parent / "fixtures"
_BASELINE_PATH = _FIXTURE_DIR / "review_profiles_security_baseline.json"


def _finding(id_: str, cls_: str, *, file: str, line: int, rule_id: str) -> Finding:
    return Finding(
        id=id_,
        rule_id=rule_id,
        cls=cls_,
        status=FindingStatus.CANDIDATE,
        severity=Severity.MEDIUM,
        file=file,
        line=line,
        message="synthetic fixture finding",
    )


def _dual_run_fixture() -> list[GatedFinding]:
    """One diff fixture (D-10): a finding per gate letter, plus one unmarked.

    F-1 unmarked (kept under both profiles, not a general-defect class).
    F-2/F-4 gate A/B with an allowlisted class (general bypasses, security drops).
    F-3 gate A with a non-allowlisted class (dropped under both).
    F-5/F-6/F-7 gates C/D/E with an allowlisted class (dropped under both — unconditional).
    """
    return [
        GatedFinding(_finding("F-1", "sqli", file="f1.py", line=1, rule_id="R1"), gate=None),
        GatedFinding(_finding("F-2", "injection", file="f2.py", line=2, rule_id="R2"), gate="A"),
        GatedFinding(_finding("F-3", "sqli", file="f3.py", line=3, rule_id="R3"), gate="A"),
        GatedFinding(
            _finding("F-4", "null-dereference", file="f4.py", line=4, rule_id="R4"), gate="B"
        ),
        GatedFinding(
            _finding("F-5", "thread-safety", file="f5.py", line=5, rule_id="R5"), gate="C"
        ),
        GatedFinding(
            _finding("F-6", "resource-leak", file="f6.py", line=6, rule_id="R6"), gate="D"
        ),
        GatedFinding(
            _finding("F-7", "error-swallowing", file="f7.py", line=7, rule_id="R7"), gate="E"
        ),
    ]


def test_apply_profile_raises_on_unknown_profile():
    with pytest.raises(ValueError, match="unknown review profile"):
        apply_profile([], "audit")


def test_apply_profile_raises_on_unknown_gate_marking():
    finding = _finding("F-1", "sqli", file="a.py", line=1, rule_id="R1")
    with pytest.raises(ValueError, match="unknown gate marking"):
        apply_profile([GatedFinding(finding, gate="Z")], "security")


def test_classify_returns_none_for_non_allowlisted_class():
    finding = _finding("F-1", "sqli", file="a.py", line=1, rule_id="R1")
    assert classify(finding) is None


def test_classify_returns_the_class_for_every_allowlisted_class():
    for cls_ in GENERAL_DEFECT_CLASSES:
        finding = _finding("F-1", cls_, file="a.py", line=1, rule_id="R1")
        assert classify(finding) == cls_


def test_unmarked_finding_is_always_kept_under_both_profiles():
    finding = _finding("F-1", "sqli", file="a.py", line=1, rule_id="R1")
    for profile in ("security", "general"):
        kept, dropped = apply_profile([GatedFinding(finding, gate=None)], profile)
        assert dropped == []
        assert len(kept) == 1
        assert kept[0].finding is finding
        assert kept[0].disposition == UNCONFIRMED_DISPOSITION
        assert kept[0].profile == profile


def test_security_profile_drops_every_gate_marked_finding():
    kept, dropped = apply_profile(_dual_run_fixture(), "security")
    assert [rf.finding.id for rf in kept] == ["F-1"]
    assert [d.rule_id for d in dropped] == ["R2", "R3", "R4", "R5", "R6", "R7"]


def test_general_profile_bypasses_gate_a_and_b_for_an_allowlisted_class():
    kept, dropped = apply_profile(_dual_run_fixture(), "general")
    kept_ids = {rf.finding.id for rf in kept}
    assert kept_ids == {"F-1", "F-2", "F-4"}
    dropped_ids = {d.rule_id for d in dropped}
    assert dropped_ids == {"R3", "R5", "R6", "R7"}


def test_general_profile_still_drops_a_non_allowlisted_gate_a_finding():
    finding = _finding("F-3", "sqli", file="f3.py", line=3, rule_id="R3")
    kept, dropped = apply_profile([GatedFinding(finding, gate="A")], "general")
    assert kept == []
    assert dropped == [DroppedFinding(path="f3.py", line=3, rule_id="R3", reason="gate-a")]


def test_general_profile_drops_gates_c_d_e_unconditionally_even_for_allowlisted_class():
    fixture = [gf for gf in _dual_run_fixture() if gf.gate in ("C", "D", "E")]
    kept, dropped = apply_profile(fixture, "general")
    assert kept == []
    assert {d.reason for d in dropped} == {"gate-c", "gate-d", "gate-e"}


def test_apply_profile_assigns_needs_deployment_testing_for_thread_safety():
    """D-12: a runtime-dependent class ships needs-deployment-testing, never unconfirmed."""
    finding = _finding("F-TS", "thread-safety", file="ts.py", line=1, rule_id="RTS")
    kept, dropped = apply_profile([GatedFinding(finding, gate="A")], "general")
    assert dropped == []
    assert len(kept) == 1
    assert kept[0].disposition == NEEDS_DEPLOYMENT_TESTING_DISPOSITION


@pytest.mark.parametrize(
    "cls_", ["null-dereference", "error-swallowing", "resource-leak", "injection"]
)
def test_apply_profile_assigns_unconfirmed_for_each_static_checkable_class(cls_):
    """D-12: every static-checkable class ships unconfirmed, never needs-deployment-testing."""
    finding = _finding("F-SC", cls_, file="sc.py", line=1, rule_id="RSC")
    kept, dropped = apply_profile([GatedFinding(finding, gate="A")], "general")
    assert dropped == []
    assert len(kept) == 1
    assert kept[0].disposition == UNCONFIRMED_DISPOSITION


def test_apply_profile_never_assigns_a_confirmed_disposition():
    thread_safety = _finding("F-TS", "thread-safety", file="ts.py", line=1, rule_id="RTS")
    fixture = [*_dual_run_fixture(), GatedFinding(thread_safety, gate="A")]
    kept, _ = apply_profile(fixture, "general")
    for rf in kept:
        assert rf.disposition != "confirmed"
        assert rf.disposition in (UNCONFIRMED_DISPOSITION, NEEDS_DEPLOYMENT_TESTING_DISPOSITION)


def test_dropped_findings_are_sorted_by_path_line_rule_id():
    fixture = list(reversed(_dual_run_fixture()))
    _, dropped = apply_profile(fixture, "security")
    assert [d.path for d in dropped] == sorted(d.path for d in dropped)


def test_exclusion_block_by_profile_names_the_two_prompt_constants_blocks():
    assert EXCLUSION_BLOCK_BY_PROFILE == {
        "security": "EXCLUSION_RULES",
        "general": "GENERAL_PROFILE_EXCLUSION_RULES",
    }


def _serialize(kept: list[ReviewFinding], dropped: list[DroppedFinding]) -> dict:
    return {
        "kept_ids": [rf.finding.id for rf in kept],
        "dropped": [
            {"path": d.path, "line": d.line, "rule_id": d.rule_id, "reason": d.reason}
            for d in dropped
        ],
    }


def test_dual_run_security_profile_matches_committed_baseline_no_regression():
    """D-10: security-profile output on the dual-run fixture must never drift.

    The baseline was captured from this same fixture at commit
    245d9e7 (test(03-04): add failing tests for review profile gating) — the
    commit that first committed ``review_profiles_security_baseline.json``.
    Any future diff to
    ``apply_profile`` that changes the security profile's kept/dropped split
    fails this test; that is the point (REV-01's no-regression guarantee).
    """
    kept, dropped = apply_profile(_dual_run_fixture(), "security")
    actual = _serialize(kept, dropped)
    expected = json.loads(_BASELINE_PATH.read_text())
    assert actual == expected


def test_dual_run_general_profile_is_a_strict_superset_of_the_security_baseline():
    """D-10: general output is the security superset plus rule-doc classes."""
    security_kept, _ = apply_profile(_dual_run_fixture(), "security")
    general_kept, _ = apply_profile(_dual_run_fixture(), "general")
    security_ids = {rf.finding.id for rf in security_kept}
    general_ids = {rf.finding.id for rf in general_kept}

    assert security_ids.issubset(general_ids)
    added_ids = general_ids - security_ids
    assert added_ids, "general profile must add at least one finding over security"
    added = {rf.finding.id: rf for rf in general_kept if rf.finding.id in added_ids}
    for rf in added.values():
        assert rf.defect_class in GENERAL_DEFECT_CLASSES
