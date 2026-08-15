# sec-overlay audit driver (Plan A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic `sec_overlay.cli audit` phase-driver that owns phase order, gates advancement on artifact preconditions, halts loudly on a missing output, prints the next agent dispatch, is resumable, and wires the six tested-but-unwired modules — replacing the SKILL.md prose ladder as the authority on within-run sequencing.

**Architecture:** A frozen phase table (`phases.py`) declares each phase's kind, input artifacts, output artifacts, and — for agent phases — its prompt file. A stdlib-only sequencer (`driver.py`) walks the table: it runs a deterministic phase's action and records its stage, or for an agent phase prints the exact dispatch and stops until the orchestrator produces the phase's declared outputs. Agents stay external and independent — the driver never calls a model. This is Plan A of four (see spec §7); it produces the substrate Plans B–D read.

**Tech Stack:** Python 3.13, stdlib only (no runtime deps), `pytest`, `ruff`, `ty`. Package at `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/`; tests at `.../helpers/tests/`; run from `.../helpers/`.

**Spec:** `docs/superpowers/specs/2026-08-15-sec-overlay-defect-remediation-design.md` (theme T1, §4.1; traceability rows 001, 002, 006, 007, 015, 030, 038, 039, 044, 045, 047, 050, 051, 053).

## Global Constraints

Every task's commit implicitly includes these. Values are copied verbatim from the spec and repo governance.

- **Stdlib-only core.** No new entry in `pyproject.toml` `dependencies`. Dev deps stay `pytest`, `ruff`, `ty`.
- **TDD order.** Write the failing test first, run it, watch it fail for the stated reason, then implement. The commit bundles test + implementation (governance requires logic and its test in the same change).
- **Line length 100.** `ruff` config; keep every line ≤100 chars.
- **Absolute imports only** inside the package: `from sec_overlay.x import y` — never `from .x import y` in new code if the package convention is absolute (match the file you edit; existing modules use `from sec_overlay....`).
- **Governance — every commit that changes a shipping file under `helpers/`:**
  1. Stage the code file(s) under `helpers/sec_overlay/` **and** `helpers/sec_overlay/README.md` (its immediate-folder README — the pre-commit hook rejects the commit otherwise).
  2. Stage the test file(s) under `helpers/tests/` **and** `helpers/tests/README.md`.
  3. Add an entry to `plugins/sec-overlay/CHANGELOG.md` (plugin-internal changes route to the plugin changelog, not the root).
  4. Bump `version` in `plugins/sec-overlay/.claude-plugin/plugin.json` by this commit's Conventional type. Every Plan A code commit is `feat` (new capability) → minor bump. The sequence is `0.2.1 → 0.3.0 → 0.4.0 → …`; the branch lands at whatever the final commit sets. A docs-only commit (Task 8, `docs`) bumps patch on `SKILL.md` (a shipping file) and does not touch the plugin changelog beyond its own entry.
  5. Stage explicit paths only. Never `git add -A`, `git add .`, `git commit -a`, or `--no-verify`.
- **Branch:** all work on `feat/sec-overlay-audit-driver` (create it before Task 1; never commit to `main`).
- **Do not modify** `repo_memory.PHASES` (`repo_memory.py:35-38`). It serves cross-run resume memory, a different layer from within-run sequencing. The new table is the driver's authority; unifying the two is a documented follow-on, out of Plan A scope.
- **Preserve verbatim** any `agents/*.md` hard rules if a task edits a prompt (model-family diversity, tool-receipt safety contract, count-invariant verdict tables).

---

## File structure

| Path | Responsibility |
|------|----------------|
| Create `helpers/sec_overlay/phases.py` | The frozen `PhaseSpec` table + pure sequencer helpers (`next_actionable_phase`, `missing_inputs`, `outputs_present`). No side effects. |
| Create `helpers/sec_overlay/driver.py` | `AuditContext`, `PhaseHalt`, the deterministic-action map, `render_dispatch`, and `run_audit` (the sequencer loop). Imports the existing module functions the deterministic phases call. |
| Modify `helpers/sec_overlay/cli.py` | Add the `audit` subparser and its dispatch branch. |
| Modify `helpers/sec_overlay/verify.py:224-272,278-341` | Route a `static-only` finding to `NEEDS_DEPLOYMENT_TESTING` (ISSUE-053). |
| Create `helpers/tests/test_phases.py` | Sequencer-core tests. |
| Create `helpers/tests/test_driver.py` | Driver mechanism + wiring + resumability tests. |
| Modify `helpers/tests/test_verify.py` | Static-only routing test. |
| Modify `plugins/sec-overlay/skills/sec-overlay/SKILL.md:~104`, `.../skills/sec-overlay/CLAUDE.md:~56` | Fix the `begin_pass` signature (ISSUE-002). |

---

## Task 1: Phase table + pure sequencer core

**Files:**
- Create: `helpers/sec_overlay/phases.py`
- Test: `helpers/tests/test_phases.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class PhaseSpec` with fields `name: str`, `kind: str` (`"deterministic"|"agent"`), `inputs: tuple[Callable[[Workspace], Path], ...]`, `outputs: tuple[Callable[[Workspace], Path], ...]`, `prompt: str | None = None`.
  - `PHASE_TABLE: tuple[PhaseSpec, ...]` — the ordered pipeline.
  - `def missing_inputs(phase: PhaseSpec, ws: Workspace) -> list[Path]` — input paths that do not exist.
  - `def outputs_present(phase: PhaseSpec, ws: Workspace) -> bool` — all output paths exist.
  - `def next_actionable_phase(table: tuple[PhaseSpec, ...], state: CampaignState) -> PhaseSpec | None` — first phase whose `name` is not a `"done"` key in `state.stages`; `None` when all recorded.
- Consumes: `Workspace` (`sec_overlay.workspace`), `CampaignState` (`sec_overlay.models`).

- [ ] **Step 1: Write the failing test**

