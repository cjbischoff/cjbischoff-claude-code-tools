---
phase: 03-rule-matching-review-modes
plan: 07
subsystem: sec-overlay-review-mode
tags: [python, review-mode, gate-chain, disposition-ladder, gap-closure]

requires:
  - phase: 03-rule-matching-review-modes (plan 05)
    provides: findings_gate.disposition_without_receipt (D-12 ladder), dead until this plan wired it
  - phase: 03-rule-matching-review-modes (plan 06)
    provides: cli.run_review wired to a real review_agent finding source
provides:
  - "cli.run_review's reflection loop reads apply_profile's kept output and actually removes a retracted finding from the reported ledger"
  - "review_findings.apply_profile assigns disposition via the D-12 ladder (needs-deployment-testing for thread-safety, unconfirmed for the four static-checkable classes)"
  - "composed end-to-end proof that both fixes hold through the real CLI path"
affects: [phase-04-scale, any-future-review-mode-reporting-work]

actuals:
  tokens: 5242
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Function-local import to break a reverse-import cycle (findings_gate imports from review_findings at module level; review_findings imports findings_gate.disposition_without_receipt inside apply_profile only)"

key-files:
  created: []
  modified:
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_findings.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_live.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_profiles.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md
    - plugins/sec-overlay/CHANGELOG.md
    - plugins/sec-overlay/.claude-plugin/plugin.json

key-decisions:
  - "Task 2's new disposition-ladder tests use a fixture local to each test, never a mutation of _dual_run_fixture — its one thread-safety entry is gate-C (unconditional drop under both profiles), so it can never exercise a kept thread-safety finding."
  - "Task 3's composed test relies on the real reflection.apply_verdict called with an empty verdict dict (cli.run_review's actual call), which keeps every finding by construction — no monkeypatch needed to represent 'reflection keeps it'."

patterns-established:
  - "Deferred (function-local) import is the sanctioned way to reference a symbol across a two-module cycle in this codebase; document the cycle reason in a one-line comment, not what the import does."

requirements-completed: [REV-02, REV-03]

coverage:
  - id: D1
    description: "A reflection retraction removes the retracted finding from review_findings in the ledger, with a matching reflection_retractions entry"
    requirement: "REV-02"
    verification:
      - kind: unit
        ref: "tests/test_review_live.py::test_reflection_retraction_removes_a_live_finding"
        status: pass
    human_judgment: false
  - id: D2
    description: "A per-file reflection failure isolates to that file (reflection_skipped) without affecting other files' findings"
    requirement: "REV-02"
    verification:
      - kind: unit
        ref: "tests/test_review_live.py::test_reflection_failure_for_one_file_leaves_other_files_unaffected"
        status: pass
    human_judgment: false
  - id: D3
    description: "A finding on a path the reflection loop never visits survives untouched"
    requirement: "REV-02"
    verification:
      - kind: unit
        ref: "tests/test_review_live.py::test_finding_on_an_unreflected_path_survives"
        status: pass
    human_judgment: false
  - id: D4
    description: "A kept thread-safety finding ships needs-deployment-testing via the D-12 ladder"
    requirement: "REV-03"
    verification:
      - kind: unit
        ref: "tests/test_review_profiles.py::test_apply_profile_assigns_needs_deployment_testing_for_thread_safety"
        status: pass
    human_judgment: false
  - id: D5
    description: "Every static-checkable class (null-dereference, error-swallowing, resource-leak, injection) ships unconfirmed via the D-12 ladder"
    requirement: "REV-03"
    verification:
      - kind: unit
        ref: "tests/test_review_profiles.py::test_apply_profile_assigns_unconfirmed_for_each_static_checkable_class"
        status: pass
    human_judgment: false
  - id: D6
    description: "Both fixes proven together through the real CLI path: a thread-safety finding ships needs-deployment-testing end to end"
    requirement: "REV-03"
    verification:
      - kind: integration
        ref: "tests/test_review_live.py::test_thread_safety_finding_ships_needs_deployment_testing_end_to_end"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-08-19
status: complete
---

# Phase 03 Plan 07: Review Wiring Gap Closure Summary

**Closed two mechanically-confirmed defects (CR-01, WR-01) in the review-mode gate chain: a reflection retraction now actually removes its finding from the reported ledger, and `apply_profile` now routes every kept general-defect finding through the D-12 disposition ladder instead of hardcoding `unconfirmed`.**

## Performance

