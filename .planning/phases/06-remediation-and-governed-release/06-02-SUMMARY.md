---
phase: 06-remediation-and-governed-release
plan: "02"
subsystem: sec-overlay-driver
tags: [python, stdlib, phase-table, driver-dispatch, tdd, ci-governance, coderabbit]

# Dependency graph
requires:
  - phase: 06-remediation-and-governed-release
    plan: "01"
    provides: "proven governance rail (branch, per-commit version bump/CHANGELOG, PR against docs/milestone-v5-diff-review, manual CodeRabbit trigger, human-approved merge) and the empirical finding that CodeRabbit auto-review is disabled on non-default base branches"
provides:
  - "redteam PhaseSpec (agent, between selfscore and artifact-gate) and postflight PhaseSpec (deterministic, final row) added to PHASE_TABLE"
  - "postflight registered in DETERMINISTIC_ACTIONS via _act_postflight, closing D-01 for the deterministic half"
  - "maintainer manual (skills/sec-overlay/CLAUDE.md, README.md, helpers/README.md) phase-order lists corrected to match the live 24-entry PHASE_TABLE"
affects: [sec-overlay-runtime-dispatch, sec-overlay-docs]

# Actuals (#2632)
actuals:
  tokens: 6448
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "table-derived test guard: test_every_deterministic_phase_has_a_registered_action reads PHASE_TABLE at test time instead of a hardcoded key list, so the table and DETERMINISTIC_ACTIONS cannot drift apart silently again"

key-files:
  created: []
  modified:
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phases.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/driver.py
    - plugins/sec-overlay/skills/sec-overlay/CLAUDE.md
    - plugins/sec-overlay/skills/sec-overlay/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_phases.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_driver.py

key-decisions:
  - "redteam is kind=\"agent\", not deterministic — confirmed against the real dispatch path (skill CLAUDE.md's phase order runs agents/redteam.md then agents/redteam-adversary.md, never a bare module call), and against the plan's explicit correction that it must sit between selfscore and artifact-gate because artifact_gate.run_artifact_gate hard-requires redteam-plan.md to exist"
  - "Both Task 1 and Task 2 share one RED commit (c7848f4) instead of one each — it was written for both test files together in the prior session before this session's continuation began; retroactively splitting an already-pushed commit was judged more disruptive than documenting the shared RED as a deviation"
  - "test_redteam_is_not_a_deterministic_action and test_every_deterministic_phase_has_a_registered_action pass on first run before any implementation exists (redteam correctly absent from an empty-ish DETERMINISTIC_ACTIONS, and the table-derived guard is vacuous with nothing registered) — treated as invariant-preservation regression guards, not new-behavior proofs, so their pre-green pass is expected and not a RED-phase violation"
  - "CodeRabbit review on PR #24 hit the reviewer's rate limit (\"Review limit reached... 21 minutes\") rather than skipping or walkthrough-ing; user waived the wait-for-walkthrough requirement for this PR given the rate limit, so no CodeRabbit findings exist to address for this plan"

requirements-completed: [REL-01, REL-02]

coverage:
  - id: D1
    description: "redteam and postflight PhaseSpecs added to PHASE_TABLE (redteam between selfscore and artifact-gate, postflight as the final entry), preserving the original 22 entries' relative order"
    requirement: "REL-01"
    verification:
      - kind: unit
        ref: "tests/test_phases.py::test_phase_table_contains_redteam_and_postflight"
        status: pass
      - kind: unit
        ref: "tests/test_phases.py::test_redteam_precedes_the_artifact_gate"
        status: pass
      - kind: unit
        ref: "tests/test_phases.py::test_postflight_is_the_final_phase"
        status: pass
      - kind: unit
        ref: "tests/test_phases.py::test_original_phase_order_is_preserved"
        status: pass
      - kind: unit
        ref: "tests/test_phases.py::test_missing_inputs_reports_absent_artifacts_for_the_new_phases"
        status: pass
      - kind: unit
        ref: "tests/test_phases.py::test_outputs_present_tracks_the_postflight_artifact"
        status: pass
    human_judgment: false
  - id: D2
    description: "postflight registered in DETERMINISTIC_ACTIONS as _act_postflight; redteam stays unregistered as an agent phase"
    requirement: "REL-01"
    verification:
      - kind: unit
        ref: "tests/test_driver.py::test_postflight_is_a_registered_deterministic_action"
        status: pass
      - kind: unit
        ref: "tests/test_driver.py::test_redteam_is_not_a_deterministic_action"
        status: pass
      - kind: unit
        ref: "tests/test_driver.py::test_every_deterministic_phase_has_a_registered_action"
        status: pass
    human_judgment: false
  - id: D3
    description: "Maintainer-manual phase-order lists (skills/sec-overlay/CLAUDE.md, README.md, helpers/README.md) reconciled to name the same 24 phases in the same order as PHASE_TABLE, with standalone-invocation instructions reduced to a manual-re-run note"
    requirement: "REL-02"
    verification:
      - kind: manual_procedural
        ref: "side-by-side read of PHASE_TABLE names vs skills/sec-overlay/CLAUDE.md's numbered phase-order block after the edit (see Accomplishments)"
        status: pass
    human_judgment: false
  - id: D4
    description: "PR #24 opened against docs/milestone-v5-diff-review, merged, branch deleted, CodeRabbit outcome recorded (rate-limited, wait waived by user)"
    requirement: "REL-02"
    verification:
      - kind: other
        ref: "gh pr view 24 --json state,baseRefName,mergedAt"
        status: pass
    human_judgment: false

