---
phase: 06-remediation-and-governed-release
plan: 05
subsystem: testing
tags: [sec-overlay, review-dispatch, e12-profile-subset, governance-receipt, defect-ledger]

# Dependency graph
requires:
  - phase: 06-remediation-and-governed-release (plans 01-04)
    provides: all four shipping fixes (WR-01/--workspace, redteam/postflight wiring, deps-template/doc corrections, frozen-contract/profile-subset tests) that this plan's ledger closes
  - phase: 05-end-to-end-verification-audit-review
    provides: 05-DEFECTS.md (11 deferred rows), the E-12 vacuous-comparison flag, and the base..head SHA range this plan re-reads verbatim
provides:
  - a real 14-file per-file reviewer dispatch (orchestrator-executed) into an isolated Phase 6 workspace, with a count-flip proof against Phase 5's all-skipped receipt
  - a non-vacuous E-12 profile-subset verdict computed over one identical recorded reviewer output set, consumed twice (security profile, general profile)
  - 06-RECEIPTS.md: sanitized commands, dispatch-mechanism deviation record, environment/version pins, the governance receipt (4 shipping PRs + this plan's zero-bump row), and the REL-03 re-assertion on the merged milestone branch
  - 06-DEFECTS.md: terminal disposition for all 11 Phase 5 defect rows plus a 12th newly-surfaced row, and the phase-closure statement against all four success criteria
  - Phase 6 closed in STATE.md (29/29 plans); milestone-to-main merge deferred to milestone close (D-14)
affects: [milestone-close, v5.0-MILESTONE-AUDIT]

# Actuals (#2632)
actuals:
  tokens: 26117
  tasks: 3
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dispatch mechanism deviation (Rule 4, Task 1 checkpoint): orchestrator spawns the 14 fresh-context review-file subagents directly since the executor's own toolset carries no Task/subagent-dispatch capability; the executor still owns sanitization, consumption, and verdict computation"
    - "E-12 profile-subset check runs both apply_profile() passes over one byte-identical recorded output set (no re-dispatch), making the security-kept subseteq general-kept comparison a genuine two-run-over-one-input demonstration"

key-files:
  created:
    - .planning/phases/06-remediation-and-governed-release/06-DEFECTS.md
  modified:
    - .planning/phases/06-remediation-and-governed-release/06-RECEIPTS.md
    - .planning/STATE.md
    - README.md
    - CHANGELOG.md

key-decisions:
  - "Task 1 boundary: d09-as-written — the D-09 sanitization boundary from Phase 6 context is used exactly as recorded, no widening or narrowing"
  - "E-12 closed non-vacuously by the live dispatch: security-kept=0, general-kept={5 ids}, ∅ ⊆ {5} holds and is genuinely non-vacuous — the primary D-08 path, not the Plan 04 unit-level backstop"
  - "D-05 mixing-criterion row dispositioned as unsatisfiable, not deferred: functions/ has only 5 commits in its entire history, so no diff range can ever satisfy both the file-count and mixing sub-criteria at once"
  - "06-02-SUMMARY.md's 'fast-forward, no merge commit' description of PR #24 is factually wrong (git cat-file -p c546511 shows 2 parents); recorded as a newly-surfaced, non-blocking doc-accuracy defect and carried, not fixed — editing a past plan's SUMMARY.md is outside this plan's files_modified scope, and an untriaged fifth PR would restart the governance rail"
  - "Governance receipt and REL-03 re-assertion consolidated into 06-RECEIPTS.md as the single source of truth; 06-DEFECTS.md points at it rather than duplicating the table, to avoid the two documents drifting apart"

patterns-established:
  - "Sanitized receipts cite command + exit code + key output field, never raw target-repo file contents or paths beyond what D-07 permits"

requirements-completed: [REL-01, REL-02, REL-03]

coverage:
  - id: D1
    description: "Real per-file reviewer dispatch (14 files) proves the count-flip against Phase 5's all-skipped baseline"
    requirement: REL-01
    verification:
      - kind: manual_procedural
        ref: "06-RECEIPTS.md, Command 2 (review_source_skipped: 0 vs Phase 5's 14)"
        status: pass
    human_judgment: false
  - id: D2
    description: "E-12 profile-subset verdict computed non-vacuously over one identical recorded output set"
    requirement: REL-01
    verification:
      - kind: manual_procedural
        ref: "06-RECEIPTS.md, E-12 verdict section (security-kept=0, general-kept={5}, not vacuous)"
        status: pass
    human_judgment: false
  - id: D3
    description: "All 11 Phase 5 defect rows plus a newly-surfaced 12th row given a terminal disposition"
    requirement: REL-01
    verification:
      - kind: manual_procedural
        ref: "06-DEFECTS.md, full ledger"
        status: pass
    human_judgment: false
  - id: D4
    description: "Governance receipt covers all 4 shipping PRs plus this plan's zero-bump row; REL-03 re-asserted on the merged milestone branch"
    requirement: REL-02
    verification:
      - kind: manual_procedural
        ref: "06-RECEIPTS.md, Governance receipt and REL-03 re-assertion sections"
        status: pass
      - kind: unit
        ref: "helpers/tests/test_frozen_contract.py::test_helpers_declare_zero_runtime_dependencies"
        status: pass
    human_judgment: false
  - id: D5
    description: "Phase 6 closed in STATE.md; four phase success criteria addressed individually against citations"
    requirement: REL-01
    verification:
      - kind: manual_procedural
        ref: "06-DEFECTS.md, Phase closure section; .planning/STATE.md"
        status: pass
    human_judgment: false

duration: unavailable (session spanned a context-compaction boundary; wall-clock start not captured)
completed: 2026-08-21
status: complete
---

# Phase 06 Plan 05: Real Dispatch, E-12 Verdict, Terminal Defect Ledger Summary

**A real 14-file reviewer dispatch produced a non-vacuous E-12 profile-subset verdict (security-kept=0, general-kept={5}), and every Phase 5 defect row now carries a terminal disposition, closing Phase 6.**

## Performance

- **Duration:** unavailable (session spanned a context-compaction boundary)
- **Tasks:** 3
- **Files modified:** 5 (`06-RECEIPTS.md`, `06-DEFECTS.md` new, `STATE.md`, `README.md`, `CHANGELOG.md`)

## Accomplishments

- Task 1 (checkpoint:decision): resolved the D-09 sanitization boundary as `d09-as-written` — used exactly as recorded in Phase 6 context, no widening or narrowing.
- Task 2: a real per-file reviewer dispatch (14 fresh-context `sonnet` `review-file` subagents, orchestrator-executed per the Rule 4 deviation below) ran against the same `base..head` range Phase 5 used, into an isolated Phase 6 workspace with Phase 5's sidecar confirmed byte-unchanged. Both a security-profile and a general-profile consume pass read the identical 14 recorded returns to compute the E-12 verdict: security-kept=0, general-kept={5 ids}, `∅ ⊆ {5}` holds and is genuinely non-vacuous — unlike Phase 5's both-empty comparison. Sanitized commands, environment pins, and the verdict are recorded in `06-RECEIPTS.md`.
- Task 3: every one of the 11 `05-DEFECTS.md` rows was given a terminal state in the new `06-DEFECTS.md` — 9 fixed with exact plan/commit citations, the mixing-criterion row dispositioned as unsatisfiable (`functions/` has only 5 commits total), and the cwd-scoping-bug row noted as already terminal from Phase 5 itself. A 12th, newly-surfaced row records that `06-02-SUMMARY.md` wrongly describes PR #24's merge as a fast-forward — `git cat-file -p c546511` shows a genuine two-parent merge commit — carried, not fixed. `06-RECEIPTS.md`'s governance-receipt section was filled with the 5-row shipping table (4 PRs + this plan's zero-bump row), REL-03 was re-asserted on the merged milestone branch, and the plan's four phase success criteria were each addressed individually with citations. `STATE.md` closed Phase 6 (29/29 plans); the milestone-to-main merge stays a separate step at milestone close (D-14).

## Task Commits

Each task was committed atomically:

1. **Task 1: Resolve D-09 sanitization boundary** — checkpoint:decision, resolved `d09-as-written`, no code/doc commit (decision recorded in Task 2's receipt).
2. **Task 2: Real dispatch, E-12 verdict, sanitized receipts** - `c5ea810` (docs)
3. **Task 3: Terminal defect ledger, governance receipt, phase closure** - `188ff37` (docs)

**Plan metadata:** (this commit) `docs(06-05): complete plan`

## Files Created/Modified

- `.planning/phases/06-remediation-and-governed-release/06-DEFECTS.md` - all 11 Phase 5 rows + 1 newly-surfaced row, each with a terminal disposition and citation
- `.planning/phases/06-remediation-and-governed-release/06-RECEIPTS.md` - Task 2's sanitized dispatch/E-12 receipt, plus Task 3's governance receipt and REL-03 re-assertion
- `.planning/STATE.md` - Phase 6 closed, progress at 29/29 plans, stale blockers resolved
- `README.md` - `.planning/` directory-guide row extended to cover this plan's outputs
- `CHANGELOG.md` - new `### Changed` bullet under `## Unreleased`

## Decisions Made

- Task 1 boundary: `d09-as-written` — the D-09 sanitization boundary is used exactly as recorded, no widening or narrowing.
- E-12 closed non-vacuously by the live dispatch (security-kept=0, general-kept={5}), the primary D-08 path — not merely Plan 04's unit-level backstop.
- D-05 mixing-criterion row dispositioned as unsatisfiable (5-commit `functions/` history makes the criterion structurally unreachable), not left deferred.
- The `06-02-SUMMARY.md` PR #24 merge-shape claim is factually wrong and is recorded, not silently corrected in that file (outside this plan's scope) or ignored (would leave a known inaccuracy unrecorded).
- Governance receipt and REL-03 re-assertion consolidated into `06-RECEIPTS.md` as the single source of truth; `06-DEFECTS.md` points at it instead of duplicating the table.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 4 - Architectural, resolved via checkpoint] Dispatch mechanism: orchestrator spawns the 14 review-file subagents, not the executor**
- **Found during:** Task 2
- **Issue:** The executor's own toolset carries no `Task`/subagent-dispatch capability, but Task 2 requires 14 real fresh-context reviewer dispatches.
- **Resolution:** Orchestrator ran the 14 dispatches directly against the target diff; the executor retained ownership of sanitization, consumption (both profile passes), and verdict computation. Recorded as a deviation in `06-RECEIPTS.md`'s "Dispatch mechanism" section, not silently absorbed.
- **Files modified:** `06-RECEIPTS.md`
- **Verification:** Receipt's count-flip proof (`review_source_skipped: 0` vs Phase 5's `14`) confirms the dispatch was real, not mocked.
- **Committed in:** `c5ea810` (Task 2 commit)

