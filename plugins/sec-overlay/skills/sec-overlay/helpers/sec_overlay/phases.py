"""Ordered phase table and pure sequencer helpers for the audit driver.

The table is the single source of within-run phase order. Each phase declares
the artifacts that must exist before it may start (``inputs``) and the artifacts
that must exist for it to count as finished (``outputs``). Agent phases also name
the ``agents/<prompt>.md`` the orchestrator must run.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from sec_overlay.kb import arc42_path, container_diagram_path, dfd_path, threat_model_path
from sec_overlay.models import CampaignState
from sec_overlay.workspace import Workspace

PathOf = Callable[[Workspace], Path]


@dataclass(frozen=True)
class PhaseSpec:
    """One pipeline phase.

    Attributes:
        name: The ``record_stage`` key; unique within the table.
        kind: ``"deterministic"`` (the driver runs it) or ``"agent"`` (the
            orchestrator runs a model; the driver prints the dispatch).
        inputs: Callables returning artifact paths that must exist to start.
        outputs: Callables returning artifact paths that must exist to finish.
        prompt: For an agent phase, the ``agents/<file>.md`` prompt name.
    """

    name: str
    kind: str
    inputs: tuple[PathOf, ...] = ()
    outputs: tuple[PathOf, ...] = ()
    prompt: str | None = None


def _profile(ws: Workspace) -> Path:
    return ws.kb / "scan-profile.json"


def _arc42(ws: Workspace) -> Path:
    return arc42_path(ws)


def _container(ws: Workspace) -> Path:
    return container_diagram_path(ws)


def _tm_doc(ws: Workspace) -> Path:
    return threat_model_path(ws)


def _dfd(ws: Workspace) -> Path:
    return dfd_path(ws)


def _arch_gate_json(ws: Workspace) -> Path:
    return ws.kb / "gates" / "arch-gate.json"


def _tm_gate_json(ws: Workspace) -> Path:
    return ws.kb / "gates" / "tm-gate.json"


def _findings_dir(ws: Workspace) -> Path:
    return ws.findings_dir


def _report(ws: Workspace) -> Path:
    return ws.report_path


def _sarif(ws: Workspace) -> Path:
    return ws.sarif_path


def _artifact_gate_json(ws: Workspace) -> Path:
    return ws.kb / "gates" / "artifact-gate.json"


def _artifact_review_json(ws: Workspace) -> Path:
    return ws.kb / "gates" / "artifact-review.json"


PHASE_TABLE: tuple[PhaseSpec, ...] = (
    PhaseSpec("recon", "agent", (), (_profile,), prompt="recon.md"),
    PhaseSpec("architecture", "agent", (_profile,), (_arc42, _container), prompt="architecture.md"),
    PhaseSpec("arch-gate", "deterministic", (_arc42, _container), (_arch_gate_json,)),
    PhaseSpec(
        "threat_model", "agent", (_arch_gate_json,), (_tm_doc, _dfd), prompt="threat-model.md"
    ),
    PhaseSpec("tm-gate", "deterministic", (_tm_doc, _dfd), (_tm_gate_json,)),
    PhaseSpec("prefilter", "deterministic", (_profile,), (_findings_dir,)),
    PhaseSpec("investigate", "agent", (_findings_dir,), (_findings_dir,), prompt="investigate.md"),
    PhaseSpec("findings-gate", "deterministic", (_findings_dir,), (_findings_dir,)),
    PhaseSpec("dedupe", "deterministic", (_findings_dir,), (_findings_dir,)),
    PhaseSpec("critic", "agent", (_findings_dir,), (_findings_dir,), prompt="critic.md"),
    PhaseSpec("judge", "agent", (_findings_dir,), (_findings_dir,), prompt="judge.md"),
    PhaseSpec("validate", "agent", (_findings_dir,), (_findings_dir,), prompt="validate.md"),
    PhaseSpec("trace", "agent", (_findings_dir,), (_findings_dir,), prompt="trace.md"),
    # No inputs/outputs declared: kb/verdicts.json is optional (Plan B emits the
    # fact-check agent that writes it) and a hard input gate would halt every run
    # until then. _act_factcheck no-ops silently when the file is absent.
    PhaseSpec("factcheck", "deterministic", (), ()),
    PhaseSpec("calibrate", "deterministic", (_findings_dir,), (_findings_dir,)),
    PhaseSpec("patch", "agent", (_findings_dir,), (_findings_dir,), prompt="patch.md"),
    PhaseSpec("verify", "deterministic", (_findings_dir,), (_findings_dir,)),
    PhaseSpec("demote-noise", "deterministic", (_findings_dir,), (_findings_dir,)),
    PhaseSpec("report", "deterministic", (_findings_dir,), (_report, _sarif)),
    PhaseSpec("selfscore", "deterministic", (_report,), (_findings_dir,)),
    PhaseSpec("artifact-gate", "deterministic", (_report, _sarif), (_artifact_gate_json,)),
    PhaseSpec(
        "artifact-review",
        "agent",
        (_artifact_gate_json,),
        (_artifact_review_json,),
        prompt="artifact-review.md",
    ),
)


def missing_inputs(phase: PhaseSpec, ws: Workspace) -> list[Path]:
    """Return the phase's input paths that do not exist."""
    return [p(ws) for p in phase.inputs if not p(ws).exists()]


def outputs_present(phase: PhaseSpec, ws: Workspace) -> bool:
    """Return True when every declared output path exists."""
    return all(p(ws).exists() for p in phase.outputs)


def next_actionable_phase(table: tuple[PhaseSpec, ...], state: CampaignState) -> PhaseSpec | None:
    """Return the first phase not recorded ``done`` in state, or None."""
    for phase in table:
        if state.stages.get(phase.name) != "done":
            return phase
    return None
