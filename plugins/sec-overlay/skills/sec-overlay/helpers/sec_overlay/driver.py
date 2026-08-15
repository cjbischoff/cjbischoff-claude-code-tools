"""Deterministic phase-driver for a sec-overlay audit run.

The driver walks ``phases.PHASE_TABLE``. It runs a deterministic phase's action
and records its stage, or — for an agent phase — prints the exact dispatch and
stops until the orchestrator produces the phase's declared outputs. It never
calls a model: agents stay external and independent.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass

from sec_overlay.calibrate import calibrate_findings
from sec_overlay.campaign import record_stage
from sec_overlay.dedupe import dedupe_findings
from sec_overlay.factcheck import apply_verdict, validate_verdict
from sec_overlay.findings_gate import validate_findings
from sec_overlay.partition import demote_noise, reconcile_plan, unrouted_candidate_classes
from sec_overlay.phases import (
    PHASE_TABLE,
    PhaseSpec,
    missing_inputs,
    next_actionable_phase,
    outputs_present,
)
from sec_overlay.prefilter import run_prefilter
from sec_overlay.profile import ScanProfile, load_profile
from sec_overlay.redactor import safe_for_prompt
from sec_overlay.report import write_report
from sec_overlay.selfscore import write_self_score
from sec_overlay.state import load_state
from sec_overlay.verify import verify_findings
from sec_overlay.workspace import Workspace, read_findings, write_findings


@dataclass
class AuditContext:
    """Everything a deterministic phase action needs.

    Attributes:
        ws: The audit workspace.
        target: Path to the target repository.
        config: Semgrep/ruleset config path for scanning phases.
        sha: The pinned target SHA for this pass.
        profile: The recon scan profile, loaded lazily when a phase needs it.
    """

    ws: Workspace
    target: str
    config: str
    sha: str
    profile: ScanProfile | None = None


class PhaseHalt(RuntimeError):
    """A phase could not start or did not finish. The run stops loudly."""


# name -> action. Populated in Task 4; kept module-level so phases resolve by name.
DETERMINISTIC_ACTIONS: dict[str, Callable[[AuditContext], None]] = {}


def run_deterministic_phase(phase: PhaseSpec, ctx: AuditContext) -> None:
    """Run one deterministic phase, gating on inputs and outputs.

    Args:
        phase: The phase to run.
        ctx: The audit context the phase's action operates against.

    Raises:
        PhaseHalt: An input artifact is missing, no action is registered, or the
            action ran but a declared output artifact is still absent.
    """
    absent = missing_inputs(phase, ctx.ws)
    if absent:
        raise PhaseHalt(
            f"phase {phase.name!r} cannot start: missing input(s) "
            + ", ".join(str(p) for p in absent)
        )
    action = DETERMINISTIC_ACTIONS.get(phase.name)
    if action is None:
        raise PhaseHalt(f"phase {phase.name!r} has no registered action")
    action(ctx)
    if not outputs_present(phase, ctx.ws):
        missing = [str(p(ctx.ws)) for p in phase.outputs if not p(ctx.ws).exists()]
        raise PhaseHalt(f"phase {phase.name!r} did not produce: " + ", ".join(missing))
    record_stage(ctx.ws, phase.name)


def render_dispatch(
    phase: PhaseSpec, ctx: AuditContext, *, classes: list[str] | None = None
) -> str:
    """Return the dispatch block for an agent phase.

    The orchestrator runs the model; this only tells it which prompt to run and
    what to substitute. Advancement happens later, when the phase's declared
    outputs exist.

    Args:
        phase: The agent phase to dispatch.
        ctx: The audit context threaded through the run.
        classes: Attack classes to fan out to (e.g. investigate's reconciled
            plan). Omitted from the block when ``None``.

    Raises:
        ValueError: ``phase`` has no prompt (it is a deterministic phase, not
            an agent phase — ``render_dispatch`` only ever applies to agents).
    """
    if phase.prompt is None:
        raise ValueError(f"render_dispatch requires an agent phase; {phase.name!r} has no prompt")
    outputs = ", ".join(str(p(ctx.ws)) for p in phase.outputs) or "(none)"
    class_line = ""
    if classes:
        class_line = "\n  {{ATTACK_CLASS}}=" + ",".join(classes)
    block = (
        f"NEXT AGENT PHASE: {phase.name}\n"
        f"  prompt: agents/{phase.prompt}\n"
        f"  substitute: {{{{TARGET}}}}={ctx.target} "
        f"{{{{WORKSPACE}}}}={ctx.ws.root} {{{{SHA}}}}={ctx.sha}"
        f"{class_line}\n"
        f"  required outputs before advancing: {outputs}"
    )
    return safe_for_prompt(block)


def unrouted_triage_dispatch(ctx: AuditContext, agents_to_spawn: list[str]) -> str | None:
    """Return a general-triage dispatch for candidate classes not in the plan.

    Returns None when every candidate class is already routed to an agent.

    Args:
        ctx: The audit context threaded through the run.
        agents_to_spawn: The reconciled ``agents_to_spawn`` list.

    Returns:
        A dispatch block naming each unrouted class and its candidate count,
        or ``None`` when nothing is unrouted.
    """
    unrouted = unrouted_candidate_classes(ctx.ws, agents_to_spawn)
    if not unrouted:
        return None
    rows = ", ".join(f"{cls}={n}" for cls, n in sorted(unrouted.items()))
    return (
        "UNROUTED CANDIDATE CLASSES — spawn general triage\n"
        "  prompt: agents/investigate.md (general-triage)\n"
        f"  classes: {rows}\n"
        f"  substitute: {{{{TARGET}}}}={ctx.target} {{{{WORKSPACE}}}}={ctx.ws.root}"
    )


def _load_profile(ctx: AuditContext) -> ScanProfile:
    """Return the recon-produced scan profile, caching it on the context."""
    if ctx.profile is None:
        ctx.profile = load_profile(ctx.ws.kb / "scan-profile.json")
    return ctx.profile


def _act_prefilter(ctx: AuditContext) -> None:
    run_prefilter(ctx.ws, ctx.target, _load_profile(ctx))


def _act_findings_gate(ctx: AuditContext) -> None:
    validate_findings(ctx.ws)  # records its own stage too; harmless


def _act_dedupe(ctx: AuditContext) -> None:
    dedupe_findings(ctx.ws)


def _act_demote_noise(ctx: AuditContext) -> None:
    demote_noise(ctx.ws)


def _act_verify(ctx: AuditContext) -> None:
    verify_findings(ctx.ws, ctx.target, ctx.config)


def _act_selfscore(ctx: AuditContext) -> None:
    write_self_score(ctx.ws)


def _act_factcheck(ctx: AuditContext) -> None:
    """Apply verdicts from ``kb/verdicts.json`` to their findings, if present.

    ``verdicts.json`` is written by a fact-check agent (Plan B) re-verifying a
    confirmed finding's citations/scope/severity against source. Until that
    agent exists, the file is absent and this phase no-ops silently — the
    input is deliberately not a hard gate (see phases.py), so a missing
    verdict artifact never halts the run.

    Args:
        ctx: The audit context; reads/writes findings in ``ctx.ws``.
    """
    verdicts_path = ctx.ws.kb / "verdicts.json"
    if not verdicts_path.exists():
        return
    verdicts = json.loads(verdicts_path.read_text())
    findings = {f.id: f for f in read_findings(ctx.ws)}
    changed = []
    for fid, d in verdicts.items():
        if fid in findings and not validate_verdict(d):
            changed.append(apply_verdict(findings[fid], d))
    if changed:
        write_findings(ctx.ws, list(findings.values()))


def _act_calibrate(ctx: AuditContext) -> None:
    calibrate_findings(ctx.ws)


def _act_report(ctx: AuditContext) -> None:
    write_report(ctx.ws, target=ctx.target)


DETERMINISTIC_ACTIONS.update(
    {
        "prefilter": _act_prefilter,
        "findings-gate": _act_findings_gate,
        "dedupe": _act_dedupe,
        "factcheck": _act_factcheck,
        "calibrate": _act_calibrate,
        "verify": _act_verify,
        "demote-noise": _act_demote_noise,
        "report": _act_report,
        "selfscore": _act_selfscore,
    }
)


def run_audit(ctx: AuditContext, *, table: tuple[PhaseSpec, ...] = PHASE_TABLE) -> str:
    """Walk the phase table from the first phase not yet recorded ``done``.

    Runs each deterministic phase in place. On an agent phase, auto-advances
    only when the phase has at least one output path that is not also one of
    its input paths (an output-only artifact proves the agent actually ran;
    several agent phases share ``findings_dir`` as both input and output, and
    the dir's mere presence there proves nothing about that specific phase).
    Otherwise returns the phase's dispatch block and stops.

    Args:
        ctx: The audit context threaded through every phase action.
        table: The phase table to walk (defaults to ``PHASE_TABLE``).

    Returns:
        ``"AUDIT COMPLETE"`` once every phase is recorded ``done``, or the
        dispatch block for the next agent phase awaiting a model run.
    """
    while True:
        phase = next_actionable_phase(table, load_state(ctx.ws))
        if phase is None:
            return "AUDIT COMPLETE"
        if phase.kind == "deterministic":
            run_deterministic_phase(phase, ctx)
            continue
        distinct_outputs = tuple(p for p in phase.outputs if p not in phase.inputs)
        if distinct_outputs and all(p(ctx.ws).exists() for p in distinct_outputs):
            record_stage(ctx.ws, phase.name)
            continue
        if phase.name == "investigate":
            profile = json.loads((ctx.ws.kb / "scan-profile.json").read_text())
            planned = list(profile.get("agents_to_spawn", []))
            reconciled = reconcile_plan(ctx.ws, planned)  # ISSUE-006: recon-omitted classes
            block = render_dispatch(phase, ctx, classes=reconciled)
            triage = unrouted_triage_dispatch(ctx, reconciled)
            return block if triage is None else block + "\n" + triage
        return render_dispatch(phase, ctx)
