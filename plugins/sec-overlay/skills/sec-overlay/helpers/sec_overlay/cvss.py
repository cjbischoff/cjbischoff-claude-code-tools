"""Deterministic CVSS v4.0 base scoring + an orthogonal OffensivePriority axis.

The LLM proposes a CVSS v4.0 vector; the score is computed here via the
MacroVector model ported from FIRST's official calculator
(https://github.com/FIRSTdotorg/cvss-v4-calculator, BSD-2-Clause), never LLM
arithmetic. OffensivePriority (P1-P4) is unchanged from the 3.1 era.

Base metrics only: no Threat (E), Environmental (CR/IR/AR, M*), or
Supplemental metric support (findings only ever carry base vectors). Per the
reference's own ``m()`` accessor, an unspecified metric defaults to its
worst-case value: E defaults to "A" and CR/IR/AR default to "H" — this
engine hardcodes those same defaults rather than accepting the metrics at
all, so the ported MacroVector/interpolation math runs unmodified.
"""

from __future__ import annotations

import math
from itertools import product

from sec_overlay.cvss4_data import MACROVECTOR_LOOKUP, MAX_COMPOSED, MAX_SEVERITY

_REQUIRED = ("AV", "AC", "AT", "PR", "UI", "VC", "VI", "VA", "SC", "SI", "SA")
_ALLOWED = {
    "AV": {"N", "A", "L", "P"},
    "AC": {"L", "H"},
    "AT": {"N", "P"},
    "PR": {"N", "L", "H"},
    "UI": {"N", "P", "A"},
    "VC": {"H", "L", "N"},
    "VI": {"H", "L", "N"},
    "VA": {"H", "L", "N"},
    "SC": {"H", "L", "N"},
    "SI": {"H", "L", "N"},
    "SA": {"H", "L", "N"},
}

# Severity-level indices, ported verbatim from cvss_score.js's level tables.
_AV_LEVELS = {"N": 0.0, "A": 0.1, "L": 0.2, "P": 0.3}
_PR_LEVELS = {"N": 0.0, "L": 0.1, "H": 0.2}
_UI_LEVELS = {"N": 0.0, "P": 0.1, "A": 0.2}
_AC_LEVELS = {"L": 0.0, "H": 0.1}
_AT_LEVELS = {"N": 0.0, "P": 0.1}
_VC_LEVELS = {"H": 0.0, "L": 0.1, "N": 0.2}
_VI_LEVELS = {"H": 0.0, "L": 0.1, "N": 0.2}
_VA_LEVELS = {"H": 0.0, "L": 0.1, "N": 0.2}
_SC_LEVELS = {"H": 0.1, "L": 0.2, "N": 0.3}
_SI_LEVELS = {"S": 0.0, "H": 0.1, "L": 0.2, "N": 0.3}
_SA_LEVELS = {"S": 0.0, "H": 0.1, "L": 0.2, "N": 0.3}
_CR_LEVELS = {"H": 0.0, "M": 0.1, "L": 0.2}
_IR_LEVELS = {"H": 0.0, "M": 0.1, "L": 0.2}
_AR_LEVELS = {"H": 0.0, "M": 0.1, "L": 0.2}


def _parse(vector: str) -> dict[str, str]:
    if vector.startswith("CVSS:3"):
        raise ValueError(
            f"CVSS 3.x vector is no longer supported; re-derive as CVSS:4.0 ({vector})"
        )
    if not vector.startswith("CVSS:4.0/"):
        raise ValueError(f"not a CVSS 4.0 vector: {vector}")
    metrics: dict[str, str] = {}
    for part in vector.split("/")[1:]:
        k, _, v = part.partition(":")
        metrics[k] = v
    missing = [k for k in _REQUIRED if k not in metrics]
    if missing:
        raise ValueError(f"malformed CVSS 4.0 vector, missing {missing}: {vector}")
    for k in _REQUIRED:
        if metrics[k] not in _ALLOWED[k]:
            raise ValueError(f"invalid CVSS 4.0 value {k}:{metrics[k]}")
    for k, v in metrics.items():
        if k in _REQUIRED:
            continue
        if v == "X":  # Not Defined -> no-op, matches the base-only defaults
            continue
        if k in ("E", "CR", "IR", "AR") or k.startswith("M"):
            raise ValueError(
                f"this engine scores base metrics only; {k}:{v} affects score: {vector}"
            )
    return metrics