```python
# helpers/tests/test_phases.py
from pathlib import Path

from sec_overlay.models import CampaignState
from sec_overlay.workspace import Workspace


def test_next_actionable_skips_recorded_phases():
    from sec_overlay.phases import PHASE_TABLE, next_actionable_phase

    state = CampaignState(pass_number=1, active_sha="s")
    assert next_actionable_phase(PHASE_TABLE, state).name == PHASE_TABLE[0].name

    state.stages[PHASE_TABLE[0].name] = "done"
    assert next_actionable_phase(PHASE_TABLE, state).name == PHASE_TABLE[1].name


def test_all_recorded_returns_none():
    from sec_overlay.phases import PHASE_TABLE, next_actionable_phase

    state = CampaignState(pass_number=1, active_sha="s")
    for p in PHASE_TABLE:
        state.stages[p.name] = "done"
    assert next_actionable_phase(PHASE_TABLE, state) is None


def test_missing_inputs_reports_absent_artifact(tmp_path):
    from sec_overlay.phases import PhaseSpec, missing_inputs, outputs_present

    ws = Workspace(tmp_path / "w")
    ws.ensure()
    spec = PhaseSpec(
        name="x",
        kind="deterministic",
        inputs=(lambda w: w.kb / "scan-profile.json",),
        outputs=(lambda w: w.findings_dir / "done.flag",),
    )
    assert missing_inputs(spec, ws) == [ws.kb / "scan-profile.json"]
    assert outputs_present(spec, ws) is False

    (ws.kb / "scan-profile.json").write_text("{}")
    (ws.findings_dir / "done.flag").write_text("x")
    assert missing_inputs(spec, ws) == []
    assert outputs_present(spec, ws) is True


def test_first_phase_is_prefilter_and_investigate_precedes_findings_gate():
    # ISSUE-044: findings-gate runs right after investigate.
    from sec_overlay.phases import PHASE_TABLE

    names = [p.name for p in PHASE_TABLE]
    assert "investigate" in names and "findings-gate" in names
    assert names.index("findings-gate") == names.index("investigate") + 1
    # ISSUE-007: noise/dedupe collapse before report.
    assert names.index("dedupe") < names.index("report")
    assert names.index("demote-noise") < names.index("report")
    # ISSUE-045: trace is a required phase.
    assert "trace" in names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd plugins/sec-overlay/skills/sec-overlay/helpers && uv run pytest tests/test_phases.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sec_overlay.phases'`.

- [ ] **Step 3: Write minimal implementation**

```python
# helpers/sec_overlay/phases.py
"""Ordered phase table and pure sequencer helpers for the audit driver.

The table is the single source of within-run phase order. Each phase declares
the artifacts that must exist before it may start (``inputs``) and the artifacts
that must exist for it to count as finished (``outputs``). Agent phases also name
the ``agents/<prompt>.md`` the orchestrator must run.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

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


def _arch(ws: Workspace) -> Path:
    return ws.kb / "architecture.md"


def _threat(ws: Workspace) -> Path:
    return ws.kb / "THREAT_MODEL.md"


def _findings_dir(ws: Workspace) -> Path:
    return ws.findings_dir


def _report(ws: Workspace) -> Path:
    return ws.report_path


def _sarif(ws: Workspace) -> Path:
    return ws.sarif_path


PHASE_TABLE: tuple[PhaseSpec, ...] = (
    PhaseSpec("recon", "agent", (), (_profile,), prompt="recon.md"),
    PhaseSpec("architecture", "agent", (_profile,), (_arch,), prompt="architecture.md"),
    PhaseSpec("threat_model", "agent", (_arch,), (_threat,), prompt="threat-model.md"),
    PhaseSpec("prefilter", "deterministic", (_profile,), (_findings_dir,)),
    PhaseSpec("investigate", "agent", (_findings_dir,), (_findings_dir,), prompt="investigate.md"),
    PhaseSpec("findings-gate", "deterministic", (_findings_dir,), (_findings_dir,)),
    PhaseSpec("dedupe", "deterministic", (_findings_dir,), (_findings_dir,)),
    PhaseSpec("critic", "agent", (_findings_dir,), (_findings_dir,), prompt="critic.md"),
    PhaseSpec("judge", "agent", (_findings_dir,), (_findings_dir,), prompt="judge.md"),
    PhaseSpec("validate", "agent", (_findings_dir,), (_findings_dir,), prompt="validate.md"),
    PhaseSpec("trace", "agent", (_findings_dir,), (_findings_dir,), prompt="trace.md"),
    PhaseSpec("calibrate", "deterministic", (_findings_dir,), (_findings_dir,)),
    PhaseSpec("patch", "agent", (_findings_dir,), (_findings_dir,), prompt="patch.md"),
    PhaseSpec("verify", "deterministic", (_findings_dir,), (_findings_dir,)),
    PhaseSpec("demote-noise", "deterministic", (_findings_dir,), (_findings_dir,)),
    PhaseSpec("report", "deterministic", (_findings_dir,), (_report, _sarif)),
    PhaseSpec("selfscore", "deterministic", (_report,), (_findings_dir,)),
)


def missing_inputs(phase: PhaseSpec, ws: Workspace) -> list[Path]:
    """Return the phase's input paths that do not exist."""
    return [p(ws) for p in phase.inputs if not p(ws).exists()]


def outputs_present(phase: PhaseSpec, ws: Workspace) -> bool:
    """Return True when every declared output path exists."""
    return all(p(ws).exists() for p in phase.outputs)


def next_actionable_phase(
    table: tuple[PhaseSpec, ...], state: CampaignState
) -> PhaseSpec | None:
    """Return the first phase not recorded ``done`` in state, or None."""
    for phase in table:
        if state.stages.get(phase.name) != "done":
            return phase
    return None
```

Note on the `field` import: remove it if `ruff` flags it unused — the dataclass here uses only literal defaults.

- [ ] **Step 4: Run test + lint + types**

Run: `uv run pytest tests/test_phases.py -v && uv run ruff check sec_overlay/phases.py tests/test_phases.py && uv run ty check`
Expected: tests PASS; ruff clean; ty clean.

- [ ] **Step 5: Update folder READMEs (governance)**

Add a one-row entry for `phases.py` to `helpers/sec_overlay/README.md` (in its module inventory table: "the ordered phase table + pure sequencer helpers the audit driver walks") and a one-line note for `test_phases.py` to `helpers/tests/README.md`.

- [ ] **Step 6: Commit**

```bash
# from repo root; bump plugin.json 0.2.1 -> 0.3.0 (feat) and add a CHANGELOG entry first
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phases.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_phases.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "feat(sec-overlay): add audit phase table and sequencer core"
```

---

