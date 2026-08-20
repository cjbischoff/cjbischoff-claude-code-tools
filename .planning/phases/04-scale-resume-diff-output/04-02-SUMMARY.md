---
phase: 04-scale-resume-diff-output
plan: 02
subsystem: infra
tags: [python, cli, argparse, threadpoolexecutor, coverage-manifest, sec-overlay]

requires:
  - phase: 04-scale-resume-diff-output plan 01
    provides: "bundle.py's group_bundles() ReviewUnit grouping and the CoverageManifest fail/seal API this plan dispatches and fails against"
provides:
  - "Three validated CLI flags on `review`: --concurrency (default 8, 1-128), --timeout (default 600s, 1-3600), --max-git-procs (default 16, 1-128), each rejecting out-of-range input with a named-flag, named-range, non-zero-exit error instead of clamping"
  - "The two per-file git-fetch loops in run_review run through a bounded ThreadPoolExecutor sized by --max-git-procs, consumed in submission order so the manifest's file order matches the prior serial order under any completion order"
  - "A per-ReviewUnit timeout (--timeout, integer seconds, no arithmetic) that fails every member file of a unit whose fetch work exceeds it, so seal() returns partial (exit 3) instead of raising on unfinished entries"
  - "SKILL.md's fan-out guidance now names --concurrency as the enforced live-subagent dispatch ceiling, since the Python core never spawns an agent itself"
affects: [04-03]

actuals:
  tokens: 9637
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Bounded validation helper (_bounded_int) shared by all three flags, called before any work begins, that rejects rather than clamps out-of-range input"
    - "Two independent ceiling constants (MAX_WORKERS=128 for counts, MAX_TIMEOUT_SECONDS=3600 for seconds) instead of one shared ceiling, since a single ceiling sized for worker counts would reject the timeout default's own order of magnitude"
    - "Per-unit dispatch via ex.submit() + zip(units, futures) + future.result(timeout=...), not .map() and never as_completed() - each future needs its own per-unit timeout, and results must stay in submission order for a byte-identical manifest"
    - "TimeoutError(TIMEOUT_NOTE) reuses the existing str(exception)-as-note code path unchanged - a timeout is handled by the same isinstance(fetched, Exception) branch as an ordinary per-file fetch failure, no special-casing needed"

key-files:
  created: []
  modified:
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_cli.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_rule_glob.py
    - plugins/sec-overlay/skills/sec-overlay/SKILL.md
    - plugins/sec-overlay/skills/sec-overlay/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md
    - plugins/sec-overlay/.claude-plugin/plugin.json
    - plugins/sec-overlay/CHANGELOG.md

key-decisions:
  - "Chose the three-file locale-sibling grouping rule in bundle.py (en.json/fr.json/de.json, same-directory locale rule, uncapped member count) over the two-file impl/test pairing rule (capped at 2 members) to satisfy the plan's explicit three-file-timed-out-unit acceptance criterion"
  - "Removed an explicit dict[str, object] type annotation on fetch_by_path because it broke ty's narrowing of the isinstance(fetched, Exception) else-branch to a tuple; let ty infer the type from usage instead"
  - "Kept the ThreadPoolExecutor context manager open across both the submit loop and the result-collection loop, since closing it after only submitting would make __exit__'s shutdown(wait=True) block until every future finishes anyway, silently defeating the timeout's early-return purpose"

patterns-established:
  - "Validate-before-work: all three bound flags are checked by _bounded_int before run_review does any fetching, so an invalid bound costs nothing"
  - "A timeout is a coverage failure; a review-source skip or reflection skip stays a non-coverage event untouched by this change"

requirements-completed: [SCALE-02]

