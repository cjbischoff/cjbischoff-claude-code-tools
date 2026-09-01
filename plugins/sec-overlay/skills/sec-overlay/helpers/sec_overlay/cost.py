"""Per-phase wall-clock accounting over CampaignState.budget.

The driver measures each deterministic phase with ``time.perf_counter`` and records the
elapsed seconds via :func:`record_timing`; the records live in the existing free-form
``CampaignState.budget`` dict (no contract change). Wall-clock is the only measured
figure this module holds. Token totals were removed at plugin 2.1.9: the harness never
surfaced a subagent's usage, so every token table rendered empty and every USD figure
rendered as zero.
"""

from __future__ import annotations

from sec_overlay.models import CampaignState


def record_timing(state: CampaignState, phase: str, seconds: float) -> None:
    """Append one phase's wall-clock duration to the campaign budget.

    Args:
        state: Campaign state to mutate.
        phase: Pipeline phase name (e.g. ``"prefilter"``).
        seconds: Wall-clock seconds the phase took.
    """
    state.budget.setdefault("timings", []).append(
        {"phase": phase, "seconds": float(seconds)}
    )


def aggregate_timings_by_phase(state: CampaignState) -> dict[str, float]:
    """Sum recorded wall-clock seconds by phase.

    Args:
        state: Campaign state holding budget timings.

    Returns:
        ``{phase: total_seconds}`` (empty when nothing was recorded).
    """
    out: dict[str, float] = {}
    for rec in state.budget.get("timings", []):
        out[rec["phase"]] = out.get(rec["phase"], 0.0) + float(rec.get("seconds", 0.0))
    return out
