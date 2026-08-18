"""Review-mode profile gating: security reproduces gates A-E, general relaxes A/B.

The security profile is byte-identical to the pre-phase gate ladder: every
finding a gate (A-E) marked is dropped. The general profile is a strict
superset — a finding gates A or B marked is KEPT when its rule-doc defect
class is a general-defect class (REV-01, D-09); every other A/B-marked
finding is still dropped, and gates C, D, and E drop a finding under both
profiles unconditionally. The general-defect class and the review-mode
disposition it ships with live here, in a new module, never in
``models.py`` — that file is byte-mirrored by the Go port (D-11).

``apply_profile`` returns a 2-tuple ``(kept, dropped)``, not the 3-tuple
``(kept, dropped, declines)`` :func:`phase_gate.review_position_gate`
returns. Profile gating is a pure allowlist decision over a gate marking
already assigned upstream — it never produces a "position could not be
resolved" decline, so there is no third bucket.

Nothing in this module ever assigns ``confirmed`` or ``FindingStatus``: the
mechanical receipt gate (``findings_gate.py``/``evidence.py``) remains the
sole authority on that status, under both profiles.
"""

from __future__ import annotations

from dataclasses import dataclass

from sec_overlay.models import Finding
from sec_overlay.phase_gate import DroppedFinding

PROFILES: frozenset[str] = frozenset({"security", "general"})

# Gate letters a finding may be marked with before it reaches apply_profile.
# Gates A and B ("no real attacker", "no security impact") are the only two
# the general profile ever relaxes; C, D, and E always drop unconditionally.
_RELAXABLE_GATES: frozenset[str] = frozenset({"A", "B"})
_UNCONDITIONAL_GATES: frozenset[str] = frozenset({"C", "D", "E"})
GATE_LETTERS: frozenset[str] = _RELAXABLE_GATES | _UNCONDITIONAL_GATES

# The five rule-doc defect classes RULE-05's per-language docs name as the
# general profile's allowlist (D-09): null/nil/None dereference, thread
# safety / data races, resource leaks, swallowed errors, and injection.
GENERAL_DEFECT_CLASSES: frozenset[str] = frozenset(
    {"null-dereference", "thread-safety", "resource-leak", "error-swallowing", "injection"}
)

UNCONFIRMED_DISPOSITION = "unconfirmed"
NEEDS_DEPLOYMENT_TESTING_DISPOSITION = "needs-deployment-testing"
# The review-mode disposition vocabulary a general-defect finding may ship
# with. D-12's static-checkable/runtime-dependent split is a later plan's
# job; apply_profile only ever assigns UNCONFIRMED_DISPOSITION today.
REVIEW_DISPOSITIONS: frozenset[str] = frozenset(
    {UNCONFIRMED_DISPOSITION, NEEDS_DEPLOYMENT_TESTING_DISPOSITION}
)

EXCLUSION_BLOCK_BY_PROFILE: dict[str, str] = {
    "security": "EXCLUSION_RULES",
    "general": "GENERAL_PROFILE_EXCLUSION_RULES",
}


@dataclass(frozen=True)
class GatedFinding:
    """A finding paired with the gate (if any) that marked it for exclusion.

    ``models.Finding`` has no field for "which of gates A-E flagged this
    candidate" — it is frozen (D-11) and carries no such member. This
    wrapper is the input `apply_profile` needs without touching the frozen
    contract.
    """

    finding: Finding
    gate: str | None = None


@dataclass(frozen=True)
class ReviewFinding:
    """A finding that survived profile gating, with its review-mode metadata."""

    finding: Finding
    defect_class: str | None
    disposition: str
    profile: str


def classify(finding: Finding) -> str | None:
    """Map a finding's attack class onto the general-defect allowlist.

    Args:
        finding: The finding to classify. Its ``cls`` field (free-text, e.g.
            ``sqli``/``secrets``/``ssrf`` per ``models.Finding``'s docstring)
            is read as-is — this function adds no new taxonomy to ``models.py``.

    Returns:
        ``finding.cls`` unchanged when it is a member of
        :data:`GENERAL_DEFECT_CLASSES`, else ``None``.
    """
    return finding.cls if finding.cls in GENERAL_DEFECT_CLASSES else None


def apply_profile(
    findings: list[GatedFinding], profile: str
) -> tuple[list[ReviewFinding], list[DroppedFinding]]:
    """Split gated findings into kept and dropped by review profile.

    Under ``security``, every gate-marked finding (A-E) is dropped — exactly
    the pre-phase gate ladder's behaviour. Under ``general``, a finding gate
    A or B marked is kept only when :func:`classify` places it in the
    general-defect allowlist; every other A/B-marked finding is still
    dropped, and gates C, D, and E drop a finding under both profiles.

    Args:
        findings: Findings paired with the gate (if any) that marked them.
            A finding with ``gate=None`` was never marked by any gate and is
            always kept.
        profile: ``"security"`` or ``"general"``.

    Returns:
        A ``(kept, dropped)`` 2-tuple: kept :class:`ReviewFinding` records
        (never carrying ``confirmed``), and :class:`phase_gate.DroppedFinding`
        records sorted by ``(path, line, rule_id)``, matching
        :func:`phase_gate.review_position_gate`'s existing shape so the
        report path needs no new rendering branch.

    Raises:
        ValueError: ``profile`` is not a member of :data:`PROFILES`, or a
            finding's ``gate`` is set but not a member of :data:`GATE_LETTERS`.
    """
    if profile not in PROFILES:
        raise ValueError(f"unknown review profile: {profile!r}")

    kept: list[ReviewFinding] = []
    dropped: list[DroppedFinding] = []
    for gated in findings:
        finding = gated.finding
        gate = gated.gate
        if gate is not None and gate not in GATE_LETTERS:
            raise ValueError(f"unknown gate marking: {gate!r}")

        defect_class = classify(finding)
        bypassed = profile == "general" and gate in _RELAXABLE_GATES and defect_class is not None
        if gate is None or bypassed:
            kept.append(
                ReviewFinding(
                    finding=finding,
                    defect_class=defect_class,
                    disposition=UNCONFIRMED_DISPOSITION,
                    profile=profile,
                )
            )
        else:
            dropped.append(
                DroppedFinding(
                    path=finding.file,
                    line=finding.line,
                    rule_id=getattr(finding, "rule_id", ""),
                    reason=f"gate-{gate.lower()}",
                )
            )
    dropped.sort(key=lambda d: (d.path, d.line, d.rule_id))
    return kept, dropped