coverage:
  - id: D1
    description: "review subcommand accepts --concurrency, --timeout, --max-git-procs with defaults 8/600/16, rejecting 0, negative, and ceiling-plus-one with a named-flag/named-range non-zero exit"
    requirement: SCALE-02
    verification:
      - kind: unit
        ref: "tests/test_cli.py -k concurrency or timeout or max_git_procs"
        status: pass
    human_judgment: false
  - id: D2
    description: "The two per-file git loops run through a bounded thread pool consumed in submission order, identical manifest file order under an out-of-order runner"
    requirement: SCALE-02
    verification:
      - kind: unit
        ref: "tests/test_cli.py::test_review_manifest_entries_preserve_file_order_despite_uneven_fetch_delay"
        status: pass
    human_judgment: false
  - id: D3
    description: "A timed-out ReviewUnit fails every member file with a timeout note; seal() returns partial (exit 3) instead of raising"
    requirement: SCALE-02
    verification:
      - kind: unit
        ref: "tests/test_cli.py::test_review_unit_timeout_fails_every_member_with_timeout_note"
        status: pass
      - kind: unit
        ref: "tests/test_cli.py::test_review_unit_within_timeout_finishes_normally"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-08-20
status: complete
---

# Phase 04 Plan 02: Bounded review CLI flags, pooled git fetch, per-unit timeout Summary

**Three validated `--concurrency`/`--timeout`/`--max-git-procs` flags on `review`, a `ThreadPoolExecutor`-bounded git-fetch loop that preserves serial file order, and a per-`ReviewUnit` timeout that fails every member file so the coverage manifest seals `"partial"` instead of hanging or raising.**

## Performance

- **Duration:** 55 min
- **Started:** 2026-08-20T10:37:00Z (approx, prior-session start)
- **Completed:** 2026-08-20T11:32:07Z
- **Tasks:** 3
- **Files modified:** 10

## Accomplishments

- `review` now rejects an out-of-range `--concurrency`, `--timeout`, or `--max-git-procs` with a message naming the flag and its accepted range, and never silently clamps (`grep -c 'max(1, min(' sec_overlay/cli.py` is 0).
- Both per-file git-fetch loops run through a `ThreadPoolExecutor` sized by `--max-git-procs`, read back in submission order, so the manifest's file order is byte-identical to the pre-pool serial order regardless of completion order.
- A `ReviewUnit` whose fetch work exceeds `--timeout` fails every one of its member files via the unchanged `CoverageManifest.fail()` API, so `seal()` returns `"partial"` (exit 3) instead of raising on unfinished entries.
- `SKILL.md` now names `--concurrency` as the enforced dispatch ceiling beside its existing fan-out guidance, closing the gap between a validated flag and its one real enforcement point (the dispatching agent).

## Task Commits

1. **Task 1: Three bounded flags on the review subcommand** - `a2fa62d` (feat)
2. **Task 2: Bound the two git loops with an order-preserving worker pool** - `0e80705` (feat)
3. **Task 3: A timed-out unit fails every member file so the seal turns partial** - `80dd119` (feat)

**Plan metadata:** pending (this commit)

_Note: all three tasks are `tdd="true"`; each commit's diff contains both the failing test and its minimal implementation together, since the plan's TDD convention here is RED+GREEN within one task commit, not split test()/feat() commits._

## Files Created/Modified

- `sec_overlay/cli.py` - three bounded flags + `_bounded_int`, per-unit `ThreadPoolExecutor` dispatch for both git-fetch loops, `_fetch_review_unit_files` helper, `TIMEOUT_NOTE` constant and per-unit timeout handling
- `tests/test_cli.py` - flag-boundary tests (1/ceiling/0/negative/ceiling+1 per flag), out-of-order-runner manifest-order test, timeout tests (three-file timed-out unit, within-timeout unit)
- `tests/test_rule_glob.py` - updated `fake_run_review` stub signature to match `run_review`'s new keyword-only parameters (Rule 1 fix, see Deviations)
- `SKILL.md` - records `--concurrency` as the enforced live-subagent dispatch ceiling beside existing fan-out guidance
- `skills/sec-overlay/README.md`, `helpers/README.md`, `sec_overlay/README.md`, `tests/README.md` - folder-README updates required by the repo's `doc-update-guard` hook, describing the new flags, pooling, and timeout design
- `.claude-plugin/plugin.json` - `1.65.0` → `1.66.0` (feat = minor bump)
- `CHANGELOG.md` - three `feat` entries under `1.66.0`

## Decisions Made

