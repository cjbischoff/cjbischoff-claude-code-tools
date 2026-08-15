"""Deterministic phase-driver for a sec-overlay audit run.

The driver walks ``phases.PHASE_TABLE``. It runs a deterministic phase's action
and records its stage, or — for an agent phase — prints the exact dispatch and
stops until the orchestrator produces the phase's declared outputs. It never
calls a model: agents stay external and independent.
"""

from collections.abc import Callable
from dataclasses import dataclass

from sec_overlay.campaign import record_stage
from sec_overlay.phases import PhaseSpec, missing_inputs, outputs_present
from sec_overlay.profile import ScanProfile
from sec_overlay.workspace import Workspace


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