def _m(metrics: dict[str, str], metric: str) -> str:
    """Metric accessor with the reference's worst-case defaults for unsupported metrics.

    Base-only: E always defaults to "A" (no threat metric accepted), CR/IR/AR
    always default to "H" (no environmental metric accepted), and modified
    (M*) metrics are never present so they never override a base value.
    `metric` is always one of the 11 base metrics or E/CR/IR/AR here, and
    ``_parse`` already guarantees every base metric is present.
    """
    if metric == "E":
        return "A"
    if metric in ("CR", "IR", "AR"):
        return "H"
    return metrics[metric]


def _macrovector(metrics: dict[str, str]) -> str:
    """Compute the six-digit EQ1..EQ6 MacroVector, ported from macroVector()."""
    av, pr, ui = _m(metrics, "AV"), _m(metrics, "PR"), _m(metrics, "UI")
    if av == "N" and pr == "N" and ui == "N":
        eq1 = "0"
    elif av != "P" and (av == "N" or pr == "N" or ui == "N"):
        eq1 = "1"
    else:
        eq1 = "2"

    ac, at = _m(metrics, "AC"), _m(metrics, "AT")
    eq2 = "0" if (ac == "L" and at == "N") else "1"

    vc, vi, va = _m(metrics, "VC"), _m(metrics, "VI"), _m(metrics, "VA")
    if vc == "H" and vi == "H":
        eq3 = "0"
    elif vc == "H" or vi == "H" or va == "H":
        eq3 = "1"
    else:
        eq3 = "2"

    sc, si, sa = _m(metrics, "SC"), _m(metrics, "SI"), _m(metrics, "SA")
    # MSI/MSA are never supplied (base-only), so the "S" (Safety) shortcut never fires.
    eq4 = "1" if (sc == "H" or si == "H" or sa == "H") else "2"

    eq5 = "0"  # E defaults to "A" under base-only scoring.

    cr, ir, ar = _m(metrics, "CR"), _m(metrics, "IR"), _m(metrics, "AR")
    high_impact = (cr == "H" and vc == "H") or (ir == "H" and vi == "H") or (ar == "H" and va == "H")
    eq6 = "0" if high_impact else "1"

    return eq1 + eq2 + eq3 + eq4 + eq5 + eq6


def _extract_value_metric(metric: str, fragment: str) -> str:
    """Pull one metric's value out of a "K:V/K:V/.../" MAX_COMPOSED fragment."""
    start = fragment.index(metric) + len(metric) + 1
    rest = fragment[start:]
    end = rest.find("/")
    return rest[:end] if end > 0 else rest


def _get_eq_maxes(mv: str, eq: int) -> list[str]:
    if eq == 3:
        return MAX_COMPOSED["eq3"][mv[2]][mv[5]]
    return MAX_COMPOSED[f"eq{eq}"][mv[eq - 1]]


