# sec-overlay Phase and Artifact Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every sec-overlay phase read only artifacts an earlier phase produced, so no stage records `done` after doing nothing and no report names a file the run never wrote.

**Architecture:** `PHASE_TABLE` in `helpers/sec_overlay/phases.py` is the single source of within-run order, and `missing_inputs` gates each deterministic phase on its declared inputs. This plan repairs five RC-9 defects by editing that table and the readers around it: it deletes the producerless `factcheck` phase, moves `redteam` before `report` and replaces the report's filesystem probe with a declared input, wires the already-written `validate-fix` prompt in as a real phase whose gate file `verify` consumes, moves the external-boundary rule from a prompt into `calibrate`, and narrows verify's write-back to the findings it touched.

**Tech Stack:** Python 3.11 (standard library only in `sec_overlay/`), pytest, ruff, ty, `uv` for every command. All commands run from `plugins/sec-overlay/skills/sec-overlay/helpers/`.

**Spec:** `docs/superpowers/specs/2026-09-01-sec-overlay-defect-repairs-design.md` (Section 5, Group 1)

## Global Constraints

- Requirement numbering starts at REQ-40. REQ-35 through REQ-39 stay unused; the prior spec names a phantom REQ-35.
- The test baseline is 1766 tests passing at plugin version 1.122.0. Run the full suite after the group.
- Run `uv run ruff check sec_overlay/ bench/ tests/` and `uv run ty check` after the group.
- One requirement per red-green pair. The red commit adds the failing acceptance test. The green commit adds the code. A single commit holding both skips the red phase.
- Carry the requirement id in both commit subjects.
- Stage explicit paths only. Never bypass the hooks. Run `prek run` before each commit.
- Bump the plugin version in `plugins/sec-overlay/.claude-plugin/plugin.json` in the same commit as any shipping-file change. Everything under `helpers/` and `agents/` is a shipping file, including `README.md` files and tests.
- REQ-42 carries a `BREAKING CHANGE:` footer and bumps major. The plugin reaches `2.0.0` in that commit.
- Stage the touched folder's `README.md` in the same commit, plus `plugins/sec-overlay/CHANGELOG.md`.
- `helpers/sec_overlay/models.py` and `helpers/sec_overlay/evidence.py` are byte-pinned by `helpers/tests/test_frozen_contract.py`. Any edit to either file requires recomputing its sha256 in that test and a hand-sync of the separate Go port.
- Do not merge and do not push. The branch is `docs/sec-overlay-defect-repairs-spec`.
- REQ-40 and REQ-43 change the phase order. A workspace resumed from a 1.x run re-runs phases. This is accepted.

---

## Pre-flight scan

Every `file:line` below was confirmed against HEAD `ade301a`, plugin version `1.122.0`.

### Rulings taken against plugin HEAD

| # | Ruling | Why |
|---|---|---|
| R-1 | REQ-42 also updates both frozen-contract digests. | Removing `"fact-checked"` from `evidence.py:25` and the `models.py:6` docstring breaks the byte pins at `test_frozen_contract.py:30-31`. Leaving the value in place would create the RC-14 defect Group 2 exists to remove. Spec §4 already accepts that schema closure fails runs that pass today. |
| R-2 | REQ-40 reverses `test_redteam_precedes_the_artifact_gate` (`test_phases.py:92-101`). | That test asserts `selfscore < redteam`. The new order is `demote-noise, redteam, report, selfscore, prove, artifact-gate`. `agents/redteam.md` reads only `{{WORKSPACE}}/findings/*.json` and `{{WORKSPACE}}/kb/*`, never `report.md`, so the move is safe. |
| R-3 | REQ-40 keeps `has_redteam_plan` as an explicit parameter instead of deleting it. | The caller knows; the filesystem probe does not. `write_report` gains the parameter with default `False`, and the driver's report action passes `True` because the phase contract guarantees the file. `cli.py:305` and `cli.py:836` are review-mode paths with no redteam phase, which is why the default is `False`. |
| R-4 | REQ-44 is smaller than the spec frames it. | `write_findings` (`workspace.py:145-157`) writes one file per finding, so a concurrent writer's *new* finding is never deleted — only a *modified* one is overwritten with verify's stale copy. The fix is a `touched` list, not a re-read and merge. |
| R-5 | REQ-41 demotes to `NEEDS_DEPLOYMENT_TESTING`, not `RAW`. | `report.py:429-431` builds the external bucket from NDT findings filtered on `completeness_tier == "external-unverifiable"`. Demoting to `RAW`, as `agents/validate.md:91-93` instructs, would erase the finding from the report. `_SCOREABLE` (`calibrate.py:30`) already contains NDT, so the mutation is safe inside the calibrate loop. |
| R-6 | REQ-43 is one phase, and `apply_fix_gates` never sets `status`. | `scoring.py:1-10` states the module computes the verdict, never the LLM. The agent writes gate statuses to `kb/gates/validate-fix.json`; `apply_fix_gates` calls `score_fix` and records the verdict; `verify` keeps sole ownership of promotion. That makes both the promote branch and the `verify:conflict` branch at `verify.py:363-371` reachable. |

### Drift rows

| Row | HEAD state | Action |
|---|---|---|
| `test_report.py:349` | `write_report(ws)` after writing `redteam-plan.md`; asserts `"redteam-plan.md" in md`. | REQ-40 green step changes the call to `write_report(ws, has_redteam_plan=True)`. The default is `False`, so the assertion would otherwise fail. |
| `test_report.py:604` | Comment reads `# pointer present unconditionally`. | REQ-40 green step reworks the comment to `# pointer present when a plan exists (the default)`. The assertion itself stays true under the default. |
| `test_phases.py:58-59` | `assert names.index("trace") < names.index("factcheck") < names.index("calibrate")`. | REQ-42 green step deletes both lines and the ISSUE-047 comment above them. |
| `test_phases.py:119` | `"factcheck"` inside `original_order`. | REQ-42 green step deletes the entry. The list filters `PHASE_TABLE` down to its own members, so the `redteam` move alone does not break it. |
| `test_driver.py:282-308` | Two tests exercising `_act_factcheck`. | REQ-42 green step deletes both. |
| `test_factcheck_baseline_envelope.py` | Holds two F8 factcheck tests plus the unrelated F10 `test_baseline_cap` and F15 neutralization tests. | REQ-42 green step deletes only the two F8 tests and the `sec_overlay.factcheck` import, then `git mv`s the file to `test_baseline_envelope.py`. |
| `test_calibrate.py:459-477` | Asserts `risk_score <= 3` and `completeness_tier`, never `status`. | REQ-41 red step adds a new test for the status demotion rather than editing this one. |
| `agents/validate-fix.md:87-100` | The `## Output` section tells the agent to write `status` and `verification` directly. | REQ-43 green step rewrites the section to write `kb/gates/validate-fix.json` instead. |