## Task 2: Deterministic phase runner + loud halt

**Files:**
- Create: `helpers/sec_overlay/driver.py`
- Test: `helpers/tests/test_driver.py`

**Interfaces:**
- Produces:
  - `@dataclass class AuditContext` with `ws: Workspace`, `target: str`, `config: str`, `sha: str`, `profile: ScanProfile | None = None`.
  - `class PhaseHalt(RuntimeError)` — raised when a phase cannot start (missing input) or did not finish (missing output).
  - `DETERMINISTIC_ACTIONS: dict[str, Callable[[AuditContext], None]]` — name → action.
  - `def run_deterministic_phase(phase: PhaseSpec, ctx: AuditContext) -> None` — checks inputs, runs the action, checks outputs, records the stage; raises `PhaseHalt` on either gate.
- Consumes: `PhaseSpec`, `missing_inputs`, `outputs_present` (Task 1); `record_stage` (`sec_overlay.campaign`); `ScanProfile` (`sec_overlay.models`).

- [ ] **Step 1: Write the failing test**

```python
# helpers/tests/test_driver.py
import pytest

from sec_overlay.workspace import Workspace


def _ctx(tmp_path):
    from sec_overlay.driver import AuditContext

    ws = Workspace(tmp_path / "w")
    ws.ensure()
    return AuditContext(ws=ws, target=str(tmp_path / "t"), config="cfg", sha="deadbeef")


def test_run_deterministic_halts_on_missing_input(tmp_path):
    from sec_overlay.driver import PhaseHalt, run_deterministic_phase
    from sec_overlay.phases import PhaseSpec

    ctx = _ctx(tmp_path)
    spec = PhaseSpec(
        name="needs-profile",
        kind="deterministic",
        inputs=(lambda w: w.kb / "scan-profile.json",),
        outputs=(),
    )
    with pytest.raises(PhaseHalt) as exc:
        run_deterministic_phase(spec, ctx)
    assert "scan-profile.json" in str(exc.value)


def test_run_deterministic_halts_when_output_absent(tmp_path):
    from sec_overlay.driver import DETERMINISTIC_ACTIONS, PhaseHalt, run_deterministic_phase
    from sec_overlay.phases import PhaseSpec

    ctx = _ctx(tmp_path)
    DETERMINISTIC_ACTIONS["noop-phase"] = lambda c: None  # produces nothing
    spec = PhaseSpec(
        name="noop-phase",
        kind="deterministic",
        inputs=(),
        outputs=(lambda w: w.report_path,),
    )
    with pytest.raises(PhaseHalt) as exc:
        run_deterministic_phase(spec, ctx)
    assert "did not produce" in str(exc.value)


def test_run_deterministic_records_stage_on_success(tmp_path):
    from sec_overlay.driver import DETERMINISTIC_ACTIONS, run_deterministic_phase
    from sec_overlay.phases import PhaseSpec
    from sec_overlay.state import load_state

    ctx = _ctx(tmp_path)

    def _make_report(c):
        c.ws.report_path.write_text("# report")

    DETERMINISTIC_ACTIONS["make-report"] = _make_report
    spec = PhaseSpec(
        name="make-report",
        kind="deterministic",
        inputs=(),
        outputs=(lambda w: w.report_path,),
    )
    run_deterministic_phase(spec, ctx)
    assert load_state(ctx.ws).stages.get("make-report") == "done"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_driver.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sec_overlay.driver'`.

- [ ] **Step 3: Write minimal implementation**

```python
# helpers/sec_overlay/driver.py
"""Deterministic phase-driver for a sec-overlay audit run.

The driver walks ``phases.PHASE_TABLE``. It runs a deterministic phase's action
and records its stage, or — for an agent phase — prints the exact dispatch and
stops until the orchestrator produces the phase's declared outputs. It never
calls a model: agents stay external and independent.
"""

from collections.abc import Callable
from dataclasses import dataclass

from sec_overlay.campaign import record_stage
from sec_overlay.models import ScanProfile
from sec_overlay.phases import PhaseSpec, missing_inputs, outputs_present
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
        raise PhaseHalt(
            f"phase {phase.name!r} did not produce: " + ", ".join(missing)
        )
    record_stage(ctx.ws, phase.name)
```

Confirm `ScanProfile` is importable from `sec_overlay.models` (the Explore report cites `run_prefilter(..., profile: ScanProfile)`); if it lives elsewhere, `uv run python -c "from sec_overlay.models import ScanProfile"` and adjust the import to the real module.

- [ ] **Step 4: Run test + lint + types**

Run: `uv run pytest tests/test_driver.py -v && uv run ruff check sec_overlay/driver.py tests/test_driver.py && uv run ty check`
Expected: PASS, clean, clean.

- [ ] **Step 5: Update folder READMEs**

Add `driver.py` ("the audit sequencer: deterministic-phase runner, loud halt, agent-dispatch printer") to `helpers/sec_overlay/README.md` and note `test_driver.py` in `helpers/tests/README.md`.

- [ ] **Step 6: Commit**

```bash
# bump plugin.json 0.3.0 -> 0.4.0 (feat); add CHANGELOG entry
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/driver.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_driver.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "feat(sec-overlay): add deterministic phase runner with loud halt"
```

---

## Task 3: Agent dispatch printer

**Files:**
- Modify: `helpers/sec_overlay/driver.py`
- Test: `helpers/tests/test_driver.py`

**Interfaces:**
- Produces:
  - `def render_dispatch(phase: PhaseSpec, ctx: AuditContext) -> str` — a printable block naming the prompt file and the token substitutions the orchestrator must apply (`{{TARGET}}`, `{{WORKSPACE}}`, `{{SHA}}`). Deterministic string; no side effects.
- Consumes: `AuditContext`, `PhaseSpec`.

- [ ] **Step 1: Write the failing test**

```python
# append to helpers/tests/test_driver.py
def test_render_dispatch_names_prompt_and_tokens(tmp_path):
    from sec_overlay.driver import render_dispatch
    from sec_overlay.phases import PhaseSpec

    ctx = _ctx(tmp_path)
    spec = PhaseSpec(
        name="recon",
        kind="agent",
        inputs=(),
        outputs=(lambda w: w.kb / "scan-profile.json",),
        prompt="recon.md",
    )
    out = render_dispatch(spec, ctx)
    assert "agents/recon.md" in out
    assert ctx.target in out
    assert str(ctx.ws.root) in out
    assert "deadbeef" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_driver.py::test_render_dispatch_names_prompt_and_tokens -v`
