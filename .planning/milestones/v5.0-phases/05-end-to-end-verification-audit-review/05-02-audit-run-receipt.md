# Phase 5 Plan 2: Audit run receipt

Sanitized per D-07 (one-way): no target-repo path below the repo root, no code
snippet, no finding body appears below. The `.sec-overlay` sidecar path is
permitted and required by D-09.

## Command

Run from `plugins/sec-overlay/skills/sec-overlay/helpers`:

```
uv run python -c "from sec_overlay.run import drive; print(drive('<target-repo-root>', config='rules/smoke.yaml'))"
```

First invocation halted before reaching the last `PHASE_TABLE` entry. Resumed
with the agent-phase loop `advance(<target-repo-root>, '<phase>')` /
re-`drive()` cycle documented in `audit.md`, closing with:

```
uv run python -m sec_overlay.postflight --workspace <sidecar-path> --sha <pinned-sha>
```

## Pinned pass SHA

`80e2abca4f0b53d056537e3281bf430089bbf7c8`

Captured before the run via `git -C <target-repo-root> rev-parse HEAD` and
confirmed unchanged in the sidecar's `run.env` and at every later checkpoint.

## Exit codes

- First `drive()` call: exit 1 (`sec_overlay.driver.PhaseHalt`). Decisive tail:
  `artifact-gate rejected 5 issue(s): artifact-gate: redteam-plan.md is
  missing — run the red-team phase first; artifact-gate: shipping finding
  ... has no red-team directive` (named for 4 shipping findings).
- `python -m sec_overlay.redteam --workspace <sidecar-path> --target
  <target-repo-root>` (run twice — see Deviation below): exit 0 both times.
- `advance(<target-repo-root>, 'artifact-gate')` (re-run after the redteam
  fix): exit 0.
- Second `drive()` call: exit 0, decisive tail `AUDIT COMPLETE`.
- `python -m sec_overlay.postflight --workspace <sidecar-path> --sha
  <pinned-sha>`: exit 0, decisive tail `prior_context.json now holds 1
  item(s)`.

## Environment

```
uv 0.11.32 (Homebrew 2026-07-23 x86_64-apple-darwin)
git version 2.55.0
Python 3.13.14
semgrep 1.171.0
CodeQL command-line toolchain release 2.26.1
ast-grep 0.45.0
osv-scanner version: 2.3.8
gitleaks 8.30.1
```

## Stage completeness

`phases.py`'s `PHASE_TABLE` holds 22 entries. All 22 recorded a `done` stage
in the sidecar's `state.json`, plus 2 out-of-table stages (`redteam`,
`postflight`) that the module-level CLI records itself — 24 stages total,
all `done`.

`kb/receipts/` in the sidecar holds 21 JSON receipts, one per deterministic
stage that ran (`findings-gate` has no separate receipt by design — an
expected non-defect per the plan's action notes, not a gap).
`kb/gates/redteam.json`, `kb/gates/redteam-adversary.json`, and
`kb/gates/artifact-review.json` hold the three agent-produced gate records
that sit alongside the deterministic receipts.

## Fence result

Before the run: `git -C <target-repo-root> status --porcelain` empty, HEAD at
the pinned SHA above.

After the run: `git -C <target-repo-root> status --porcelain
--untracked-files=no` empty. The tracked tree is byte-identical before and
after. The sidecar directory itself is untracked in the target and did not
trip the fence, confirming the flagged assumption in the plan's
`flagged_assumptions` block.

## Sidecar retention (D-09)

Sidecar path: `<target-repo-root>/.sec-overlay/mando-05-02-audit/`.
A second, earlier sidecar from Plan 01's work
(`<target-repo-root>/.sec-overlay/mando-c4872e65/`) also remains present.
Both are retained untouched until v5.0 ships through Phase 6 and the
milestone audit; neither was deleted, overwritten, or pruned during this
task.

## Headline finding counts

From `report.md`'s Bottom line and Triage table: 4 shipping findings — 1
confirmed critical (dependency advisory, lockfile-only match, reachability
not runtime-verified), 3 `needs-runtime` (routed into `redteam-plan.md`
directives). No finding was dropped, retracted, or position-review-required.
No file's review source was skipped. Dataflow coverage: 0% (LLM-shape-hunting
only, both counted languages), consistent with the "coverage & limitations"
honesty check the `artifact-review` gate performed.

## Deviation discovered during this task

The first `drive()` call halted at `artifact-gate` because `redteam` and
`postflight` are documented pipeline steps (`skills/sec-overlay/CLAUDE.md`'s
"Phase order" list, steps 13.5 and C2) that are not entries in `phases.py`'s
mechanical `PHASE_TABLE` and are therefore never invoked by `drive()` /
`advance()`. This is a real documentation-vs-implementation gap in the
shipped plugin, not an error in this run. Triaged as a run-blocker under
D-10 because it stopped the pass from reaching the last `PHASE_TABLE` entry;
closed by running the `redteam` producer role, the `redteam-adversary`
review role, and `postflight` as the separate module invocations the
plugin's own maintainer manual documents, then re-running `artifact-gate`
and `drive()` to completion. See `05-DEFECTS.md` for the full dispositioned
rows, including a second, related gap found while performing the redteam
producer role (a prose-vs-mechanics mismatch in the runtime-disposition
override), and a third, cosmetic finding-template rendering gap the
`artifact-review` role surfaced and correctly declined to fix under its
safety contract.