### Resulting phase order

```
route-census, recon, recall-gate, architecture, arch-gate, threat_model, tm-gate,
prefilter, investigate, findings-gate, dedupe, critic, judge, validate, trace,
calibrate, patch, validate-fix, verify, demote-noise, redteam, report, selfscore,
prove, artifact-gate, artifact-review, artifact-consistency, postflight
```

28 phases before, 27 after REQ-42's deletion, 28 again after REQ-43 adds `validate-fix`.

---

## File Structure

**Created:**
- `helpers/tests/test_phase_artifact_contract.py` — the group's acceptance tests. Task 1 creates it; every later task extends it.

**Deleted:**
- `helpers/sec_overlay/factcheck.py`
- `helpers/agents/factcheck.md` (path: `plugins/sec-overlay/skills/sec-overlay/agents/factcheck.md`)

**Renamed:**
- `helpers/tests/test_factcheck_baseline_envelope.py` → `helpers/tests/test_baseline_envelope.py`

**Modified:**
- `helpers/sec_overlay/phases.py` — the phase table and one new path helper
- `helpers/sec_overlay/driver.py` — the action registry, `_act_factcheck` removal, `_act_verify`
- `helpers/sec_overlay/report.py` — `has_redteam_plan` threading, probe removal
- `helpers/sec_overlay/verify.py` — `apply_fix_gates`, the `touched` write-back
- `helpers/sec_overlay/calibrate.py` — the external-boundary demotion
- `helpers/sec_overlay/evidence.py` — drop `"fact-checked"`
- `helpers/sec_overlay/models.py` — drop `fact-checked` from the docstring
- `helpers/tests/test_frozen_contract.py` — both digests
- `references/finding.schema.json`, `references/prompt-constants.md` — the `verification` enum
- `agents/validate.md`, `agents/validate-fix.md`, `agents/README.md`
- `skills/sec-overlay/SKILL.md`, `skills/sec-overlay/CLAUDE.md`

---

## Task 1: Delete the factcheck phase (REQ-42)

The phase's only input, `kb/verdicts.json`, has no producing phase. `phases.py:132-135` therefore declares no inputs at all, `_act_factcheck` no-ops when the file is absent, and every run records `factcheck: done` after doing nothing.

**Files:**
- Create: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_phase_artifact_contract.py`
- Delete: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/factcheck.py`
- Delete: `plugins/sec-overlay/skills/sec-overlay/agents/factcheck.md`
- Rename: `helpers/tests/test_factcheck_baseline_envelope.py` → `helpers/tests/test_baseline_envelope.py`
- Modify: `helpers/sec_overlay/phases.py:132-135`, `helpers/sec_overlay/driver.py:26`, `:295-317`, `:447`
- Modify: `helpers/sec_overlay/evidence.py:23-26`, `helpers/sec_overlay/models.py:6`
- Modify: `helpers/tests/test_frozen_contract.py:30-31`
- Modify: `references/finding.schema.json:28`, `references/prompt-constants.md:190-192`
- Modify: `helpers/tests/test_phases.py:57-59`, `:119`, `helpers/tests/test_driver.py:282-308`
- Modify: `agents/README.md:69`, `:176`, `helpers/README.md:100`, `:148`, `helpers/sec_overlay/README.md:372-378`, `:1212-1217`, `helpers/tests/README.md`
- Modify: `helpers/tests/test_docs_invariants.py:185`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `helpers/tests/test_phase_artifact_contract.py`, the file every later task appends to. The `verification` closed enum becomes `{"verified-static", "static-only", "not-fixed", "verify-error"}` — four values, no `"fact-checked"`.

- [ ] **Step 1: Write the failing tests**

Create `helpers/tests/test_phase_artifact_contract.py`:

```python
"""Group 1 (RC-9) acceptance tests: no phase reads what no earlier phase writes.

Each test names the requirement it pins. The defects these cover all share one
shape — a reader whose input has no producer, so the stage ledger records work
that never happened.
"""

from __future__ import annotations

from sec_overlay.workspace import Workspace


def test_factcheck_phase_is_deleted() -> None:
    # REQ-42: the phase's only input (kb/verdicts.json) had no producing phase,
    # so every run recorded `factcheck: done` after doing nothing.
    from sec_overlay.driver import DETERMINISTIC_ACTIONS
    from sec_overlay.phases import PHASE_TABLE

    assert "factcheck" not in [p.name for p in PHASE_TABLE]
    assert "factcheck" not in DETERMINISTIC_ACTIONS


def test_no_verification_value_lacks_a_writer() -> None:
    # REQ-42: `fact-checked` was written only by the deleted factcheck stage.
    from sec_overlay.evidence import VERIFICATION_VALUES

    assert "fact-checked" not in VERIFICATION_VALUES


def test_the_factcheck_module_and_prompt_are_gone() -> None:
    # REQ-42: a deleted phase must leave no CLI-callable module behind.
    import importlib.util

    assert importlib.util.find_spec("sec_overlay.factcheck") is None
    overlay_root = Workspace(__import__("pathlib").Path("/nonexistent")).root.parents
    del overlay_root  # placeholder guard removed below
```

Replace that last test with the prompt-file check, which needs the skill root rather than a workspace:

```python
def test_the_factcheck_module_and_prompt_are_gone() -> None:
    # REQ-42: a deleted phase must leave no CLI-callable module and no prompt.
    import importlib.util
    from pathlib import Path

    assert importlib.util.find_spec("sec_overlay.factcheck") is None
    skill_root = Path(__file__).resolve().parents[2]
    assert not (skill_root / "agents" / "factcheck.md").exists()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_phase_artifact_contract.py -v`
Expected: all three FAIL — `"factcheck" not in [...]` is False, `"fact-checked"` is in `VERIFICATION_VALUES`, and `find_spec` returns a spec.

- [ ] **Step 3: Commit the red state**

```bash
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_phase_artifact_contract.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "test(sec-overlay): pin the REQ-42 factcheck deletion"
```

Bump `version` to `1.122.1`. Add a `helpers/tests/README.md` row for the new file and a CHANGELOG entry.

- [ ] **Step 4: Delete the phase row and the driver wiring**

In `helpers/sec_overlay/phases.py`, delete the three-line comment and the row:

```python
    # No inputs/outputs declared: kb/verdicts.json is optional (Plan B emits the
    # fact-check agent that writes it) and a hard input gate would halt every run
    # until then. _act_factcheck no-ops silently when the file is absent.
    PhaseSpec("factcheck", "deterministic", (), ()),
```