def _interpolated_score(metrics: dict[str, str], mv: str) -> float:
    """Port of cvss_score.js's mean-distance interpolation against the lookup table."""
    value = MACROVECTOR_LOOKUP[mv]
    eq1, eq2, eq3, eq4, eq5, eq6 = mv[0], mv[1], mv[2], mv[3], mv[4], mv[5]

    lower_eq1 = MACROVECTOR_LOOKUP.get(f"{int(eq1) + 1}{eq2}{eq3}{eq4}{eq5}{eq6}")
    lower_eq2 = MACROVECTOR_LOOKUP.get(f"{eq1}{int(eq2) + 1}{eq3}{eq4}{eq5}{eq6}")
    lower_eq4 = MACROVECTOR_LOOKUP.get(f"{eq1}{eq2}{eq3}{int(eq4) + 1}{eq5}{eq6}")
    lower_eq5 = MACROVECTOR_LOOKUP.get(f"{eq1}{eq2}{eq3}{eq4}{int(eq5) + 1}{eq6}")

    if (eq3 == "1" and eq6 == "1") or (eq3 == "0" and eq6 == "1"):
        lower_eq3eq6 = MACROVECTOR_LOOKUP.get(f"{eq1}{eq2}{int(eq3) + 1}{eq4}{eq5}{eq6}")
    elif eq3 == "1" and eq6 == "0":
        lower_eq3eq6 = MACROVECTOR_LOOKUP.get(f"{eq1}{eq2}{eq3}{eq4}{eq5}{int(eq6) + 1}")
    elif eq3 == "0" and eq6 == "0":
        left = MACROVECTOR_LOOKUP.get(f"{eq1}{eq2}{eq3}{eq4}{eq5}{int(eq6) + 1}")
        right = MACROVECTOR_LOOKUP.get(f"{eq1}{eq2}{int(eq3) + 1}{eq4}{eq5}{eq6}")
        if left is None:
            lower_eq3eq6 = right
        elif right is None:
            lower_eq3eq6 = left
        else:
            lower_eq3eq6 = max(left, right)
    else:  # eq3 == "2" (eq6 must be "1"): no lower MacroVector exists.
        lower_eq3eq6 = MACROVECTOR_LOOKUP.get(f"{eq1}{eq2}{int(eq3) + 1}{eq4}{eq5}{int(eq6) + 1}")

    eq1_maxes = _get_eq_maxes(mv, 1)
    eq2_maxes = _get_eq_maxes(mv, 2)
    eq3_eq6_maxes = _get_eq_maxes(mv, 3)
    eq4_maxes = _get_eq_maxes(mv, 4)
    eq5_maxes = _get_eq_maxes(mv, 5)

    dist_av = dist_pr = dist_ui = dist_ac = dist_at = 0.0
    dist_vc = dist_vi = dist_va = dist_sc = dist_si = dist_sa = 0.0
    dist_cr = dist_ir = dist_ar = 0.0
    for e1_max, e2_max, e3e6_max, e4_max, e5_max in product(
        eq1_maxes, eq2_maxes, eq3_eq6_maxes, eq4_maxes, eq5_maxes
    ):
        max_vector = e1_max + e2_max + e3e6_max + e4_max + e5_max
        dist_av = _AV_LEVELS[_m(metrics, "AV")] - _AV_LEVELS[_extract_value_metric("AV", max_vector)]
        dist_pr = _PR_LEVELS[_m(metrics, "PR")] - _PR_LEVELS[_extract_value_metric("PR", max_vector)]
        dist_ui = _UI_LEVELS[_m(metrics, "UI")] - _UI_LEVELS[_extract_value_metric("UI", max_vector)]
        dist_ac = _AC_LEVELS[_m(metrics, "AC")] - _AC_LEVELS[_extract_value_metric("AC", max_vector)]
        dist_at = _AT_LEVELS[_m(metrics, "AT")] - _AT_LEVELS[_extract_value_metric("AT", max_vector)]
        dist_vc = _VC_LEVELS[_m(metrics, "VC")] - _VC_LEVELS[_extract_value_metric("VC", max_vector)]
        dist_vi = _VI_LEVELS[_m(metrics, "VI")] - _VI_LEVELS[_extract_value_metric("VI", max_vector)]
        dist_va = _VA_LEVELS[_m(metrics, "VA")] - _VA_LEVELS[_extract_value_metric("VA", max_vector)]
        dist_sc = _SC_LEVELS[_m(metrics, "SC")] - _SC_LEVELS[_extract_value_metric("SC", max_vector)]
        dist_si = _SI_LEVELS[_m(metrics, "SI")] - _SI_LEVELS[_extract_value_metric("SI", max_vector)]
        dist_sa = _SA_LEVELS[_m(metrics, "SA")] - _SA_LEVELS[_extract_value_metric("SA", max_vector)]
        dist_cr = _CR_LEVELS[_m(metrics, "CR")] - _CR_LEVELS[_extract_value_metric("CR", max_vector)]
        dist_ir = _IR_LEVELS[_m(metrics, "IR")] - _IR_LEVELS[_extract_value_metric("IR", max_vector)]
        dist_ar = _AR_LEVELS[_m(metrics, "AR")] - _AR_LEVELS[_extract_value_metric("AR", max_vector)]
        if all(
            d >= 0
            for d in (
                dist_av, dist_pr, dist_ui, dist_ac, dist_at,
                dist_vc, dist_vi, dist_va, dist_sc, dist_si, dist_sa,
                dist_cr, dist_ir, dist_ar,
            )
        ):
            break

    current_eq1 = dist_av + dist_pr + dist_ui
    current_eq2 = dist_ac + dist_at
    current_eq3eq6 = dist_vc + dist_vi + dist_va + dist_cr + dist_ir + dist_ar
    current_eq4 = dist_sc + dist_si + dist_sa

    step = 0.1
    max_sev_eq1 = MAX_SEVERITY["eq1"][eq1] * step
    max_sev_eq2 = MAX_SEVERITY["eq2"][eq2] * step
    max_sev_eq3eq6 = MAX_SEVERITY["eq3eq6"][eq3][eq6] * step
    max_sev_eq4 = MAX_SEVERITY["eq4"][eq4] * step

    n_existing_lower = 0
    normalized = 0.0
    for lower, current, max_sev in (
        (lower_eq1, current_eq1, max_sev_eq1),
        (lower_eq2, current_eq2, max_sev_eq2),
        (lower_eq3eq6, current_eq3eq6, max_sev_eq3eq6),
        (lower_eq4, current_eq4, max_sev_eq4),
    ):
        if lower is not None:
            n_existing_lower += 1
            available_distance = value - lower
            normalized += available_distance * (current / max_sev)
    if lower_eq5 is not None:
        # eq5's percentage is always 0 (E is fixed at its worst-case "A").
        n_existing_lower += 1

    mean_distance = normalized / n_existing_lower if n_existing_lower else 0.0
    score = value - mean_distance
    score = max(0.0, min(10.0, score))
    return math.floor(score * 10 + 0.5) / 10.0