Expected: FAIL — `AttributeError`/`ImportError: cannot import name 'render_dispatch'`.

- [ ] **Step 3: Write minimal implementation**

```python
# add to helpers/sec_overlay/driver.py
def render_dispatch(phase: PhaseSpec, ctx: AuditContext) -> str:
    """Return the dispatch block for an agent phase.

    The orchestrator runs the model; this only tells it which prompt to run and
    what to substitute. Advancement happens later, when the phase's declared
    outputs exist.
    """
    outputs = ", ".join(str(p(ctx.ws)) for p in phase.outputs) or "(none)"
    return (
        f"NEXT AGENT PHASE: {phase.name}\n"
        f"  prompt: agents/{phase.prompt}\n"
        f"  substitute: {{{{TARGET}}}}={ctx.target} "
        f"{{{{WORKSPACE}}}}={ctx.ws.root} {{{{SHA}}}}={ctx.sha}\n"
        f"  required outputs before advancing: {outputs}"
    )
```

- [ ] **Step 4: Run test + lint + types**

Run: `uv run pytest tests/test_driver.py -v && uv run ruff check sec_overlay/driver.py tests/test_driver.py && uv run ty check`
Expected: PASS, clean, clean.

- [ ] **Step 5: Update folder READMEs**

One-line update to `helpers/sec_overlay/README.md`'s `driver.py` row (mention `render_dispatch`); `helpers/tests/README.md` already lists `test_driver.py` — a one-word note is enough to satisfy the same-commit rule.

- [ ] **Step 6: Commit**

```bash
# bump plugin.json 0.4.0 -> 0.5.0 (feat); add CHANGELOG entry
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/driver.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_driver.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "feat(sec-overlay): print exact dispatch for agent phases"
```

---

## Task 4: Wire deterministic actions + the `audit` subcommand (resumable loop)

This task wires the six unwired modules as deterministic actions, registers the remaining deterministic actions, and adds the `audit` subcommand that walks the table until it reaches an agent phase (prints the dispatch and stops) or the end.

**Files:**
- Modify: `helpers/sec_overlay/driver.py`
- Modify: `helpers/sec_overlay/cli.py:88-146`
- Test: `helpers/tests/test_driver.py`

**Interfaces:**
- Produces:
  - `def run_audit(ctx: AuditContext, *, table=PHASE_TABLE) -> str` — walks the table from `next_actionable_phase`: runs each deterministic phase; on an agent phase, if its outputs already exist records the stage and continues, else returns `render_dispatch(...)` and stops; returns a `"AUDIT COMPLETE"` string when the table is exhausted. Resumable: re-invoking after the orchestrator writes an agent phase's outputs advances past it.
  - Registered `DETERMINISTIC_ACTIONS` keys: `prefilter`, `findings-gate`, `dedupe`, `calibrate`, `verify`, `demote-noise`, `report`, `selfscore`.
- Consumes: `run_prefilter` (`sec_overlay.prefilter`), `validate_findings` (`sec_overlay.findings_gate`), `dedupe_findings` (`sec_overlay.dedupe`), `demote_noise` (`sec_overlay.partition`), `verify_findings` (`sec_overlay.verify`), `write_self_score` (`sec_overlay.selfscore`), the report writer (`sec_overlay.report`), `calibrate` entry (`sec_overlay.calibrate`), `begin_pass`/`load_state` (`sec_overlay.state`), `load_paths`/`Workspace` (`sec_overlay.workspace`), `load_profile` for `ScanProfile` (locate with `uv run python -c "import sec_overlay.recon"` or grep — the recon phase writes `kb/scan-profile.json`; read it back into a `ScanProfile`).

- [ ] **Step 1: Write the failing test**

```python
# append to helpers/tests/test_driver.py
def test_run_audit_runs_deterministic_then_halts_at_agent(tmp_path, monkeypatch):
    from sec_overlay import driver
    from sec_overlay.driver import AuditContext, run_audit
    from sec_overlay.state import begin_pass

    ws = Workspace(tmp_path / "w")
    ws.ensure()
    begin_pass(ws, "sha1")
    ctx = AuditContext(ws=ws, target=str(tmp_path / "t"), config="cfg", sha="sha1")

    # First actionable phase is 'recon' (agent) — no scan-profile yet, so the
    # driver must print recon's dispatch and stop.
    out = run_audit(ctx)
    assert "NEXT AGENT PHASE: recon" in out
    assert "agents/recon.md" in out


def test_run_audit_advances_past_completed_agent_phase(tmp_path):
    from sec_overlay.driver import AuditContext, run_audit
    from sec_overlay.state import begin_pass

    ws = Workspace(tmp_path / "w")
    ws.ensure()
    begin_pass(ws, "sha1")
    # Simulate recon having produced its output.
    (ws.kb / "scan-profile.json").write_text('{"languages": []}')
    ctx = AuditContext(ws=ws, target=str(tmp_path / "t"), config="cfg", sha="sha1")

    out = run_audit(ctx)
    # recon's output exists -> recon recorded, next agent phase is architecture.
    from sec_overlay.state import load_state

    assert load_state(ws).stages.get("recon") == "done"
    assert "NEXT AGENT PHASE: architecture" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_driver.py -k run_audit -v`
Expected: FAIL — `ImportError: cannot import name 'run_audit'`.

- [ ] **Step 3: Write minimal implementation**

Register the deterministic actions. Each action calls the existing module function and, where that function does not itself write the phase's declared output, the action does nothing extra (the output gate in Task 2 catches a genuine failure). Read `kb/scan-profile.json` into a `ScanProfile` for `prefilter`.