- **Duration:** 55 min
- **Started:** 2026-08-19T12:30:00Z (approx, prior to this session's visible window)
- **Completed:** 2026-08-19T13:25:54Z
- **Tasks:** 3/3
- **Files modified:** 8

## Accomplishments

- `cli.run_review`'s reflection loop now reads each reviewable file's findings from `apply_profile`'s kept output (`review_findings`), not the position gate's pre-profile list, and rebinds `review_findings` to exclude every retracted id across the whole loop — a retraction now removes its finding from the ledger instead of only recording the retraction event.
- `review_findings.apply_profile` calls `findings_gate.disposition_without_receipt` (via a function-local import that avoids the reverse-import cycle with `findings_gate`) for every kept finding with a classified defect class — a kept thread-safety finding now ships `needs-deployment-testing`, and the four static-checkable classes still ship `unconfirmed`.
- A composed end-to-end test proves both fixes hold together through the real `run_review` CLI path, not only at unit level.

## Task Commits

Each task was committed atomically:

1. **Task 1: run_review's reflection loop reports survivors (REV-02)** - `fb5aca7` (fix)
2. **Task 2: apply_profile assigns via the D-12 ladder (REV-03)** - `45dafc1` (fix)
3. **Task 3: End-to-end proof and phase gate receipt** - `5cf439e` (test)

_Note: this plan's tasks are `tdd="true"` bug-fix tasks — each is a single RED-confirmed-then-fixed commit, not a separate test/feat/refactor sequence, matching the plan's own commit-subject instructions._

## Files Created/Modified

- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py` - reflection loop rewired to read/rebind against `apply_profile`'s output; docstring corrected (Task 1)
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_findings.py` - `apply_profile` routes disposition through `disposition_without_receipt`; module docstring and disposition comment updated (Task 2)
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_live.py` - retraction-absence rewrite, multi-file isolation test, unreflected-path-survives test (Task 1); composed end-to-end disposition test (Task 3)
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_profiles.py` - two new disposition-ladder tests plus an extended never-assigns-confirmed test (Task 2)
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md` - one paragraph per task describing the fix mechanism
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md` - one paragraph per task describing the new/changed tests
- `plugins/sec-overlay/CHANGELOG.md` - one `### Fixed`/`### Added` entry per commit (1.61.1, 1.61.2, 1.61.3)
- `plugins/sec-overlay/.claude-plugin/plugin.json` - version bumped 1.61.0 → 1.61.3 across the three commits

## Decisions Made

- Task 2's new tests build a fixture local to each test rather than extending `_dual_run_fixture` — that shared fixture's one thread-safety entry is gate-C (an unconditional drop under both profiles), so it structurally cannot produce a kept thread-safety finding; mutating it to add one would also risk the committed D-10 baseline comparison test.
- Task 3's composed test does not fake `apply_verdict`: `cli.run_review` calls the real `reflection.apply_verdict` with an empty verdict dict, which by construction retracts nothing, so it already is the "reflection keeps it" case the plan asked for.

## Deviations from Plan

None - plan executed exactly as written. Task 2's disposition-ladder tests and Task 3's composed test match the plan's `<behavior>` specs; no Rule 1-4 auto-fixes were needed beyond the plan's own instructions.

## Issues Encountered

For Task 2, edited `review_findings.py` before writing the RED tests (out of TDD order). Caught before running anything: reverted the production file with `git checkout -- sec_overlay/review_findings.py`, ran the new tests against the pre-fix code to confirm the required RED failure (`test_apply_profile_assigns_needs_deployment_testing_for_thread_safety` failed with `'unconfirmed' == 'needs-deployment-testing'`), then reapplied the same fix and confirmed GREEN. No functional impact — the committed diff is TDD-correct even though the drafting order briefly wasn't.

## User Setup Required

None - no external service configuration required.

## Phase Gate Receipt (Task 3)

Run from `plugins/sec-overlay/skills/sec-overlay/helpers/`:

- `uv run ruff check .` → **All checks passed!** (exit 0)
- `uv run ty check` → **Found 9 diagnostics**, all `unresolved-attribute` on `R.stdout` in `tests/test_review_tracer.py` (exit 1) — pre-existing, unrelated to any file this plan touches; zero new diagnostics.
- `uv run pytest -q` → **1169 passed, 2 failed** (exit 1) — the two documented environmental failures (`test_bench.py::test_seed_corpus_is_valid`, `test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd`, both gitignored-fixture/submodule gaps per 03-VERIFICATION.md), no third failure. 1169 = the 1161-passed baseline plus the 8 tests this plan added (2 new + 1 rewritten in Task 1, 1 new thread-safety test + 4-way parametrized static-checkable test + 1 extended test in Task 2, 1 new composed test in Task 3).
- `rg -n "dependencies" pyproject.toml` → `dependencies = []` — unchanged, still empty.

## Next Phase Readiness

REV-02 and REV-03 are both closed; `findings_gate.disposition_without_receipt` now has a live production call site. No blockers for Phase 4 (concurrency, SCALE-01, is explicitly out of scope per this plan's backstop truth).

---
*Phase: 03-rule-matching-review-modes*
*Completed: 2026-08-19*

## Self-Check: PASSED

- FOUND: `.planning/phases/03-rule-matching-review-modes/03-07-SUMMARY.md`
- FOUND: `fb5aca7`, `45dafc1`, `5cf439e`