In `helpers/sec_overlay/driver.py`, delete the import at `:26`:

```python
from sec_overlay.factcheck import apply_verdict, validate_verdict
```

delete the whole `_act_factcheck` function (`:295-317`), and delete the registry entry:

```python
        "factcheck": _act_factcheck,
```

- [ ] **Step 5: Delete the module and the prompt**

```bash
cd plugins/sec-overlay/skills/sec-overlay
trash helpers/sec_overlay/factcheck.py agents/factcheck.md
```

- [ ] **Step 6: Close the verification enum**

In `helpers/sec_overlay/evidence.py:23-26`:

```python
VERIFICATION_VALUES = frozenset(
    {"verified-static", "static-only", "not-fixed", "verify-error"}
)
```

In `helpers/sec_overlay/models.py`, the module docstring's last sentence becomes:

```
Verification values: ``verified-static | static-only | not-fixed | verify-error``.
```

In `references/finding.schema.json:27-29`:

```json
      "verification": {
        "enum": ["verified-static", "static-only", "not-fixed", "verify-error", null]
      },
```

In `references/prompt-constants.md:190-192`:

```
- **`verification` (closed enum):** `verified-static`, `static-only`, `not-fixed`,
  `verify-error`. Any other value is rejected when a finding loads. Never write prose
  here.
```

- [ ] **Step 7: Recompute both frozen-contract digests**

`models.py` and `evidence.py` are byte-pinned. Recompute:

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
python3 -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" sec_overlay/models.py
python3 -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" sec_overlay/evidence.py
```

Write both results into `helpers/tests/test_frozen_contract.py:30-31`, replacing:

```python
_MODELS_SHA256 = "0640eae390e1f2d6292a5ed2c15bbf2756d64dac0f9b6e5dd4a1bdf364261949"
_EVIDENCE_SHA256 = "870ab9d3348195f8fdbbcf67d09aa5ea22c5f31b75d85b677d5a027d4b3519c7"
```

The Go port must receive the identical change by hand. An executor cannot obtain sign-off mid-plan, so record the obligation in the commit body: `Go port needs the same two-file change by hand; digests updated per test_frozen_contract.py's stated procedure.`

- [ ] **Step 8: Update the tests the deletion invalidates**

In `helpers/tests/test_phases.py`, delete the comment and assertion at `:57-59`:

```python
    # ISSUE-047: factcheck applies the validate phase's verdict artifact.
    assert names.index("trace") < names.index("factcheck") < names.index("calibrate")
```

and delete `"factcheck",` from `original_order` at `:119`.

In `helpers/tests/test_driver.py`, delete the two tests spanning `:282-308` that exercise `_act_factcheck`.

In `helpers/tests/test_factcheck_baseline_envelope.py`, delete the import line

```python
from sec_overlay.factcheck import apply_verdict, validate_verdict
```

and the two tests `test_factcheck_verified_corrected_rejected` and `test_factcheck_validation`. Keep `test_baseline_cap` and the two F15 neutralization tests. Then rename:

```bash
git mv helpers/tests/test_factcheck_baseline_envelope.py helpers/tests/test_baseline_envelope.py
```

In `helpers/tests/test_docs_invariants.py:184-186`, the comment names `factcheck` as a deliberately omitted phase. Reword it to name only `demote-noise`:

```python
    # The CLAUDE.md phase-order block is a condensed operator view: it deliberately
    # omits some PHASE_TABLE rows (demote-noise), so the enforced invariant is
    # relative order, not one label per row.
```

- [ ] **Step 9: Remove the remaining document references**

Delete or reword every factcheck mention in: `agents/README.md:69` (drop the `INV -.re-check.-> FC["factcheck.md"]` edge from the mermaid diagram) and `:176`; `helpers/README.md:100`, `:148`; `helpers/sec_overlay/README.md:372-378` and `:1212-1217`; `helpers/tests/README.md:252`, `:385`, `:433-436`, `:674`, `:1152`, `:1191`.

Do not touch `helpers/sec_overlay/correlate/workspace.py:46,48` — that is a different `verdicts.json` inside the correlate subpackage.

- [ ] **Step 10: Run the group tests, then the full suite**

Run: `uv run pytest tests/test_phase_artifact_contract.py -v`
Expected: 3 PASS.

Run: `uv run pytest -q`
Expected: all pass. The count drops below 1766 — four tests are deleted and three added.

- [ ] **Step 11: Lint and type-check**

Run: `uv run ruff check sec_overlay/ bench/ tests/ && uv run ty check`
Expected: clean.

- [ ] **Step 12: Commit the green state**

Bump `version` to `2.0.0`. Then:

```bash
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phases.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/driver.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/factcheck.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/evidence.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/models.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/ \
        plugins/sec-overlay/skills/sec-overlay/agents/ \
        plugins/sec-overlay/skills/sec-overlay/references/finding.schema.json \
        plugins/sec-overlay/skills/sec-overlay/references/prompt-constants.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
prek run
git commit
```

Commit message:

```
feat(sec-overlay)!: delete the factcheck phase

The phase's only input, kb/verdicts.json, had no producing phase. The row
therefore declared no inputs, the action no-opped when the file was absent,
and every run recorded `factcheck: done` after doing nothing. The
`fact-checked` verification value had no writer for the same reason.

Go port needs the same two-file change by hand; digests updated per
test_frozen_contract.py's stated procedure.

BREAKING CHANGE: the `factcheck` phase name, the `sec_overlay.factcheck`
module, the `agents/factcheck.md` prompt, and the `fact-checked` verification
value are removed. A workspace resumed from a 1.x run carries a `factcheck`
stage key that no longer maps to a phase.
```

---

## Task 2: Move redteam before report and delete the probe (REQ-40)

`report.py:679` probes the filesystem for `redteam-plan.md`, but `redteam` runs after `report`, so on a first pass the probe is always false while `render_ndt` names the file unconditionally. The report tells the reader to open a file the run has not written.

**Files:**
- Modify: `helpers/sec_overlay/phases.py:140-142`
- Modify: `helpers/sec_overlay/report.py:225-270`, `:292-315`, `:376-389`, `:465-470`, `:524-530`, `:541-563`, `:612-624`, `:679`, `:706-715`
- Modify: `helpers/sec_overlay/driver.py:324-325`
- Modify: `helpers/tests/test_phase_artifact_contract.py`
- Modify: `helpers/tests/test_phases.py:92-101`, `helpers/tests/test_report.py:349`, `:604`
- Modify: `skills/sec-overlay/CLAUDE.md:54-99`