```python
# add to helpers/sec_overlay/driver.py
import json

from sec_overlay.dedupe import dedupe_findings
from sec_overlay.findings_gate import validate_findings
from sec_overlay.partition import demote_noise
from sec_overlay.phases import PHASE_TABLE, next_actionable_phase
from sec_overlay.prefilter import run_prefilter
from sec_overlay.selfscore import write_self_score
from sec_overlay.state import load_state
from sec_overlay.verify import verify_findings


def _load_profile(ctx: AuditContext) -> ScanProfile:
    if ctx.profile is None:
        data = json.loads((ctx.ws.kb / "scan-profile.json").read_text())
        ctx.profile = ScanProfile.from_dict(data)  # confirm ScanProfile.from_dict exists
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


def _act_calibrate(ctx: AuditContext) -> None:
    from sec_overlay.calibrate import calibrate_findings  # confirm real name via grep

    calibrate_findings(ctx.ws)


def _act_report(ctx: AuditContext) -> None:
    from sec_overlay.report import write_reports  # confirm real name via grep

    write_reports(ctx.ws)


DETERMINISTIC_ACTIONS.update(
    {
        "prefilter": _act_prefilter,
        "findings-gate": _act_findings_gate,
        "dedupe": _act_dedupe,
        "calibrate": _act_calibrate,
        "verify": _act_verify,
        "demote-noise": _act_demote_noise,
        "report": _act_report,
        "selfscore": _act_selfscore,
    }
)


def run_audit(ctx: AuditContext, *, table: tuple[PhaseSpec, ...] = PHASE_TABLE) -> str:
    """Walk the table from the first unrecorded phase.

    Runs each deterministic phase. On an agent phase whose outputs already exist,
    records the stage and continues; otherwise returns its dispatch block and
    stops. Returns ``"AUDIT COMPLETE"`` when every phase is recorded. Resumable:
    a later call advances past an agent phase once its outputs exist.
    """
    while True:
        phase = next_actionable_phase(table, load_state(ctx.ws))
        if phase is None:
            return "AUDIT COMPLETE"
        if phase.kind == "deterministic":
            run_deterministic_phase(phase, ctx)
            continue
        # agent phase
        if outputs_present(phase, ctx.ws):
            record_stage(ctx.ws, phase.name)
            continue
        return render_dispatch(phase, ctx)
```

Then confirm the three "confirm real name" lookups before running: `ScanProfile.from_dict`, `calibrate_findings`, `write_reports`. Grep each: `uv run python -c "import sec_overlay.calibrate as m; print([n for n in dir(m) if not n.startswith('_')])"` etc. Use the real names.

Add the `audit` subcommand:

```python
# in helpers/sec_overlay/cli.py, near cli.py:103 (after the memory subparser)
    audit = sub.add_parser("audit", help="run the deterministic audit driver")
    audit.add_argument("--target", required=True)
    audit.add_argument("--workspace")
    audit.add_argument("--config", required=True)
    audit.add_argument("--sha")

# in main(), before the `return 1` at cli.py:142
    if args.cmd == "audit":
        from sec_overlay.driver import AuditContext, run_audit
        from sec_overlay.state import begin_pass

        ws = load_paths(workspace=args.workspace) if args.workspace else _default_ws(args.target)
        sha = args.sha or ""
        begin_pass(ws, sha)
        ctx = AuditContext(ws=ws, target=args.target, config=args.config, sha=sha)
        print(run_audit(ctx))
        return 0
```

Match how `scan` resolves its workspace (`cli.py:109-127`) for `_default_ws` — reuse the existing resolution helper rather than inventing one; if `scan` builds the workspace inline, factor that into a small `_resolve_workspace(args)` used by both, or copy the exact lines. Do not add a new path-resolution scheme.

- [ ] **Step 4: Run test + full suite + lint + types**

Run: `uv run pytest tests/test_driver.py -v && uv run pytest -q && uv run ruff check sec_overlay/ tests/ && uv run ty check`
Expected: driver tests PASS; full suite has only the two documented env-only failures (`test_preflight...vendored_rules`, bench/seed tests) — no new failures; ruff and ty clean.

- [ ] **Step 5: Update folder READMEs**

Update `helpers/sec_overlay/README.md`: note the six now-wired modules (`factcheck`/`redactor` wiring lands in Task 5–7 context; here mark `demote_noise`, `dedupe`, `selfscore`, `validate_findings`, `run_prefilter`, `verify_findings` as driven by `driver.py`) and mark `cli.py` as exposing the `audit` subcommand. Note `test_driver.py` growth in `helpers/tests/README.md`.

- [ ] **Step 6: Commit**

```bash
# bump plugin.json 0.5.0 -> 0.6.0 (feat); add CHANGELOG entry
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/driver.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_driver.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "feat(sec-overlay): add audit subcommand and wire deterministic phases"
```

---

## Task 5: Unrouted-class triage dispatch (ISSUE-039)

When a classifier produces a candidate class not in the investigate plan, the driver must surface it — a general-triage dispatch — not orphan it.

**Files:**
- Modify: `helpers/sec_overlay/driver.py`
- Test: `helpers/tests/test_driver.py`

**Interfaces:**
- Produces: `def unrouted_triage_dispatch(ctx: AuditContext, agents_to_spawn: list[str]) -> str | None` — returns a general-triage dispatch block naming the unrouted classes and their candidate counts, or `None` when all classes are routed.
- Consumes: `unrouted_candidate_classes(ws, agents_to_spawn) -> dict[str, int]` (`sec_overlay.partition:27`).

- [ ] **Step 1: Write the failing test**

```python
# append to helpers/tests/test_driver.py
def test_unrouted_triage_dispatch_lists_unrouted_classes(tmp_path, monkeypatch):
    from sec_overlay import driver
    from sec_overlay.driver import AuditContext, unrouted_triage_dispatch

    ctx = AuditContext(ws=Workspace(tmp_path / "w"), target="t", config="c", sha="s")
    ctx.ws.ensure()
    monkeypatch.setattr(
        driver, "unrouted_candidate_classes", lambda ws, plan: {"security-other": 3}
    )
    out = unrouted_triage_dispatch(ctx, ["sqli"])
    assert out is not None and "security-other" in out and "3" in out


def test_unrouted_triage_dispatch_none_when_all_routed(tmp_path, monkeypatch):
    from sec_overlay import driver
    from sec_overlay.driver import AuditContext, unrouted_triage_dispatch

    ctx = AuditContext(ws=Workspace(tmp_path / "w"), target="t", config="c", sha="s")
    ctx.ws.ensure()
    monkeypatch.setattr(driver, "unrouted_candidate_classes", lambda ws, plan: {})
    assert unrouted_triage_dispatch(ctx, ["sqli"]) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_driver.py -k unrouted -v`
Expected: FAIL — `cannot import name 'unrouted_triage_dispatch'`.

