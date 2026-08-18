---
phase: 03-rule-matching-review-modes
plan: 04
subsystem: security-review
tags: [python, sec-overlay, review-profiles, tdd, sast]

requires:
  - phase: 03-rule-matching-review-modes
    provides: "03-03's per-language rule-doc general-defect classes (null-dereference, thread-safety, resource-leak, error-swallowing, injection)"
provides:
  - "review_findings.py: apply_profile(findings, profile) -> (kept, dropped), classify(finding), GENERAL_DEFECT_CLASSES, PROFILES, REVIEW_DISPOSITIONS, EXCLUSION_BLOCK_BY_PROFILE"
  - "cli.py review --profile security|general wired end-to-end into the position gate → report → ledger path"
  - "GENERAL_PROFILE_EXCLUSION_RULES block in prompt-constants.md, selected by profile in SKILL.md"
  - "committed dual-run baseline fixture proving the security profile did not regress"
affects: [rule-matching-review-modes, receipt-gate-disposition-ladder]

actuals:
  tokens: 11830
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "review_findings.py mirrors evidence.py's shape: frozensets + small pure predicates, no I/O, no state"
    - "ReviewFinding wrapper dataclass keeps review-mode metadata (defect_class, disposition, profile) off the frozen models.Finding contract"
    - "committed expected-output baseline fixture (JSON) for byte-identical no-regression proof, rather than recomputing inside the test"

key-files:
  created:
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_findings.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_profiles.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/fixtures/review_profiles_security_baseline.json
  modified:
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py
    - plugins/sec-overlay/skills/sec-overlay/references/prompt-constants.md
    - plugins/sec-overlay/skills/sec-overlay/SKILL.md
    - plugins/sec-overlay/skills/sec-overlay/README.md
    - plugins/sec-overlay/skills/sec-overlay/references/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md

key-decisions:
  - "Checkpoint decision: option-a — new review_findings.py module with a ReviewFinding wrapper, keeping models.Finding and the frozen FindingStatus enum untouched (D-11)."
  - "apply_profile returns a 2-tuple (kept, dropped), a deliberate divergence from review_position_gate's 3-tuple: profile gating is a pure allowlist decision over an already-positioned finding and can never produce a decline."
  - "Security-profile baseline is a committed JSON fixture (review_profiles_security_baseline.json), not recomputed inside the test, so a future regression fails the comparison instead of silently moving the baseline with it."

patterns-established:
  - "A profile-scoped feature adds a wrapper module beside the frozen contract rather than extending it, when the contract is a byte-mirrored cross-language boundary."

requirements-completed: [REV-01]

coverage:
  - id: D1
    description: "review --profile security produces output byte-identical to pre-phase gate behavior on the dual-run fixture"
    requirement: REV-01
    verification:
      - kind: unit
        ref: "tests/test_review_profiles.py#test_dual_run_security_profile_matches_committed_baseline_no_regression"
        status: pass
    human_judgment: false
  - id: D2
    description: "review --profile general output is a strict, non-empty superset of the security output, with every added finding carrying an allowlisted defect_class"
    requirement: REV-01
    verification:
      - kind: unit
        ref: "tests/test_review_profiles.py#test_dual_run_general_profile_is_a_strict_superset_of_the_security_baseline"
        status: pass
    human_judgment: false
  - id: D3
    description: "Gates C, D, and E drop findings identically under both profiles; only A/B relax for the five allowlisted general-defect classes"
    requirement: REV-01
    verification:
      - kind: unit
        ref: "tests/test_review_profiles.py#test_general_profile_drops_gates_c_d_e_unconditionally_even_for_allowlisted_class"
        status: pass
      - kind: unit
        ref: "tests/test_review_profiles.py#test_general_profile_bypasses_gate_a_and_b_for_an_allowlisted_class"
        status: pass
    human_judgment: false
  - id: D4
    description: "An unknown profile name raises ValueError instead of defaulting"
    requirement: REV-01
    verification:
      - kind: unit
        ref: "tests/test_review_profiles.py#test_apply_profile_raises_on_unknown_profile"
        status: pass
    human_judgment: false
  - id: D5
    description: "models.py and evidence.py remain untouched across the plan's commits"
    requirement: REV-01
    verification:
      - kind: other
        ref: "git diff --stat 245d9e7~1 HEAD -- .../models.py .../evidence.py (empty output)"
        status: pass
    human_judgment: false