**Interfaces:**
- Consumes: `helpers/tests/test_phase_artifact_contract.py` from Task 1.
- Produces:
  - `render_ndt(f: Finding, *, has_redteam_plan: bool = True) -> str`
  - `_ndt_next_actions(ndt: list[Finding], *, has_redteam_plan: bool = True) -> dict[str, str]`
  - `to_markdown(..., has_redteam_plan: bool = False, ...) -> str` — the existing keyword, now caller-supplied
  - `write_finding_details(ws, findings, patch_statuses=None, *, has_redteam_plan: bool = True) -> list[str]`
  - `write_report(ws, *, target=None, ..., has_redteam_plan: bool = False) -> dict`
  - Phase order: `redteam` sits between `demote-noise` and `report`; `report` declares `_redteam_plan` as an input.

- [ ] **Step 1: Write the failing tests**

Append to `helpers/tests/test_phase_artifact_contract.py`:

```python
def test_report_declares_the_redteam_plan_as_an_input(tmp_path) -> None:
    # REQ-40: the report named redteam-plan.md unconditionally while the phase
    # that writes it ran later. Declare it, so the driver gates on it.
    from sec_overlay.phases import PHASE_TABLE, missing_inputs

    ws = Workspace(tmp_path / "w")
    ws.ensure()
    report = next(p for p in PHASE_TABLE if p.name == "report")
    assert missing_inputs(report, ws) == [ws.reports / "redteam-plan.md"]


def test_redteam_runs_before_report() -> None:
    # REQ-40: reversal of the prior invariant. redteam produced an artifact the
    # report links, so it must precede the report, not follow it.
    from sec_overlay.phases import PHASE_TABLE

    names = [p.name for p in PHASE_TABLE]
    assert names.index("demote-noise") < names.index("redteam") < names.index("report")
    assert names.index("report") < names.index("selfscore") < names.index("artifact-gate")


def test_render_ndt_omits_the_redteam_pointer_when_no_plan_exists() -> None:
    # REQ-40: review mode renders a report with no redteam phase.
    from sec_overlay.models import Finding, FindingStatus, Severity
    from sec_overlay.report import render_ndt

    f = Finding(
        id="F-1",
        rule_id="r",
        cls="xss",
        status=FindingStatus.NEEDS_DEPLOYMENT_TESTING,
        severity=Severity.HIGH,
        file="a.py",
        line=1,
        message="m",
    )
    assert "redteam-plan.md" not in render_ndt(f, has_redteam_plan=False)


def test_report_module_holds_no_redteam_plan_probe() -> None:
    # REQ-40: the caller knows whether the plan exists; the filesystem does not.
    import inspect

    from sec_overlay import report

    src = inspect.getsource(report)
    assert 'redteam-plan.md").exists()' not in src
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_phase_artifact_contract.py -v`
Expected: the four new tests FAIL. `missing_inputs` returns `[]`, `redteam` sits after `selfscore`, `render_ndt` rejects the keyword with `TypeError`, and the probe source is present.

- [ ] **Step 3: Commit the red state**

Bump `version` to `2.0.1`. Stage the test file, `helpers/tests/README.md`, `plugin.json`, and `plugins/sec-overlay/CHANGELOG.md`.

```bash
git commit -m "test(sec-overlay): pin the REQ-40 report input contract"
```

- [ ] **Step 4: Move the redteam row and declare the report input**

In `helpers/sec_overlay/phases.py`, the rows from `demote-noise` through `prove` become:

```python
    PhaseSpec("demote-noise", "deterministic", (_findings_dir,), (_findings_dir,)),
    PhaseSpec("redteam", "agent", (_findings_dir,), (_redteam_plan,), prompt="redteam.md"),
    PhaseSpec("report", "deterministic", (_findings_dir, _redteam_plan), (_report, _sarif)),
    PhaseSpec("selfscore", "deterministic", (_report,), (_findings_dir,)),
    PhaseSpec("prove", "agent", (_findings_dir,), (_prove_json,), prompt="prove.md"),
```

- [ ] **Step 5: Thread `has_redteam_plan` through the renderers**

In `helpers/sec_overlay/report.py`, change `render_ndt`'s signature and make its trailing pointer conditional:

```python
def render_ndt(f: Finding, *, has_redteam_plan: bool = True) -> str:
```

and at the end of the body, replace the unconditional line at `:270`:

```python
    if has_redteam_plan:
        out += ["_Runnable payloads + telemetry: see `redteam-plan.md`._", ""]
```

Change `_ndt_next_actions` to take the flag and fall back to text that names no file:

```python
def _ndt_next_actions(
    ndt: list[Finding], *, has_redteam_plan: bool = True
) -> dict[str, str]:
    """Map each needs-runtime finding to its next action.

    Args:
        ndt: The needs-runtime findings, already filtered of external-unverifiable.
        has_redteam_plan: True when the run produced ``redteam-plan.md``. When
            False the actions name no file, because none exists.

    Returns:
        A mapping of finding id to next-action text.

    Example:
        >>> _ndt_next_actions([])
        {}
    """
    disc = discriminate(ndt)
    if not has_redteam_plan:
        return {f.id: "no runtime plan produced" for f in ndt}
    actions = {f.id: "see redteam-plan gaps" for f in disc["below_bar"]}
    actions.update({f.id: "see redteam-plan preconditions" for f in disc["unrunnable"]})
    actions.update({f.id: "run redteam-plan directive" for f in disc["needs_runtime"]})
    return actions
```

In `to_markdown`, pass the flag into both call sites. At `:465-470`:

```python
    ndt_actions = _ndt_next_actions(ndt, has_redteam_plan=has_redteam_plan)
    default_action = "see redteam-plan gaps" if has_redteam_plan else "no runtime plan produced"
    all_triage = [
        (f, "needs-runtime", ndt_actions.get(f.id, default_action)) for f in ndt
    ] + [
        (f, "confirmed", "bump" if f.cls == "deps" else "apply fix (§ below)") for f in conf
    ]
```

and in the external-leads block at `:512-522`:

```python
        for f in external:
            lines += ["", render_ndt(f, has_redteam_plan=has_redteam_plan)]
```

- [ ] **Step 6: Thread the flag through the writers and delete the probe**

Add the keyword to `write_finding_details`:

```python
def write_finding_details(
    ws: Workspace,
    findings: list[Finding],
    patch_statuses: dict[str, str] | None = None,
    *,
    has_redteam_plan: bool = True,
) -> list[str]:
```

and at `:558`:

```python
        body = render_ndt(f, has_redteam_plan=has_redteam_plan)
```