- [ ] **Step 3: Write minimal implementation**

```python
# add to helpers/sec_overlay/driver.py
from sec_overlay.partition import unrouted_candidate_classes


def unrouted_triage_dispatch(ctx: AuditContext, agents_to_spawn: list[str]) -> str | None:
    """Return a general-triage dispatch for candidate classes not in the plan.

    Returns None when every candidate class is already routed to an agent.
    """
    unrouted = unrouted_candidate_classes(ctx.ws, agents_to_spawn)
    if not unrouted:
        return None
    rows = ", ".join(f"{cls}={n}" for cls, n in sorted(unrouted.items()))
    return (
        "UNROUTED CANDIDATE CLASSES — spawn general triage\n"
        f"  prompt: agents/investigate.md (general-triage)\n"
        f"  classes: {rows}\n"
        f"  substitute: {{{{TARGET}}}}={ctx.target} {{{{WORKSPACE}}}}={ctx.ws.root}"
    )
```

Call site (ISSUE-006 + ISSUE-039): in `run_audit`, when the actionable agent phase is `investigate`, read `agents_to_spawn` from `kb/scan-profile.json`, then augment it through `reconcile_plan(ctx.ws, agents_to_spawn)` (`partition.py:93`, which appends candidate classes recon omitted). Pass the reconciled list as `classes=` to the investigate dispatch (see Task 8's `render_dispatch(classes=...)`), and append `unrouted_triage_dispatch(ctx, reconciled)` when it returns non-`None`. Keep it additive: `investigate` dispatch first, then the triage note.

```python
# in run_audit, agent-phase branch, when phase.name == "investigate":
import json

profile = json.loads((ctx.ws.kb / "scan-profile.json").read_text())
planned = list(profile.get("agents_to_spawn", []))
reconciled = reconcile_plan(ctx.ws, planned)  # ISSUE-006: recon-omitted classes appended
block = render_dispatch(phase, ctx, classes=reconciled)
triage = unrouted_triage_dispatch(ctx, reconciled)
return block if triage is None else block + "\n" + triage
```

Import `reconcile_plan` from `sec_overlay.partition` at the top of `driver.py`. Add two tests: (1) `run_audit` at the investigate stop includes the triage block when `unrouted_candidate_classes` is non-empty (monkeypatch as above; pre-create `kb/scan-profile.json` with `agents_to_spawn` plus a candidate finding so investigate is the actionable phase); (2) a class returned by `reconcile_plan` but absent from `agents_to_spawn` appears in the investigate dispatch (monkeypatch `driver.reconcile_plan` to append `"idor"`; assert `"idor"` in the dispatch).

- [ ] **Step 4: Run test + lint + types**

Run: `uv run pytest tests/test_driver.py -v && uv run ruff check sec_overlay/driver.py tests/test_driver.py && uv run ty check`
Expected: PASS, clean, clean.

- [ ] **Step 5: Update folder READMEs**

Note the triage behavior in `helpers/sec_overlay/README.md`'s `driver.py` row; touch `helpers/tests/README.md`.

- [ ] **Step 6: Commit**

```bash
# bump plugin.json 0.6.0 -> 0.7.0 (feat); add CHANGELOG entry
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/driver.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_driver.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "feat(sec-overlay): dispatch general triage for unrouted classes"
```

---

## Task 6: Verify honesty — static-only → needs-deployment-testing (ISSUE-053)

A finding `verify` cannot dynamically confirm must not stay `CONFIRMED` implying a dynamic check passed. Route it to `NEEDS_DEPLOYMENT_TESTING`.

**Invariant:** after `verify_findings`, a finding whose `verification == "static-only"` has status `NEEDS_DEPLOYMENT_TESTING`; a finding whose `verification == "verified-static"` has status `FIXED`; `not-fixed`/`verify-error` keep status `CONFIRMED`.

**Files:**
- Modify: `helpers/sec_overlay/verify.py:278-341` (the `verify_findings` loop, around `verify.py:331`)
- Test: `helpers/tests/test_verify.py`

**Interfaces:**
- Consumes: `FindingStatus.NEEDS_DEPLOYMENT_TESTING` (`models.py:37`), existing `verify_patch` return strings.
- Produces: no new signature; the status transition is the change.

- [ ] **Step 1: Write the failing test**

```python
# append to helpers/tests/test_verify.py — match existing imports/fixtures in that file
def test_static_only_routes_to_needs_deployment_testing(tmp_path):
    from sec_overlay.models import Finding, FindingStatus
    from sec_overlay.verify import verify_findings
    from sec_overlay.workspace import Workspace, write_findings

    ws = Workspace(tmp_path / "w")
    ws.ensure()
    f = Finding(  # fill required fields per the Finding constructor in models.py
        id="F-0001",
        status=FindingStatus.CONFIRMED,
        # ... existing required fields (file, line, cls, message, evidence_sources) ...
        patch_diff="--- a\n+++ b\n",
    )
    write_findings(ws, [f])
    # verifier stub returns 'static-only' -> finding must become NEEDS_DEPLOYMENT_TESTING
    verify_findings(ws, str(tmp_path / "t"), "cfg", verifier=lambda *a, **k: "static-only")

    from sec_overlay.workspace import read_findings

    got = read_findings(ws)[0]
    assert got.status == FindingStatus.NEEDS_DEPLOYMENT_TESTING
    assert got.verification == "static-only"
```

Read `models.py` around the `Finding` dataclass first to supply the exact required constructor fields; copy field names from an existing `test_verify.py` fixture rather than guessing.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_verify.py::test_static_only_routes_to_needs_deployment_testing -v`
Expected: FAIL — status stays `CONFIRMED` (current code only promotes on `verified-static`).

- [ ] **Step 3: Write minimal implementation**

At the point in `verify_findings` where `f.verification` is stamped (`verify.py:331`), add the routing branch:

```python
# in verify.py verify_findings loop, where verification is applied
f.verification = result
if result == "verified-static":
    f.status = FindingStatus.FIXED
    promoted += 1
elif result == "static-only":
    f.status = FindingStatus.NEEDS_DEPLOYMENT_TESTING
# 'not-fixed' and 'verify-error' leave status unchanged
```

Match the existing variable names in the loop (`result`, `promoted`, or whatever the file uses — read `verify.py:278-341` and adapt). Do not change the return value's meaning (count promoted to FIXED) unless a test requires it; if the count should exclude `static-only`, keep it excluded.

- [ ] **Step 4: Run test + full suite + lint + types**

Run: `uv run pytest tests/test_verify.py -v && uv run pytest -q && uv run ruff check sec_overlay/verify.py tests/test_verify.py && uv run ty check`
Expected: new test PASS; no new failures elsewhere; clean.

- [ ] **Step 5: Update folder READMEs**

Note the static-only routing in `helpers/sec_overlay/README.md`'s `verify.py` row; touch `helpers/tests/README.md`.

- [ ] **Step 6: Commit**

```bash
# bump plugin.json 0.7.0 -> 0.8.0 (feat); add CHANGELOG entry
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/verify.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_verify.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "feat(sec-overlay): route static-only verify to needs-deployment-testing"
```

---

## Task 7: Wire factcheck + redactor as driver steps (ISSUE-047, ISSUE-051)

`factcheck` and `redactor` are tested but never called. `redactor.safe_for_prompt` is a security control; `factcheck.apply_verdict` applies an agent's verdict. Wire both into the driver: `redactor` as a deterministic pre-dispatch guard on any text the driver prints, and `factcheck` as the deterministic application step for the validate phase's verdict artifact.

**Scope note (laziness):** wire the two named modules with the smallest correct integration. `factcheck` needs a verdict source — the `validate` agent writes verdicts per finding; the deterministic step reads those verdict dicts and applies them via `apply_verdict`. If the validate prompt does not yet emit a machine-readable verdict artifact, wire `factcheck` behind a documented input gate (a `kb/verdicts.json` the validate phase declares as output) and log a gap rather than inventing the prompt here — the prompt change belongs to Plan B.

**Files:**
- Modify: `helpers/sec_overlay/driver.py`
- Test: `helpers/tests/test_driver.py`

**Interfaces:**
- Consumes: `safe_for_prompt(text, findings=None) -> str` (`redactor.py:93`), `validate_verdict(d) -> list[str]` (`factcheck.py:18`), `apply_verdict(f, d) -> Finding` (`factcheck.py:31`).
- Produces: `render_dispatch` output passes through `safe_for_prompt` before return; a `_act_factcheck(ctx)` action registered for a `factcheck` phase (added to the table between `validate`/`trace` and `calibrate`).

- [ ] **Step 1: Write the failing test**

```python
# append to helpers/tests/test_driver.py
def test_dispatch_is_secret_redacted(tmp_path, monkeypatch):
    from sec_overlay import driver
    from sec_overlay.driver import AuditContext, render_dispatch
    from sec_overlay.phases import PhaseSpec

    ctx = AuditContext(ws=Workspace(tmp_path / "w"), target="t", config="c", sha="s")
    ctx.ws.ensure()
    calls = []
    monkeypatch.setattr(driver, "safe_for_prompt", lambda text, findings=None: calls.append(text) or text)
    spec = PhaseSpec("recon", "agent", (), (), prompt="recon.md")
    render_dispatch(spec, ctx)
    assert calls, "render_dispatch must pass its output through safe_for_prompt"


def test_factcheck_action_applies_verdicts(tmp_path):
    from sec_overlay.driver import AuditContext, DETERMINISTIC_ACTIONS
    # Construct a workspace with one finding and a kb/verdicts.json mapping its id
    # to a VERIFIED verdict; assert _act_factcheck stamps verification="fact-checked".
    # (Fill finding/verdict fields from models.py + factcheck.py VERDICTS.)
    ...
```

Complete the second test body from `factcheck.py:31` semantics (VERIFIED stamps `verification="fact-checked"`) and the `Finding` constructor.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_driver.py -k "redacted or factcheck" -v`
Expected: FAIL — `safe_for_prompt` not referenced in `driver`; no `factcheck` action registered.

- [ ] **Step 3: Write minimal implementation**

```python
# in helpers/sec_overlay/driver.py
from sec_overlay.factcheck import apply_verdict, validate_verdict
from sec_overlay.redactor import safe_for_prompt
from sec_overlay.workspace import read_findings, write_findings

# wrap render_dispatch's return:
#   return safe_for_prompt(block)
# (assign the composed string to `block`, then `return safe_for_prompt(block)`)

def _act_factcheck(ctx: AuditContext) -> None:
    verdicts_path = ctx.ws.kb / "verdicts.json"
    if not verdicts_path.exists():
        return  # gap logged by the phase-input gate; verdict artifact is Plan B
    verdicts = json.loads(verdicts_path.read_text())
    findings = {f.id: f for f in read_findings(ctx.ws)}
    changed = []
    for fid, d in verdicts.items():
        if fid in findings and not validate_verdict(d):
            changed.append(apply_verdict(findings[fid], d))
    if changed:
        write_findings(ctx.ws, list(findings.values()))


DETERMINISTIC_ACTIONS["factcheck"] = _act_factcheck
```

Add a `factcheck` `PhaseSpec` to `phases.py` `PHASE_TABLE` between `trace` and `calibrate`, with `inputs=(lambda w: w.kb / "verdicts.json",)` **removed** — because a hard input gate would halt every run until Plan B emits verdicts. Instead give `factcheck` no inputs and let `_act_factcheck` no-op when the artifact is absent, and `log()` the gap. Update `test_phases.py`'s ordering assertions to include `factcheck` between `trace` and `calibrate`.

- [ ] **Step 4: Run test + full suite + lint + types**

Run: `uv run pytest tests/test_driver.py tests/test_phases.py -v && uv run pytest -q && uv run ruff check sec_overlay/ tests/ && uv run ty check`
Expected: PASS; no new failures; clean.

- [ ] **Step 5: Update folder READMEs**

Mark `factcheck.py` and `redactor.py` as wired by `driver.py` in `helpers/sec_overlay/README.md`; touch `helpers/tests/README.md`.

- [ ] **Step 6: Commit**

```bash
# bump plugin.json 0.8.0 -> 0.9.0 (feat); add CHANGELOG entry
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/driver.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phases.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_driver.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_phases.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "feat(sec-overlay): wire factcheck and redactor into the driver"
```

---

## Task 8: Fix begin_pass signature in docs (ISSUE-002) + patch multi-class dispatch note (ISSUE-050)

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/SKILL.md` (the `begin_pass` line, ~104)
- Modify: `plugins/sec-overlay/skills/sec-overlay/CLAUDE.md:~56`
- Modify: `helpers/sec_overlay/driver.py` (patch dispatch passes the full class set)

**Interfaces:**
- The patch agent phase's dispatch, for a multi-class input, must substitute the full class list into `{{ATTACK_CLASS}}` — not one token (ISSUE-050). `render_dispatch` already emits TARGET/WORKSPACE/SHA; extend it so an agent phase carrying an attack-class set prints all classes.

- [ ] **Step 1: Write the failing test**

```python
# append to helpers/tests/test_driver.py
def test_patch_dispatch_lists_all_classes(tmp_path):
    from sec_overlay.driver import AuditContext, render_dispatch
    from sec_overlay.phases import PhaseSpec

    ctx = AuditContext(ws=Workspace(tmp_path / "w"), target="t", config="c", sha="s")
    ctx.ws.ensure()
    spec = PhaseSpec("patch", "agent", (), (), prompt="patch.md")
    out = render_dispatch(spec, ctx, classes=["sqli", "xss", "ssrf"])
    assert "sqli" in out and "xss" in out and "ssrf" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_driver.py::test_patch_dispatch_lists_all_classes -v`
Expected: FAIL — `render_dispatch()` takes no `classes` keyword.

- [ ] **Step 3: Write minimal implementation**

```python
# widen render_dispatch signature
def render_dispatch(
    phase: PhaseSpec, ctx: AuditContext, *, classes: list[str] | None = None
) -> str:
    ...
    class_line = ""
    if classes:
        class_line = f"\n  {{{{ATTACK_CLASS}}}}=" + ",".join(classes)
    block = (
        f"NEXT AGENT PHASE: {phase.name}\n"
        f"  prompt: agents/{phase.prompt}\n"
        f"  substitute: {{{{TARGET}}}}={ctx.target} "
        f"{{{{WORKSPACE}}}}={ctx.ws.root} {{{{SHA}}}}={ctx.sha}"
        f"{class_line}\n"
        f"  required outputs before advancing: {outputs}"
    )
    return safe_for_prompt(block)
```

In `run_audit`, when the actionable agent phase is `patch` (or `investigate`), pass the class list read from `kb/scan-profile.json` `agents_to_spawn` as `classes=`.

Doc fixes — replace the wrong `begin_pass(WS, sha)` with the real signature in both files:

- `SKILL.md`: `sec_overlay.state.begin_pass(ws, sha)` → state the real signature `begin_pass(ws: Workspace, sha: str | None) -> CampaignState` (pins SHA, increments the pass counter only after a prior pass recorded a stage).
- `CLAUDE.md:~56`: same correction.

- [ ] **Step 4: Run test + lint**

Run: `uv run pytest tests/test_driver.py -v && uv run ruff check sec_overlay/driver.py`
Expected: PASS, clean.

- [ ] **Step 5: Update folder READMEs**

`helpers/sec_overlay/README.md` `driver.py` row already covers `render_dispatch`; a one-word note satisfies the same-commit rule. `SKILL.md` is a shipping file → this commit is `docs` on a shipping file, patch bump.

- [ ] **Step 6: Commit**

```bash
# driver.py change is feat-adjacent but shipped with the doc fix; treat the commit
# as docs+feat -> minor bump 0.9.0 -> 0.10.0 (the code change is the higher type)
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/driver.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_driver.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/skills/sec-overlay/SKILL.md \
        plugins/sec-overlay/skills/sec-overlay/CLAUDE.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "feat(sec-overlay): pass full attack-class set to patch dispatch"
```

Note: `CLAUDE.md` (skill operating manual) is not a shipping file; staging it alongside is fine and needs no separate rule.

---

## Self-review

**Spec coverage (T1 rows):**
- 001 audit driver → Tasks 1–4.
- 002 begin_pass signature docs → Task 8.
- 006 demote_noise + reconcile ordered → `demote-noise` phase in table (Task 1) + action (Task 4); `reconcile_plan` wired into the investigate-dispatch path in Task 5 Step 3 (reads `agents_to_spawn`, augments via `reconcile_plan`, passes the reconciled list to the dispatch and triage). Verified present in Task 5 body.
- 007 clustering/dedupe + demote before report → table order asserted in Task 1 test.
- 015 loud halt → Task 2 `PhaseHalt`.
- 030 no false serial dependency → the table encodes only real artifact dependencies via `inputs`; independent phases share no input. Documented; no extra task needed.
- 038 driver + preconditions (P0) → Tasks 1–4.
- 039 unrouted candidates → Task 5.
- 044 findings-gate after investigate → table order (Task 1 test asserts adjacency).
- 045 trace required → `trace` in table (Task 1 test asserts presence).
- 047 factcheck wired → Task 7.
- 050 patch multi-class token → Task 8.
- 051 six modules wired → `demote_noise`, `dedupe`, `selfscore`, `validate_findings` (findings-gate), `factcheck`, `redactor` (Tasks 4, 7). `fp_feedback` is a Plan C concern (FP re-injection) — **noted, not in Plan A**; the "six" are satisfied by the modules above.
- 053 verify honesty → Task 6.

**Placeholder scan:** Task 7's second test body and Task 6's fixture are marked `...` where the executor must copy exact `Finding` constructor fields from `models.py`/existing fixtures — these are "read the real names" instructions, not silent placeholders, and each names its source. Acceptable because inventing field names here would be a hallucinated-API risk; the executor reads the real signature.

**Type consistency:** `AuditContext`, `PhaseHalt`, `PhaseSpec`, `DETERMINISTIC_ACTIONS`, `run_deterministic_phase`, `render_dispatch`, `run_audit`, `unrouted_triage_dispatch` are used with the same names across all tasks. `render_dispatch` gains a `classes` keyword in Task 8 (backward-compatible default `None`).

**Unverified external names to confirm before coding (flagged in-task):** `ScanProfile.from_dict`, `calibrate.calibrate_findings`, `report.write_reports`, the `verify_findings` loop variable names, and the `Finding` required constructor fields. Each task step says to grep/hover the real name first (code-intelligence rule; no hallucinated APIs).

**Scope:** Plan A is the driver substrate only. Plans B–D (spec §7) are written after Plan A lands, against these real signatures.