duration: ~55min (14min for the 3 implementation/doc commits; remainder was the CodeRabbit manual-trigger wait, which hit the reviewer's rate limit)
completed: 2026-08-21
status: complete
---

# Phase 06 Plan 02: Wire redteam and postflight into PHASE_TABLE Summary

**Added `redteam` (agent, before `artifact-gate`) and `postflight` (deterministic, final row) to the 22-entry `PHASE_TABLE`, registered `postflight` in `DETERMINISTIC_ACTIONS`, and reconciled three maintainer-doc phase-order lists that still described the pre-D-01 (unwired) ordering — closing D-01 so `run.drive()`/`run.advance()` reach both phases instead of silently skipping them.**

## Performance

- **Duration:** ~14 min for the 3 implementation/doc commits (13:15–13:29 local); wall-clock to merge was longer due to the CodeRabbit manual-review wait hitting a rate limit
- **Started:** 2026-08-21T13:15:21-06:00 (RED commit `c7848f4`)
- **Completed:** 2026-08-21 (PR #24 merged into `docs/milestone-v5-diff-review`)
- **Tasks:** 3
- **Files modified:** 11 (across the 3 implementation/doc commits; plus this SUMMARY and planning-state files in the final metadata commit)

## Accomplishments

- `PHASE_TABLE` grows from 22 to 24 entries: `redteam` (`kind="agent"`, `agents/redteam.md`, input `findings_dir`, output `redteam-plan.md`) inserted between `selfscore` and `artifact-gate` — not after `artifact-review`, because `artifact_gate.run_artifact_gate` hard-requires `redteam-plan.md` to exist before it runs. `postflight` (`kind="deterministic"`, input the artifact-review gate JSON, output `prior_context_path`) appended as the table's final row.
- `driver.py` gains `_act_postflight` (function-local import of `sec_overlay.postflight`, cycle-avoidance convention preserved) wrapping `postflight.run_postflight(ctx.ws, ctx.sha)`, with no try/except and no `PhaseHalt` — `run_postflight` returns a merged-item count, not a verdict. `redteam` gets no driver entry; it stays an agent phase dispatched by prompt, not by `DETERMINISTIC_ACTIONS`.
- `test_every_deterministic_phase_has_a_registered_action` now derives its expected key set from `PHASE_TABLE` itself instead of a hardcoded list, so the table and `DETERMINISTIC_ACTIONS` cannot silently drift apart again.
- Side-by-side count after the doc fix: `[p.name for p in PHASE_TABLE]` names 24 phases ending `..., report, selfscore, redteam, artifact-gate, artifact-review, postflight`; `skills/sec-overlay/CLAUDE.md`'s "Phase order (one pass)" block now reads `... 14 Report → 14.4 Red Team → 14.5 Artifact gate → 14.6 Artifact review → 15 Postflight`, matching order and adjacency (module-only steps like `selfscore` are a pre-existing gap in that numbered list, not a mismatch — see Deviations). The same `redteam`-after-`report`/`postflight`-last correction was applied to `skills/sec-overlay/README.md`'s pipeline diagram, worked-example table, and CLI legend, and to `skills/sec-overlay/helpers/README.md`'s deterministic-pipeline diagram.
- No doc surface still tells a maintainer to run `redteam` or `postflight` as a *required* standalone module call — each now carries a "PHASE_TABLE-wired (D-01)... remains available for a standalone manual re-run" note instead.
- PR #24 opened against `docs/milestone-v5-diff-review` (never `main`), merged, branch `fix/wire-redteam-and-postflight-phases` deleted.

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire redteam and postflight into PHASE_TABLE** — `4b73d5e` (fix) — shares its RED phase with Task 2 in `c7848f4` (see Deviations)
2. **Task 2: Register postflight as a deterministic action** — `61c5645` (fix)
3. **Task 3: Reconcile maintainer docs and ship the PR** — `73ef5b6` (docs)

**RED (shared, both tasks):** `c7848f4` — `test(06-02): add failing tests for redteam/postflight wiring`

**PR:** #24, merged `2026-08-21T20:08:49Z` into `docs/milestone-v5-diff-review` (fast-forward, no merge commit); branch `fix/wire-redteam-and-postflight-phases` deleted (local + remote)

**Plan metadata:** _see final commit hash in the completion message_

_Note: this plan's acceptance criteria called for five commits (one RED + one GREEN per task, plus the docs commit); it landed as four because Task 1 and Task 2's RED tests were written together in one commit before this session's continuation began — see Deviations._

## Files Created/Modified

- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phases.py` - adds the `redteam` and `postflight` `PhaseSpec` entries
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/driver.py` - adds `_act_postflight` and its `DETERMINISTIC_ACTIONS` registration
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_phases.py` - 6 new tests proving table shape, order, and I/O tracking for both new entries
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_driver.py` - 3 new tests proving `postflight` is registered, `redteam` is not, and the registered-action set is table-derived
- `plugins/sec-overlay/skills/sec-overlay/CLAUDE.md` - corrects the numbered phase-order list (`redteam` 13.5→14.4, `postflight` C2→15)
- `plugins/sec-overlay/skills/sec-overlay/README.md` - corrects the pipeline diagram, worked-example table, and CLI legend (also fixes a pre-existing `selfscore` misplacement in the CLI legend as a one-line adjacent fix)
- `plugins/sec-overlay/skills/sec-overlay/helpers/README.md` - corrects the deterministic-pipeline diagram's `redteam`/`report`/`postflight` ordering
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md` - documents the two new `PHASE_TABLE` entries and the `_act_postflight` registration
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md` - documents the 9 new test functions
- `plugins/sec-overlay/.claude-plugin/plugin.json` - `1.69.1` → `1.69.4` across the four commits
- `plugins/sec-overlay/CHANGELOG.md` - one entry per commit (`1.69.2`, `1.69.3`, `1.69.4`)

## Decisions Made

- `redteam`'s `kind="agent"` (not deterministic) was confirmed against the real dispatch path in `skills/sec-overlay/CLAUDE.md`'s phase-order table before writing the `PhaseSpec` — it runs `agents/redteam.md` (sonnet) then `agents/redteam-adversary.md` (opus), never a bare module call, so registering it in `DETERMINISTIC_ACTIONS` would have been wrong.
- `redteam` placed between `selfscore` and `artifact-gate`, not after `artifact-review` as `06-PATTERNS.md`'s rough draft had suggested — `artifact_gate.run_artifact_gate` hard-requires `redteam-plan.md` to exist before it runs, so redteam must precede the gate it feeds.
- CodeRabbit's manual `@coderabbitai review` trigger on PR #24 returned "Review limit reached... next review available in 21 minutes" (a Pro Plus per-developer OSS review-limit exhaustion), not a walkthrough and not the "auto-review disabled on non-default base branches" skip recorded in Plan 01. The user explicitly waived the wait-for-walkthrough requirement for this PR given the rate limit, so the PR merged without a CodeRabbit walkthrough having posted for this diff.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Adjacent fix] `selfscore` mispositioned in `skills/sec-overlay/README.md`'s CLI legend**
- **Found during:** Task 3 (doc reconciliation)
- **Issue:** The CLI legend listed `uv run python -m sec_overlay.selfscore` after `postflight`, with no phase number — already wrong before this plan touched the block.
- **Fix:** Moved the line to directly after `report`, before `redteam`, while already editing the surrounding lines for the `redteam`/`postflight` reorder.
- **Files modified:** `plugins/sec-overlay/skills/sec-overlay/README.md`
- **Verification:** Read the corrected block; order now matches `PHASE_TABLE`.
- **Committed in:** `73ef5b6` (Task 3 commit)

### Deferred (out of scope, logged not fixed)

- Pre-existing `selfscore`/`artifact-gate`/`artifact-review` nodes missing from `skills/sec-overlay/helpers/README.md`'s deterministic-pipeline mermaid diagram.
- Pre-existing: `skills/sec-overlay/CLAUDE.md`'s numbered "Phase order (one pass)" list never had a numbered `selfscore` entry, before or after this plan (confirmed via `git diff 9e3892e -- .../CLAUDE.md`).
- Both logged in full, with reasoning, in `.planning/phases/06-remediation-and-governed-release/deferred-items.md` under `## 06-02`.

### RED-commit structure deviation

- **[Rule 4-adjacent, documented not asked]** Plan's `<acceptance_criteria>` for Task 3 expects "five commits total for this plan" (one RED + one GREEN per task, plus the docs commit). This plan landed with four: Task 1 and Task 2's RED tests (`test_phases.py`, `test_driver.py`) were both written into the single commit `c7848f4` in the prior session, before this session's continuation began. Retroactively splitting an already-pushed, already-reviewed-by-CodeRabbit commit into two was judged more disruptive (rebase, force-push, re-review) than documenting the shared RED honestly. TDD discipline itself was not violated — RED was genuinely captured, in full, before any GREEN work started for either task; only the commit-count bookkeeping differs from the plan's expectation.

---

**Total deviations:** 1 auto-fixed adjacent fix (in-scope), 2 pre-existing gaps deferred (out of scope), 1 commit-structure deviation from a prior-session artifact (documented, not corrected retroactively).
**Impact on plan:** No scope creep; no correctness or security impact. The commit-count deviation is bookkeeping only — `git log --oneline docs/milestone-v5-diff-review..HEAD` shows 4 commits, each carrying `plugin.json` and `CHANGELOG.md`, rather than the 5 the plan anticipated.

## Issues Encountered

- **CodeRabbit rate limit on PR #24:** the manual `@coderabbitai review` trigger (required per Plan 01's finding that auto-review is disabled on non-default base branches) returned "Review limit reached... next review available in 21 minutes" instead of a walkthrough. A background wait-and-retry was started, then superseded by the user's explicit instruction to waive the wait for this PR given the rate limit. No CodeRabbit findings exist for this diff as a result — this is the honest outcome, not a walkthrough that was ignored.
- `claude plugin validate .` must be run from the repo root (`/Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools`), not from inside `plugins/sec-overlay/skills/sec-overlay/helpers/` — running it from the wrong cwd fails with "No manifest found in directory" since it looks for `.claude-plugin/marketplace.json` relative to cwd.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `PHASE_TABLE` and `DETERMINISTIC_ACTIONS` are now the single source of truth for the pipeline's 24 phases, and the maintainer docs agree with them — a future plan changing phase order only needs to update `phases.py`/`driver.py` plus the same three doc surfaces, following this plan's pattern.
- D-01 is closed: `run.drive()`/`run.advance()` now reach `redteam` and `postflight` instead of silently skipping them.
- Two documentation gaps remain deferred (see `deferred-items.md`) — neither blocks correctness, both are candidates for a future doc-only pass.
- CodeRabbit's per-developer OSS review-limit behavior (distinct from the auto-review-disabled-on-non-default-base finding from Plan 01) is now empirically recorded for any future plan in this phase that opens a PR against `docs/milestone-v5-diff-review` in quick succession.

## Self-Check: PASSED

- FOUND: `06-02-SUMMARY.md`
- FOUND: `c7848f4` (RED)
- FOUND: `4b73d5e` (Task 1 GREEN)
- FOUND: `61c5645` (Task 2 GREEN)
- FOUND: `73ef5b6` (Task 3 docs)
- PR #24: `state=MERGED`, `mergedAt=2026-08-21T20:08:49Z`, `baseRefName=docs/milestone-v5-diff-review`
- Branch `fix/wire-redteam-and-postflight-phases` confirmed absent from both `git branch` and `git ls-remote --heads origin`

---
*Phase: 06-remediation-and-governed-release*
*Completed: 2026-08-21*