Add `has_redteam_plan: bool = False` as the last keyword parameter of `write_report`, delete the probe at `:679`:

```python
    has_redteam_plan = (ws.reports / "redteam-plan.md").exists()
```

and pass the parameter through to both `to_markdown` (`:706-715`, already keyed) and `write_finding_details` (`:720`):

```python
    write_finding_details(
        ws,
        reportable + ndt,
        patch_statuses=patch_statuses,
        has_redteam_plan=has_redteam_plan,
    )
```

- [ ] **Step 7: Make the driver assert the contract**

In `helpers/sec_overlay/driver.py:324-325`, the report action passes `True`, because the phase's declared input guarantees the file:

```python
def _act_report(ctx: AuditContext) -> None:
    write_report(ctx.ws, target=ctx.target, has_redteam_plan=True)
```

Leave `cli.py:305` and `cli.py:836` alone. Both are review-mode paths with no redteam phase, and the `False` default is correct for them.

- [ ] **Step 8: Update the two invalidated tests**

In `helpers/tests/test_phases.py:92-101`, replace the test body and its comment:

```python
def test_redteam_precedes_the_report():
    # REQ-40 reverses the earlier invariant: redteam writes redteam-plan.md, which
    # the report links and now declares as an input, so redteam runs first.
    # artifact_gate.run_artifact_gate still hard-requires the file, and still runs
    # later.
    from sec_overlay.phases import PHASE_TABLE

    names = [p.name for p in PHASE_TABLE]
    assert names.index("demote-noise") < names.index("redteam") < names.index("report")
    assert names.index("report") < names.index("artifact-gate")
    rt = next(p for p in PHASE_TABLE if p.name == "redteam")
    assert rt.kind == "agent" and rt.prompt == "redteam.md"
```

In `helpers/tests/test_report.py:348`, the call becomes:

```python
    write_report(ws, has_redteam_plan=True)
```

At `:604`, reword the trailing comment:

```python
    assert "redteam-plan.md" in out  # pointer present when a plan exists (the default)
```

- [ ] **Step 9: Update the operator phase-order block**

In `skills/sec-overlay/CLAUDE.md:54-99`, move the `14.4 Red Team` entry above `14 Report`, renumber it so the list stays ascending, and replace its four-line comment. The old comment says the driver dispatches redteam after selfscore; it now dispatches before report. State that `report` declares `reports/redteam-plan.md` as an input and that `artifact_gate.run_artifact_gate` still requires the file.

`test_docs_invariants.py::test_claude_md_phase_order_tracks_phase_table` enforces relative order between the labelled phases, so this edit is mandatory, not cosmetic.

- [ ] **Step 10: Run the tests**

Run: `uv run pytest tests/test_phase_artifact_contract.py tests/test_phases.py tests/test_report.py tests/test_docs_invariants.py -q`
Expected: all pass.

Run: `uv run pytest -q && uv run ruff check sec_overlay/ bench/ tests/ && uv run ty check`
Expected: clean.

- [ ] **Step 11: Commit**

Bump `version` to `2.0.2`.

```bash
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phases.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/driver.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/ \
        plugins/sec-overlay/skills/sec-overlay/skills/sec-overlay/CLAUDE.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
prek run
git commit -m "fix(sec-overlay): run redteam before the report (REQ-40)"
```

Note: the CLAUDE.md path above is `plugins/sec-overlay/skills/sec-overlay/CLAUDE.md`. Confirm the path before staging.

---

## Task 3: Wire validate-fix as a phase (REQ-43)

`agents/validate-fix.md` and `scoring.py:score_fix` both ship, and nothing calls either. `verify.py:363-371` branches on a `validate-fix:` history event that no phase writes, so the `verify:conflict` branch is dead code.

**Files:**
- Modify: `helpers/sec_overlay/phases.py` — one path helper, one new row, one input change
- Modify: `helpers/sec_overlay/verify.py` — add `apply_fix_gates`
- Modify: `helpers/sec_overlay/driver.py` — `_act_verify`
- Modify: `agents/validate-fix.md:87-100`
- Modify: `helpers/tests/test_phase_artifact_contract.py`
- Modify: `skills/sec-overlay/SKILL.md:521-523`

**Interfaces:**
- Consumes: the phase table shape from Task 2.
- Produces:
  - `_validate_fix_json(ws: Workspace) -> Path` in `phases.py`, returning `ws.kb / "gates" / "validate-fix.json"`
  - `apply_fix_gates(ws: Workspace) -> int` in `verify.py`, returning the count of findings it stamped
  - Phase `PhaseSpec("validate-fix", "agent", (_findings_dir,), (_validate_fix_json,), prompt="validate-fix.md")` between `patch` and `verify`
  - `verify`'s inputs become `(_findings_dir, _validate_fix_json)`
  - Gate file shape: `{"<finding-id>": {"root_cause": "pass|partial|fail|skip", "instance_coverage": ..., "no_new_vulnerabilities": ..., "best_practices": ...}}`

- [ ] **Step 1: Write the failing tests**

Append to `helpers/tests/test_phase_artifact_contract.py`:

```python
def _confirmed_with_patch(fid: str):
    from sec_overlay.models import Finding, FindingStatus, Severity

    return Finding(
        id=fid,
        rule_id="r",
        cls="authz",
        status=FindingStatus.CONFIRMED,
        severity=Severity.HIGH,
        file="a.py",
        line=1,
        message="m",
        patch_diff="--- a/a.py\n+++ b/a.py\n",
    )


def test_validate_fix_is_a_phase_between_patch_and_verify() -> None:
    # REQ-43: the prompt and score_fix both shipped with no caller, so
    # verify.py's `verify:conflict` branch was unreachable.
    from sec_overlay.phases import PHASE_TABLE

    names = [p.name for p in PHASE_TABLE]
    assert names.index("patch") < names.index("validate-fix") < names.index("verify")
    vf = next(p for p in PHASE_TABLE if p.name == "validate-fix")
    assert vf.kind == "agent" and vf.prompt == "validate-fix.md"


def test_verify_declares_the_validate_fix_gate_as_an_input(tmp_path) -> None:
    # REQ-43: verify reads the gate file, so the driver must gate on it.
    from sec_overlay.phases import PHASE_TABLE, missing_inputs

    ws = Workspace(tmp_path / "w")
    ws.ensure()
    verify = next(p for p in PHASE_TABLE if p.name == "verify")
    assert missing_inputs(verify, ws) == [ws.kb / "gates" / "validate-fix.json"]


def test_apply_fix_gates_records_the_verdict_without_setting_status(tmp_path) -> None:
    # REQ-43: scoring.py computes the verdict, never the LLM, and verify keeps
    # sole ownership of promotion.
    import json

    from sec_overlay.models import FindingStatus
    from sec_overlay.verify import apply_fix_gates
    from sec_overlay.workspace import read_findings, write_findings

    ws = Workspace(tmp_path / "w")
    ws.ensure()
    write_findings(ws, [_confirmed_with_patch("F-1")])
    (ws.kb / "gates").mkdir(parents=True, exist_ok=True)
    (ws.kb / "gates" / "validate-fix.json").write_text(
        json.dumps(
            {
                "F-1": {
                    "root_cause": "pass",
                    "instance_coverage": "partial",
                    "no_new_vulnerabilities": "partial",
                    "best_practices": "pass",
                }
            }
        )
    )

    assert apply_fix_gates(ws) == 1
    f = read_findings(ws)[0]
    assert f.status is FindingStatus.CONFIRMED  # apply_fix_gates never promotes
    events = [h.get("event") for h in f.history]
    assert "validate-fix:partial" in events


def test_score_fix_has_a_non_test_caller() -> None:
    # REQ-43: score_fix shipped with no production caller.
    import inspect

    from sec_overlay import verify

    assert "score_fix" in inspect.getsource(verify)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_phase_artifact_contract.py -v`
