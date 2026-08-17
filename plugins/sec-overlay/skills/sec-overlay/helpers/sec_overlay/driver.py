"""Deterministic phase-driver for a sec-overlay audit run.

The driver walks ``phases.PHASE_TABLE``. It runs a deterministic phase's action
and records its stage, or — for an agent phase — prints the exact dispatch and
stops until the orchestrator produces the phase's declared outputs. It never
calls a model: agents stay external and independent.
"""

import json
import time
from collections.abc import Callable
from dataclasses import dataclass

from sec_overlay import cost
from sec_overlay.calibrate import calibrate_findings
from sec_overlay.campaign import record_stage
from sec_overlay.dedupe import dedupe_findings
from sec_overlay.factcheck import apply_verdict, validate_verdict
from sec_overlay.findings_gate import validate_citations, validate_findings
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
from sec_overlay.state import load_state, save_state
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


def run_deterministic_phase(
    phase: PhaseSpec, ctx: AuditContext, *, on_complete: Callable[[str], None] | None = None
) -> None:
    """Run one deterministic phase, gating on inputs and outputs.

    Args:
        phase: The phase to run.
        ctx: The audit context the phase's action operates against.
        on_complete: Optional callback invoked with ``phase.name`` right before the
            stage is recorded done (e.g. to fence the tree and write a receipt).

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
    start = time.perf_counter()
    action(ctx)
    elapsed = time.perf_counter() - start
    if not outputs_present(phase, ctx.ws):
        missing = [str(p(ctx.ws)) for p in phase.outputs if not p(ctx.ws).exists()]
        raise PhaseHalt(f"phase {phase.name!r} did not produce: " + ", ".join(missing))
    state = load_state(ctx.ws)
    cost.record_timing(state, phase.name, elapsed)
    save_state(ctx.ws, state)
    if on_complete is not None:
        on_complete(phase.name)
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
    errors = validate_findings(ctx.ws)  # records its own stage too
    errors += validate_citations(ctx.ws, ctx.target)
    if errors:
        raise PhaseHalt(
            f"findings-gate rejected {len(errors)} finding(s): " + "; ".join(errors)
        )


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


def _act_artifact_gate(ctx: AuditContext) -> None:
    from sec_overlay.artifact_gate import run_artifact_gate  # local: avoid import cycle

    errors = run_artifact_gate(ctx.ws)
    if errors:
        raise PhaseHalt(
            f"artifact-gate rejected {len(errors)} issue(s): " + "; ".join(errors)
        )


def _write_gate(ws: Workspace, name: str, errors: list[str], warnings: list[str]) -> None:
    (ws.kb / "gates").mkdir(parents=True, exist_ok=True)
    (ws.kb / "gates" / f"{name}.json").write_text(
        json.dumps({"passed": not errors, "errors": errors, "warnings": warnings}, indent=2)
    )


def _act_arch_gate(ctx: AuditContext) -> None:
    from sec_overlay.diagram_gate import run_diagram_gate
    from sec_overlay.ste_lint import lint_prose

    arch = ctx.ws.root / "architecture"
    # run_diagram_gate existence-guards the threat-model files, so an absent
    # tm tree at arch-gate time produces no spurious errors
    errors = run_diagram_gate(arch, ctx.ws.root / "threat-model")
    prose_errors, warnings = lint_prose((arch / "arc42.md").read_text())
    errors += [f"arc42.md: {e}" for e in prose_errors]
    if "ASD-STE100" not in (arch / "arc42.md").read_text():
        errors.append("arc42.md: missing ASD-STE100 limitation statement")
    _write_gate(ctx.ws, "arch-gate", errors, warnings)
    if errors:
        raise PhaseHalt(f"arch-gate rejected {len(errors)} issue(s): " + "; ".join(errors))


def _act_tm_gate(ctx: AuditContext) -> None:
    from sec_overlay.artifact_gate import check_duplication
    from sec_overlay.diagram_gate import run_diagram_gate
    from sec_overlay.ste_lint import lint_prose

    arch = ctx.ws.root / "architecture"
    tm = ctx.ws.root / "threat-model"
    errors = run_diagram_gate(arch, tm, require_threat_model=True)
    tm_text = (tm / "threat-model.md").read_text()
    prose_errors, warnings = lint_prose(tm_text)
    errors += [f"threat-model.md: {e}" for e in prose_errors]
    if "ASD-STE100" not in tm_text:
        errors.append("threat-model.md: missing ASD-STE100 limitation statement")
    errors += check_duplication((arch / "arc42.md").read_text(), tm_text)
    _write_gate(ctx.ws, "tm-gate", errors, warnings)
    if errors:
        raise PhaseHalt(f"tm-gate rejected {len(errors)} issue(s): " + "; ".join(errors))


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
        "artifact-gate": _act_artifact_gate,
        "arch-gate": _act_arch_gate,
        "tm-gate": _act_tm_gate,
    }
)


def run_audit(
    ctx: AuditContext,
    *,
    table: tuple[PhaseSpec, ...] = PHASE_TABLE,
    on_complete: Callable[[str], None] | None = None,
) -> str:
    """Walk the phase table from the first phase not yet recorded ``done``.

    Runs each deterministic phase in place. On an agent phase, auto-advances
    only when the phase has at least one output path that is not also one of
    its input paths (an output-only artifact proves the agent actually ran;
    several agent phases share ``findings_dir`` as both input and output, and
    the dir's mere presence there proves nothing about that specific phase).
    Otherwise returns the phase's dispatch block and stops. The output-exists
    gate in ``run_deterministic_phase`` only ever fires for ``report`` — the
    other deterministic phases' declared output is ``findings_dir``, which is
    already present by the time they run, so a missing finding file is not,
    by design, treated as that phase's failure. ``recon``/``architecture``/
    ``threat_model`` auto-record via their own distinct output file; the six
    ``findings_dir``-in/out agent phases (investigate, critic, judge,
    validate, trace, patch) never auto-advance and require the orchestrator
    to call ``record_stage`` manually once its output is ready.

    Args:
        ctx: The audit context threaded through every phase action.
        table: The phase table to walk (defaults to ``PHASE_TABLE``).
        on_complete: Optional callback invoked with a phase's name right before
            that phase's stage is recorded done (deterministic phases and the
            auto-advance agent-phase branch only; not the dispatch-and-stop path).

    Returns:
        ``"AUDIT COMPLETE"`` once every phase is recorded ``done``, or the
        dispatch block for the next agent phase awaiting a model run.
    """
    while True:
        phase = next_actionable_phase(table, load_state(ctx.ws))
        if phase is None:
            return "AUDIT COMPLETE"
        if phase.kind == "deterministic":
            run_deterministic_phase(phase, ctx, on_complete=on_complete)
            continue
        distinct_outputs = tuple(p for p in phase.outputs if p not in phase.inputs)
        if distinct_outputs and all(p(ctx.ws).exists() for p in distinct_outputs):
            if on_complete is not None:
                on_complete(phase.name)
            record_stage(ctx.ws, phase.name)
            continue
        if phase.name in ("investigate", "patch"):
            try:
                profile = json.loads((ctx.ws.kb / "scan-profile.json").read_text())
            except (FileNotFoundError, json.JSONDecodeError):
                raise PhaseHalt(
                    f"phase {phase.name!r} cannot start: missing or malformed "
                    "scan-profile.json"
                ) from None
            planned = list(profile.get("agents_to_spawn", []))
            reconciled = reconcile_plan(ctx.ws, planned)  # ISSUE-006: recon-omitted classes
            block = render_dispatch(phase, ctx, classes=reconciled)
            if phase.name != "investigate":
                return block
            triage = unrouted_triage_dispatch(ctx, reconciled)
            return block if triage is None else block + "\n" + triage
        return render_dispatch(phase, ctx)