def _rating(score: float) -> str:
    """Map a base score to its qualitative band."""
    if score == 0.0:
        return "None"
    if score < 4.0:
        return "Low"
    if score < 7.0:
        return "Medium"
    if score < 9.0:
        return "High"
    return "Critical"


def cvss40_base(vector: str) -> tuple[float, str]:
    """Compute the CVSS v4.0 base score and rating for a vector string.

    Args:
        vector: A CVSS 4.0 vector (``CVSS:4.0/AV:.../SA:H``), base metrics only.

    Returns:
        ``(base_score, rating)``.

    Raises:
        ValueError: If the vector is a CVSS 3.x vector, or is missing/has
            invalid base metrics.

    Example:
        >>> cvss40_base("CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N")
        (9.3, 'Critical')
    """
    m = _parse(vector)
    if all(m[k] == "N" for k in ("VC", "VI", "VA", "SC", "SI", "SA")):
        return 0.0, "None"
    score = _interpolated_score(m, _macrovector(m))
    return score, _rating(score)


def offensive_priority(vector: str, *, externally_facing: bool = False) -> str:
    """Rank exploitability/reachability P1 (worst) .. P4, orthogonal to severity.

    Args:
        vector: A CVSS 4.0 vector.
        externally_facing: Optional hint that the component is externally reachable.

    Returns:
        ``"P1".."P4"``.

    Example:
        >>> offensive_priority("CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N")
        'P1'
    """
    m = _parse(vector)
    av, pr = m["AV"], m["PR"]
    if av == "N" and pr == "N":
        return "P1"
    if av == "N" and pr == "L":
        return "P2"
    if externally_facing and pr != "H":
        return "P2"
    if av in ("A", "L") or pr == "H":
        return "P3"
    return "P4"