- Used the locale-sibling grouping rule (uncapped member count) rather than the impl/test pairing rule (capped at 2) to build a genuine three-file `ReviewUnit` for the timeout test, since the plan's acceptance criteria explicitly required a three-file case.
- Removed an explicit `dict[str, object]` annotation on `fetch_by_path` after it broke `ty`'s exception-branch narrowing; let `ty` infer the type instead.
- Reused `TimeoutError(TIMEOUT_NOTE)` through the existing `str(exception)`-as-note code path so no special-casing was needed for the timeout branch versus an ordinary per-file fetch failure.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `ty check` type-narrowing regression from an explicit dict annotation**
- **Found during:** Task 3
- **Issue:** Annotating `fetch_by_path: dict[str, object] = {}` broke `ty`'s narrowing of the `isinstance(fetched, Exception)` else-branch to a tuple, producing `error[not-iterable]`.
- **Fix:** Removed the explicit annotation; `ty` infers the correct type from usage.
- **Files modified:** `sec_overlay/cli.py`
- **Verification:** `uv run ty check` → "All checks passed!"
- **Committed in:** `80dd119` (Task 3 commit)

**2. [Rule 1 - Bug] `test_rule_glob.py` regression from Task 1's new `run_review` kwargs**
- **Found during:** Task 3, running the full test suite as a good-practice check beyond task-scoped `<verify>` blocks
- **Issue:** `test_review_cli_parses_rule_and_exclude_and_reaches_run_review`'s monkeypatched `fake_run_review` stub didn't accept the `concurrency`/`timeout`/`max_git_procs` keyword arguments Task 1 added to the real `run_review`, causing `TypeError: fake_run_review() got an unexpected keyword argument 'concurrency'`.
- **Fix:** Added matching keyword arguments with the same defaults to the stub's signature.
- **Files modified:** `tests/test_rule_glob.py`
- **Verification:** `uv run pytest -q` → only the two known baseline environmental failures remain.
- **Committed in:** `80dd119` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 - bug fixes)
**Impact on plan:** Both fixes were required for correctness (`ty check` clean, full suite green beyond the two known baseline failures). No scope creep - neither touched a prohibited file.

## Issues Encountered

- The `doc-update-guard` prek hook rejected the first commit attempt for missing `skills/sec-overlay/README.md` (the folder README for `SKILL.md`'s own directory, distinct from `helpers/README.md`); resolved by adding a one-line parenthetical to that README and staging it.
- An amend to fix the timeout test's file count (2→3 files) was rejected by the same hook because `CHANGELOG.md` showed no diff relative to the pre-amend `HEAD` even though its 1.66.0 entry already existed; resolved by adding a genuinely new sentence to the changelog entry describing the three-member test, giving the amend a real diff to satisfy the hook.
- Neither issue required a plan deviation rule beyond documentation - both are repo-governance mechanics, not code defects.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- SCALE-02 is fully implemented and tested: bounded flags, pooled git fetch, per-unit timeout with honest partial sealing.
- `review_coverage.py`, `models.py`, and `evidence.py` remain untouched, as required by this plan and by 04-03's dependency on an unmodified manifest API.
- 04-03 (resume identity) can build directly on this plan's `CoverageManifest.fail()`-based timeout path without any manifest schema change from this plan.

## Self-Check: PASSED

- `sec_overlay/cli.py`, `tests/test_cli.py`, `tests/test_rule_glob.py`, `SKILL.md`, all four folder READMEs, `plugin.json`, `CHANGELOG.md` - all present on disk at the paths listed above.
- `a2fa62d`, `0e80705`, `80dd119` - all found in `git log --oneline --all`.
- `uv run pytest -q` → 1229 passed, 2 failed (both pre-existing baseline: `test_bench.py::test_seed_corpus_is_valid`, `test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd`).
- `uv run ruff check sec_overlay/ bench/ tests/` → "All checks passed!"
- `uv run ty check` → "All checks passed!"
- `uv run python -m sec_overlay.cli review --help` → lists `--concurrency`, `--timeout` (default 600), `--max-git-procs` with the documented defaults.
- `git diff HEAD -- sec_overlay/review_coverage.py` → empty.

---
*Phase: 04-scale-resume-diff-output*
*Completed: 2026-08-20*