Expected: the five new tests FAIL. `validate-fix` is not in `PHASE_TABLE`, `missing_inputs(verify, ws)` returns `[]`, and `sec_overlay.verify` has no `apply_fix_gates`.

- [ ] **Step 3: Commit the red state**

Bump `version` to `2.0.3`. Stage the test file, `helpers/tests/README.md`, `plugin.json`, `plugins/sec-overlay/CHANGELOG.md`.

```bash
git commit -m "test(sec-overlay): pin the REQ-43 validate-fix phase"
```

- [ ] **Step 4: Add the path helper and the phase row**

In `helpers/sec_overlay/phases.py`, add the helper beside the other gate helpers:

```python
def _validate_fix_json(ws: Workspace) -> Path:
    return ws.kb / "gates" / "validate-fix.json"
```

Then change the `patch` through `verify` rows:

```python
    PhaseSpec("patch", "agent", (_findings_dir,), (_findings_dir,), prompt="patch.md"),
    PhaseSpec(
        "validate-fix",
        "agent",
        (_findings_dir,),
        (_validate_fix_json,),
        prompt="validate-fix.md",
    ),
    PhaseSpec(
        "verify", "deterministic", (_findings_dir, _validate_fix_json), (_findings_dir,)
    ),
```

`validate-fix` has an output that is not also an input, so `run_audit` (`driver.py:505-510`) auto-advances once the agent writes the file and dispatches-and-stops until then. That is the same contract `redteam` uses.

- [ ] **Step 5: Add `apply_fix_gates`**

In `helpers/sec_overlay/verify.py`, add the import and the function. Place the function directly above `verify_findings`.

```python
from sec_overlay.scoring import score_fix
```

```python
def apply_fix_gates(ws: Workspace) -> int:
    """Score the validate-fix agent's per-gate statuses and record each verdict.

    The agent supplies gate statuses only. ``scoring.score_fix`` computes the
    verdict, so an LLM cannot promote a finding by writing a status field. This
    function never sets ``status``: ``verify_findings`` owns promotion, and its
    ``verify:conflict`` branch reads the history event written here.

    Args:
        ws: The audit workspace. ``kb/gates/validate-fix.json`` must exist; the
            phase table declares it as verify's input, so a missing file is a
            driver-level halt, not a case to tolerate here.

    Returns:
        The number of findings stamped with a verdict.

    Raises:
        FileNotFoundError: The gate file is absent.
        json.JSONDecodeError: The gate file is not valid JSON.

    Example:
        >>> from sec_overlay.scoring import score_fix
        >>> score_fix({"root_cause": "pass", "instance_coverage": "pass",
        ...            "no_new_vulnerabilities": "pass", "best_practices": "pass"})[0]
        'fixed'
    """
    gates = json.loads((ws.kb / "gates" / "validate-fix.json").read_text())
    touched: list[Finding] = []
    for f in read_findings(ws):
        entry = gates.get(f.id)
        if not isinstance(entry, dict):
            continue
        verdict, score = score_fix(entry)
        f.history.append({"event": f"validate-fix:{verdict}", "score": score})
        if verdict in ("partial", "not_fixed"):
            f.verification = "not-fixed"
        elif verdict == "unverifiable":
            f.verification = "verify-error"
        touched.append(f)
    if touched:
        write_findings(ws, touched)
    return len(touched)
```

Add `import json` at the top if the module lacks it, and confirm `Finding`, `read_findings`, and `write_findings` are already imported. They are, because `verify_findings` uses all three.

- [ ] **Step 6: Call it from the verify action**

In `helpers/sec_overlay/driver.py`, the verify action becomes:

```python
def _act_verify(ctx: AuditContext) -> None:
    apply_fix_gates(ctx.ws)
    verify_findings(ctx.ws, ctx.target, ctx.config)
```

Add `apply_fix_gates` to the existing `from sec_overlay.verify import ...` line. Do not call it from inside `verify_findings`: the many unit tests that call `verify_findings` directly build no gate file, and a tolerant reader there would recreate the RC-9 shape this group removes.

- [ ] **Step 7: Rewrite the prompt's Output section**

In `agents/validate-fix.md`, replace lines 87-100 (`## Output` through the return-a-table sentence) with:

```markdown
## Output
Write `{{WORKSPACE}}/kb/gates/validate-fix.json`. The file maps each validated
finding id to its four gate statuses:

```json
{
  "AUTHZ-0001": {
    "root_cause": "pass",
    "instance_coverage": "partial",
    "no_new_vulnerabilities": "pass",
    "best_practices": "skip"
  }
}
```

Write the file even when you validated nothing. An empty object (`{}`) is the
correct output for a run with no patched findings, and the phase does not
complete until the file exists.

Do not edit any finding's `status` or `verification`. `verify.apply_fix_gates`
calls `score_fix` on these statuses, records the verdict in the finding's
history, and the deterministic `verify` phase decides promotion. A verdict you
write by hand would bypass the scoring weights.

Return a table: finding id, per-gate status, and which persona supplied the
deciding citation.
```

- [ ] **Step 8: Update SKILL.md**

`skills/sec-overlay/SKILL.md:521-523` describes the verify step. Add one sentence naming the `validate-fix` phase, its gate file, and the fact that scoring is deterministic.

- [ ] **Step 9: Run the tests**

Run: `uv run pytest tests/test_phase_artifact_contract.py tests/test_verify.py tests/test_phases.py tests/test_contract_lint.py -q`
Expected: all pass.