duration: 40min
completed: 2026-08-18
status: complete
---

# Phase 03 Plan 04: Review Profiles and General-Defect Class Summary

**`review_findings.apply_profile` adds a `general` review profile that bypasses gates A/B for five allowlisted defect classes, proven a strict superset of the unchanged `security` profile by a committed dual-run baseline fixture.**

## Performance

- **Duration:** 40 min
- **Tasks:** 3 (1 checkpoint:decision resolved in a prior segment, 2 auto/tdd)
- **Files modified:** 14

## Accomplishments

- New `review_findings.py` module (160 lines): `GatedFinding`/`ReviewFinding` dataclasses, `PROFILES`, `GENERAL_DEFECT_CLASSES` (5-member frozenset), `REVIEW_DISPOSITIONS`, `EXCLUSION_BLOCK_BY_PROFILE`, `classify()`, and `apply_profile()` — modeled on `evidence.py`'s frozenset-plus-predicate shape, zero I/O, zero state.
- `apply_profile` reproduces the security profile's gate ladder (A-E) byte-for-byte and relaxes gates A/B under `general` only for a finding whose rule-doc class is in the five-member allowlist (null-dereference, thread-safety, resource-leak, error-swallowing, injection); gates C, D, E drop unconditionally under both profiles.
- `cli.py`'s `run_review` wires `--profile` through `apply_profile` between the position gate and the report write; `report.py`'s `write_report`/`write_review_ledger` gained a `review_findings` parameter and a `review_findings` ledger key recording each surviving record's `profile` and `defect_class`.
- `GENERAL_PROFILE_EXCLUSION_RULES` added to `prompt-constants.md` beside the untouched `EXCLUSION_RULES` block; `SKILL.md` selects the block by `--profile` value.
- 14-test `test_review_profiles.py` suite, including a D-10 dual-run pair (`test_dual_run_security_profile_matches_committed_baseline_no_regression`, `test_dual_run_general_profile_is_a_strict_superset_of_the_security_baseline`) against a committed `review_profiles_security_baseline.json` fixture.

## Task Commits

Each task was committed atomically, with a TDD RED->GREEN cycle for the behavior-adding task:

1. **Task 1: checkpoint:decision (option-a selected)** - resolved in a prior segment, no separate commit (decision recorded in this plan's frontmatter/action text).
2. **Task 2+3: Profile branch, general-defect allowlist, dual-run proof** - TDD RED `245d9e7` (`test(03-04): add failing tests for review profile gating`) -> GREEN `8a982ce` (`feat(03-04): add review profile gating (REV-01)`).
3. **Fix: baseline commit hash in docstring** - `e45d76a` (`fix(03-04): correct baseline commit hash in docstring`) — corrected a placeholder hash left from drafting to the real commit (`245d9e7`) that first committed the baseline fixture.
4. **Fix: `-k dual_run` test naming** - `6235453` (`fix(03-04): name dual-run tests to match -k dual_run`) — the plan's acceptance criterion filters on `-k dual_run`; the two D-10 tests did not carry that substring.

**Plan metadata:** pending (this commit) — `docs(03-04): complete review profiles plan`

_TDD Task 2/3 combined into one RED/GREEN pair since both were driven by the same test file and delivered together per the plan's task-2 action block ("Write the tests first" covering both tasks' `<behavior>` lists)._

## Files Created/Modified

- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_findings.py` - the profile gate module (new)
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_profiles.py` - 14 tests, including the D-10 dual-run pair (new)
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/fixtures/review_profiles_security_baseline.json` - committed expected-output baseline (new)
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py` - `run_review` threads `--profile` through `apply_profile`
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py` - `write_report`/`write_review_ledger` gained `review_findings` param + ledger key
- `plugins/sec-overlay/skills/sec-overlay/references/prompt-constants.md` - added `GENERAL_PROFILE_EXCLUSION_RULES` block, existing block untouched
- `plugins/sec-overlay/skills/sec-overlay/SKILL.md` - documents the `review` verb and `--profile` selection
- `plugins/sec-overlay/skills/sec-overlay/README.md`, `references/README.md`, `helpers/README.md`, `helpers/sec_overlay/README.md`, `helpers/tests/README.md` - folder-README updates (doc-update-guard requirement)

## Decisions Made

- Checkpoint decision (Task 1, resolved in a prior segment): option-a, a new `review_findings.py` module wrapping findings in `ReviewFinding`, keeping `models.py`/`evidence.py` frozen per D-11.
- `apply_profile` returns a 2-tuple, deliberately diverging from `review_position_gate`'s 3-tuple — profile gating over an already-positioned finding can never produce a decline; documented in the module docstring so a future reader does not "fix" the shape back to three elements.
- Security-profile baseline captured as a committed JSON fixture rather than recomputed inline, so a future regression to `apply_profile` fails the comparison instead of silently moving the baseline.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Placeholder commit hash left in docstring**
- **Found during:** post-GREEN-commit verification pass
- **Issue:** `test_dual_run_security_profile_matches_committed_baseline_no_regression`'s docstring cited `15cb180` (an earlier, unrelated commit) as the baseline's provenance commit, a drafting placeholder never corrected.
- **Fix:** Updated the docstring to cite `245d9e7`, the actual commit that first committed `review_profiles_security_baseline.json`.
- **Files modified:** `tests/test_review_profiles.py`, plus mechanical `tests/README.md`/`CHANGELOG.md`/`plugin.json` doc-update-guard companions.
- **Verification:** `uv run pytest tests/test_review_profiles.py -q` — 14 passed.
- **Committed in:** `e45d76a`

**2. [Rule 1 - Bug] Dual-run tests did not match the plan's `-k dual_run` acceptance criterion**
- **Found during:** running the plan's literal acceptance-criteria commands as a self-check
- **Issue:** `uv run pytest tests/test_review_profiles.py -k dual_run -q` deselected all 14 tests — neither D-10 test's name contained the substring `dual_run`, failing an explicit plan acceptance criterion ("collects at least 1 test and exits 0").
- **Fix:** Renamed the two tests to `test_dual_run_security_profile_matches_committed_baseline_no_regression` and `test_dual_run_general_profile_is_a_strict_superset_of_the_security_baseline`.
- **Files modified:** `tests/test_review_profiles.py`, plus mechanical `tests/README.md`/`CHANGELOG.md`/`plugin.json` doc-update-guard companions.
- **Verification:** `uv run pytest tests/test_review_profiles.py -k dual_run -q` — 2 passed; full suite unchanged (1110 passed, 2 known-environmental failures).
- **Committed in:** `6235453`

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bugs against the plan's own explicit acceptance criteria, discovered by running those criteria literally as a self-check).
**Impact on plan:** Both fixes are test-naming/documentation corrections with no production-code change. No scope creep.

## Issues Encountered

None beyond the two auto-fixed items above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `apply_profile`'s `ReviewFinding` wrapper and `REVIEW_DISPOSITIONS`/`UNCONFIRMED_DISPOSITION` are the exact surface plan 03-05 attaches the receipt-gate disposition ladder to.
- `EXCLUSION_BLOCK_BY_PROFILE` and the committed baseline fixture are reusable if 03-05 needs another profile-scoped regression proof.
- No blockers. `models.py`/`evidence.py` remain untouched; the Go-port mirror contract holds.

---
*Phase: 03-rule-matching-review-modes*
*Completed: 2026-08-18*