**2. [Rule 2 - missing critical documentation] Newly-surfaced PR #24 merge-shape inaccuracy recorded, not silently left**
- **Found during:** Task 3 (cross-checking prior plan summaries for exact commit citations)
- **Issue:** `06-02-SUMMARY.md` states PR #24 merged via fast-forward with no merge commit; `git cat-file -p c546511` and `git log --oneline --merges` show a genuine two-parent merge commit, matching the pattern of PRs #23/#25/#26.
- **Fix:** Recorded as row 12 of `06-DEFECTS.md` (carried, not fixed — editing a past plan's SUMMARY.md is outside this plan's `files_modified` scope, and per the plan's own instruction, an untriaged fifth PR would restart the governance rail) and reflected accurately in `06-RECEIPTS.md`'s governance table.
- **Files modified:** `06-DEFECTS.md`, `06-RECEIPTS.md`
- **Verification:** `git cat-file -p c546511` (2 parent lines) and `git log --oneline --merges docs/milestone-v5-diff-review` re-run and confirmed twice across the session.
- **Committed in:** `188ff37` (Task 3 commit)

---

**Total deviations:** 2 (1 architectural/Rule 4, resolved via checkpoint; 1 Rule 2 documentation gap, auto-fixed)
**Impact on plan:** Both deviations were necessary to complete the plan honestly — neither fabricates capability the executor doesn't have nor hides a discovered inaccuracy. No scope creep.

## Issues Encountered

None beyond the two deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 6 is closed (29/29 plans complete). All three REL requirements (REL-01, REL-02, REL-03) are satisfied per `06-DEFECTS.md`'s phase-closure statement. This plan's own PR (#27) merged into `docs/milestone-v5-diff-review` as merge commit `2a93058`; the milestone branch is synced. The milestone-to-main merge is a deliberate separate step at milestone close (D-14) and is not part of this plan or phase.

---
*Phase: 06-remediation-and-governed-release*
*Completed: 2026-08-21*

## Self-Check: PASSED

All 6 claimed files found on disk; all 3 claimed commit hashes (`c5ea810`, `188ff37`, `2a93058`) found in git history.