Run: `uv run pytest -q && uv run ruff check sec_overlay/ bench/ tests/ && uv run ty check`
Expected: clean.

- [ ] **Step 10: Commit**

Bump `version` to `2.1.0`.

```bash
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phases.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/verify.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/driver.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/ \
        plugins/sec-overlay/skills/sec-overlay/agents/validate-fix.md \
        plugins/sec-overlay/skills/sec-overlay/agents/README.md \
        plugins/sec-overlay/skills/sec-overlay/SKILL.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
prek run
git commit -m "feat(sec-overlay): wire validate-fix as a phase (REQ-43)"
```

---

## Task 4: Enforce the external-boundary rule in calibrate (REQ-41)

`agents/validate.md:89-93` forbids the validate agent from confirming an external-boundary finding. A prompt rule is not an enforcer: the trace phase runs after validate and can set the blocker later, and no code checks the outcome. Move the rule into `calibrate`, which runs at index 16, after `trace`.

**Files:**
- Modify: `helpers/sec_overlay/calibrate.py:265-270`
- Modify: `agents/validate.md:89-93`, `agents/README.md:139`
- Modify: `helpers/tests/test_phase_artifact_contract.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: after `calibrate`, no finding with `reachability.blocker == "external-boundary"` holds `FindingStatus.CONFIRMED`. Such a finding carries `status = NEEDS_DEPLOYMENT_TESTING`, `completeness_tier = "external-unverifiable"`, `risk_score <= 3`, and a `calibrate:external-boundary` history event.

- [ ] **Step 1: Write the failing tests**

Append to `helpers/tests/test_phase_artifact_contract.py`:

```python
def test_calibrate_demotes_an_external_boundary_confirmation(tmp_path) -> None:
    # REQ-41: the rule lived only in the validate prompt, and trace runs after
    # validate, so a blocker set by trace was never enforced.
    from sec_overlay.calibrate import calibrate
    from sec_overlay.models import Finding, FindingStatus, Severity
    from sec_overlay.workspace import read_findings, write_findings

    ws = Workspace(tmp_path / "w")
    ws.ensure()
    write_findings(
        ws,
        [
            Finding(
                id="EXT-1",
                rule_id="r",
                cls="ssrf",
                status=FindingStatus.CONFIRMED,
                severity=Severity.HIGH,
                file="a.py",
                line=1,
                message="m",
                reachability={"blocker": "external-boundary"},
            )
        ],
    )

    calibrate(ws)

    f = read_findings(ws)[0]
    assert f.status is FindingStatus.NEEDS_DEPLOYMENT_TESTING
    assert f.completeness_tier == "external-unverifiable"
    assert f.risk_score <= 3


def test_the_validate_prompt_no_longer_bans_external_boundary() -> None:
    # REQ-41: an unenforced prompt rule is worse than no rule; calibrate owns it.
    from pathlib import Path

    prompt = (Path(__file__).resolve().parents[2] / "agents" / "validate.md").read_text()
    assert "external-boundary" not in prompt
```

Check `calibrate`'s exported name before running: the function in `helpers/sec_overlay/calibrate.py` that holds the scoring loop is the one to import. If the public entry point is named differently, use that name in both the test and Step 4.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_phase_artifact_contract.py -v`
Expected: both FAIL. The status stays `CONFIRMED`, and `agents/validate.md` still contains the banned phrase.

- [ ] **Step 3: Commit the red state**

Bump `version` to `2.1.1`. Stage the test file, `helpers/tests/README.md`, `plugin.json`, `plugins/sec-overlay/CHANGELOG.md`.

```bash
git commit -m "test(sec-overlay): pin the REQ-41 external-boundary demotion"
```

- [ ] **Step 4: Add the demotion**

In `helpers/sec_overlay/calibrate.py`, the external-boundary block becomes:

```python
                if _is_external_boundary(f):
                    f.risk_score = min(f.risk_score, _EXTERNAL_CAP)
                    f.completeness_tier = "external-unverifiable"
                    if f.status is FindingStatus.CONFIRMED:
                        # REQ-41: the report's external bucket reads NDT findings,
                        # so demote to NDT, not RAW — RAW would erase the finding.
                        f.status = FindingStatus.NEEDS_DEPLOYMENT_TESTING
                    if not any(h.get("event") == "calibrate:external-boundary" for h in f.history):
                        f.history.append({"event": "calibrate:external-boundary"})
```

`_SCOREABLE` at `calibrate.py:30` already contains both `CONFIRMED` and `NEEDS_DEPLOYMENT_TESTING`, so the mutation does not change which findings the loop processes.

- [ ] **Step 5: Remove the prompt rule**

In `agents/validate.md`, delete the second and third sentences of the block at `:89-93`, keeping the dataflow instruction:

```markdown
If your independent trace differs from the recorded `dataflow`, correct it.
```

In `agents/README.md:139`, delete the line documenting the validate-phase ban. Leave `:153` alone — it describes a different rule. Confirm before editing.

- [ ] **Step 6: Run the tests**

Run: `uv run pytest tests/test_phase_artifact_contract.py tests/test_calibrate.py tests/test_selfscore.py tests/test_report.py -q`
Expected: all pass. `test_calibrate.py:459-477` asserts only `risk_score` and `completeness_tier`, so it stays green.

Run: `uv run pytest -q && uv run ruff check sec_overlay/ bench/ tests/ && uv run ty check`
Expected: clean.

- [ ] **Step 7: Commit**

Bump `version` to `2.1.2`.

```bash
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/calibrate.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/ \
        plugins/sec-overlay/skills/sec-overlay/agents/validate.md \
        plugins/sec-overlay/skills/sec-overlay/agents/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
prek run
git commit -m "fix(sec-overlay): enforce external-boundary in calibrate (REQ-41)"
```

---

## Task 5: Narrow verify's write-back (REQ-44)

`verify.py:392` writes the whole finding set from the snapshot read at `:349`. A finding modified by another writer between those two points is overwritten with verify's stale copy.

**Files:**
- Modify: `helpers/sec_overlay/verify.py:327-397`
- Modify: `helpers/tests/test_phase_artifact_contract.py`

**Interfaces:**
- Consumes: `apply_fix_gates` from Task 3 (same module, no signature dependency).
- Produces: `verify_findings` writes only the findings whose history or fields it changed. Its return type stays `int`.

- [ ] **Step 1: Write the failing test**

Append to `helpers/tests/test_phase_artifact_contract.py`:

```python
def test_verify_writes_back_only_the_findings_it_touched(tmp_path) -> None:
    # REQ-44: verify read the whole set, then wrote the whole set. A finding
    # another writer changed in between was overwritten with verify's stale copy.
    from sec_overlay.models import Finding, FindingStatus, Severity
    from sec_overlay.verify import verify_findings
    from sec_overlay.workspace import read_findings, write_findings

    ws = Workspace(tmp_path / "w")
    ws.ensure()
    untouched = Finding(
        id="U-1",
        rule_id="r",
        cls="xss",
        status=FindingStatus.RAW,  # no patch_diff, so verify skips it
        severity=Severity.LOW,
        file="b.py",
        line=2,
        message="m",
    )
    write_findings(ws, [_confirmed_with_patch("F-1"), untouched])

    def _writer_races(*args, **kwargs):
        # Simulate a concurrent writer mutating U-1 after verify's read.
        other = next(f for f in read_findings(ws) if f.id == "U-1")
        other.message = "changed by another writer"
        write_findings(ws, [other])
        return "not-fixed"

    verify_findings(ws, tmp_path, {}, verifier=_writer_races)

    survivor = next(f for f in read_findings(ws) if f.id == "U-1")
    assert survivor.message == "changed by another writer"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_phase_artifact_contract.py::test_verify_writes_back_only_the_findings_it_touched -v`
Expected: FAIL — `survivor.message` is `"m"`, because verify's whole-set write restored the stale copy.

- [ ] **Step 3: Commit the red state**

Bump `version` to `2.1.3`. Stage the test file, `helpers/tests/README.md`, `plugin.json`, `plugins/sec-overlay/CHANGELOG.md`.

```bash
git commit -m "test(sec-overlay): pin the REQ-44 verify write-back scope"
```

- [ ] **Step 4: Replace the `changed` flag with a `touched` list**

In `helpers/sec_overlay/verify.py`, inside `verify_findings`:

Replace the initialisation:

```python
    changed = False
```

with:

```python
    touched: list[Finding] = []
```

Then replace each of the three `changed = True` statements. In the conflict branch:

```python
            f.history.append({"event": "verify:conflict", "reason": (...)})
            touched.append(f)
            continue
```

After the cause event:

```python
        f.history.append({"event": f"verify:cause:{cause}"})
        f.verification = verification
        touched.append(f)
```

And the write-back at the end:

```python
    if touched:
        write_findings(ws, touched)
    record_stage(ws, "verify")
    return fixed
```

`write_findings` (`workspace.py:145-157`) writes one file per finding, so a subset write is correct and no barrier is needed. Keep the `(...)` reason text exactly as it stands in the source; do not retype it from this plan.

- [ ] **Step 5: Run the tests**

Run: `uv run pytest tests/test_phase_artifact_contract.py tests/test_verify.py -q`
Expected: all pass.

Run: `uv run pytest -q && uv run ruff check sec_overlay/ bench/ tests/ && uv run ty check`
Expected: clean.

- [ ] **Step 6: Commit**

Bump `version` to `2.1.4`.

```bash
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/verify.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/ \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
prek run
git commit -m "fix(sec-overlay): write back only touched findings (REQ-44)"
```

---

## Group verification

- [ ] **Step 1: Full suite**

Run: `cd plugins/sec-overlay/skills/sec-overlay/helpers && uv run pytest -q`
Expected: all pass. The count moves non-monotonically against the 1766 baseline: Task 1 deletes four tests and adds three, and Tasks 2 to 5 add eleven more.

- [ ] **Step 2: Lint and types**

Run: `uv run ruff check sec_overlay/ bench/ tests/ && uv run ty check`
Expected: clean.

- [ ] **Step 3: Manifest validation**

Run: `cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools && claude plugin validate .`
Expected: valid.

- [ ] **Step 4: Confirm the phase order**

Run:

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
uv run python -c "from sec_overlay.phases import PHASE_TABLE; print([p.name for p in PHASE_TABLE])"
```

Expected: 28 phases, with `patch, validate-fix, verify, demote-noise, redteam, report, selfscore, prove, artifact-gate` in that order and no `factcheck`.

- [ ] **Step 5: Log the major-version decision**

Spec §9 requires the major-version decision in `docs/decisions.md`. Add one section in the Decision / Context / Alternatives / Reasoning / Trade-offs / Supersedes form, recording that REQ-42 removes a phase name, a CLI-callable module, a documented prompt, and a `verification` enum value, and that no resume-across-version guarantee exists today. Commit it on its own.

- [ ] **Step 6: Stop**

Do not merge and do not push. Report the suite count, the version reached, and the Go-port hand-sync obligation from Task 1 Step 7.

---

## Self-review

**Spec coverage.** Group 1 holds five requirements. REQ-40 is Task 2, REQ-41 is Task 4, REQ-42 is Task 1, REQ-43 is Task 3, REQ-44 is Task 5. Each acceptance test in the spec's Group 1 table maps to a test in `test_phase_artifact_contract.py`: the report naming no absent file and no remaining probe (Task 2 Steps 1, tests 1 and 4); the external-boundary demotion and the removed prompt rule (Task 4); the absent `factcheck` stage key, module, and prompt (Task 1); the reachable `verify:conflict` branch and `score_fix`'s non-test caller (Task 3); the surviving concurrent write (Task 5).

**Two spec acceptance criteria are met indirectly.** "The `verify:conflict` branch at `verify.py:363-371` is reachable" is proven by `test_apply_fix_gates_records_the_verdict_without_setting_status` writing a `validate-fix:partial` event that the branch reads, combined with the existing verify tests that exercise the branch. A dedicated end-to-end conflict test is not added, because the existing suite already covers the branch given a history event. "No run records a `factcheck` stage key" is proven by the absent phase row, since `record_stage` is only called with a phase name.

**Placeholders.** Task 1 Step 1 shows a discarded first draft of the third test followed by its replacement. That is deliberate — the draft's `Workspace(...).root.parents` line is wrong, and the step says to replace it. No other step defers content.

**Type consistency.** `has_redteam_plan: bool` keeps one name across `render_ndt`, `_ndt_next_actions`, `to_markdown`, `write_finding_details`, and `write_report`. Its default is `True` on the two renderers whose existing test call sites pass no keyword, and `False` on the two writers that review mode calls. `apply_fix_gates(ws) -> int` matches `verify_findings`'s `-> int` convention, and `touched: list[Finding]` matches the name used in Task 5. `_validate_fix_json` follows the `_recall_gate_json` naming already in `phases.py`.

**One unresolved name.** Task 4 imports `calibrate` from `sec_overlay.calibrate`. The scoring loop's public entry point was read at `calibrate.py:228-294` but its `def` line sits above that window. Task 4 Step 1 instructs the executor to confirm the name before running.
