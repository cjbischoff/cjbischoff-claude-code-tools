---
phase: 04-scale-resume-diff-output
plan: 04
subsystem: testing
tags: [python, argparse, threadpoolexecutor, subprocess, tdd, sec-overlay]

# Dependency graph
requires:
  - phase: 04-scale-resume-diff-output
    provides: "04-01/04-02/04-03's coverage manifest, resume-identity gate, and bounded concurrency in cli.py"
provides:
  - "OUT-01: embedded coverage_manifest.seal in review_comments.json always matches the on-disk manifest's seal, for complete and partial runs"
  - "SCALE-03: --model is a real argparse flag on the review subcommand, forwarded to run_review and enforced on resume via check_resume_identity"
  - "SCALE-02: run_review returns bounded by --timeout on a hung unit fetch; the abandoned worker stops at its own deadline and the underlying git subprocess is killed rather than orphaned"
affects: [sec-overlay-review-cli, sec-overlay-verification]

actuals:
  tokens: 8417
  tasks: 3
  commits: 6

tech-stack:
  added: []
  patterns:
    - "Seal-then-write: compute the coverage manifest's seal exactly once, then write every artifact that embeds it from that single sealed value — never write an artifact from a manifest that could still be re-sealed."
    - "Executor lifetime vs. process lifetime are separate problems: ex.shutdown(wait=False) frees the calling thread from an abandoned worker, but the interpreter's own atexit hook still joins that worker, so the actual kill has to happen at the subprocess level (partial(subprocess.run, timeout=timeout))."
    - "Compute a worker's own deadline at the worker's entry point, not at submit time — a queued unit's wait in a bounded pool would otherwise silently consume its own execution budget."

key-files:
  created: []
  modified:
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_cli.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_live.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_tracer.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_rule_glob.py
    - plugins/sec-overlay/skills/sec-overlay/SKILL.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md
    - plugins/sec-overlay/CHANGELOG.md
    - plugins/sec-overlay/.claude-plugin/plugin.json

key-decisions:
  - "Zero-reviewable early-return path keeps writing the comments file with an unsealed manifest.to_dict() rather than sealing an empty manifest, because CoverageManifest.seal() raises by design on an empty manifest (decision T-02-05)."
  - "Production runner default becomes partial(subprocess.run, timeout=timeout) at the single r = runner or ... assignment point, so every git call in run_review (RepoMemory, resolve_ref_sha, _bounded_map, changed_file_records, binary_paths, unit fetches) inherits the kill deadline with no per-call-site change."
  - "Per-call subprocess timeout is set equal to the declared --timeout (not a fraction of it), so the consuming thread's future.result(timeout=timeout) clock — which starts earlier, at submit time — always expires first and TIMEOUT_NOTE stays deterministic."

patterns-established:
  - "Fake-runner **kwargs convention: any test double monkeypatched onto subprocess.run, or injected as runner=, must accept and ignore a timeout keyword, because the production default is now partial(subprocess.run, timeout=timeout)."

requirements-completed: [OUT-01, SCALE-02, SCALE-03]

coverage:
  - id: D1
    description: "OUT-01: review_comments.json's embedded coverage_manifest.seal equals the on-disk manifest's seal for both a complete and a partial run"
    requirement: "OUT-01"
    verification:
      - kind: unit
        ref: "tests/test_cli.py::test_review_comments_embedded_manifest_seal_matches_on_disk_after_complete_run"
        status: pass
      - kind: unit
        ref: "tests/test_cli.py::test_review_comments_embedded_manifest_seal_is_partial_after_partial_run"
        status: pass
    human_judgment: false
  - id: D2
    description: "SCALE-03: --model is accepted by argparse, forwarded to run_review, and a resumed run with a changed --model exits 2 through main()"
    requirement: "SCALE-03"
    verification:
      - kind: unit
        ref: "tests/test_cli.py::test_review_accepts_model_flag_and_forwards_it_to_run_review"
        status: pass
      - kind: unit
        ref: "tests/test_cli.py::test_review_resume_with_changed_model_exits_2_via_main_entrypoint"
        status: pass
    human_judgment: false
  - id: D3
    description: "SCALE-02: run_review returns bounded by --timeout on a hung unit fetch, the abandoned worker stops at its deadline, and the underlying git subprocess is killed"
    requirement: "SCALE-02"
    verification:
      - kind: unit
        ref: "tests/test_cli.py::test_review_returns_before_hung_unit_fetch_completes"
        status: pass
      - kind: unit
        ref: "tests/test_cli.py::test_review_abandoned_unit_fetch_stops_at_the_unit_deadline"
        status: pass
      - kind: unit
        ref: "tests/test_cli.py::test_review_production_git_calls_carry_subprocess_timeout"
        status: pass
    human_judgment: false

duration: 26min
completed: 2026-08-20
status: complete
---

# Phase 04 Plan 04: Gap Closure (OUT-01, SCALE-03, SCALE-02) Summary

**Seals the coverage manifest before embedding it, gives `--model` a real CLI surface, and bounds `run_review`'s wall clock on a hung git fetch via executor `shutdown(wait=False)` plus a per-call `subprocess.run(timeout=...)` kill.**

## Performance

- **Duration:** 26 min
- **Started:** 2026-08-20T19:58:37Z
- **Completed:** 2026-08-20T20:24:30Z
- **Tasks:** 3
- **Files modified:** 10

## Accomplishments
- `review_comments.json`'s embedded `coverage_manifest.seal` now always matches the on-disk manifest's seal, for both a complete and a partial run (OUT-01).
- `cli review --model <id>` is a real argparse flag, forwarded to `run_review`, and a resumed run with a changed model exits 2 through `main()` (SCALE-03).
- A hung review-unit git fetch no longer holds `run_review` (or the CLI process) past `--timeout`: the executor stops waiting on the abandoned worker, the worker itself stops fetching remaining members past its own deadline, and the underlying git child is killed via a per-call `subprocess.run(timeout=...)` (SCALE-02).

## Task Commits

Each task was executed as a full TDD red/green cycle:

1. **Task 1: Seal the coverage manifest before embedding it (OUT-01)**
   - `70aaf9d` (test) — failing embedded-seal tests
   - `728ff73` (fix) — reorder `run_review`'s output block so `manifest.seal()` runs before `write_review_comments`
2. **Task 2: Give `--model` a CLI surface (SCALE-03)**
   - `36b08d0` (test) — failing `--model` CLI surface tests
   - `7b72c75` (fix) — wire `--model` through argparse and `main()`
3. **Task 3: Bound review wall-clock time on a hung unit fetch (SCALE-02)**
   - `80074fd` (test) — failing hung-fetch timeout tests
   - `e6dcddc` (fix) — explicit executor `try`/`finally` `shutdown(wait=False)` + subprocess-level kill deadline + worker-side unit deadline

**Plan metadata:** pending (this commit)

_All three tasks used the RED (failing test, committed) → GREEN (fix, committed) cycle; no REFACTOR commit was needed for any task._

## Files Created/Modified
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py` - reordered seal-then-write, `--model` argparse + forwarding, executor lifetime fix, subprocess-level timeout, worker deadline in `_fetch_review_unit_files`
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_cli.py` - 7 new tests across the three gaps; `_make_review_runner` gained `**kwargs`
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_live.py` - `_fake_run_for`/`failing_diff` gained `**kwargs`
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_tracer.py` - `_fake_run`/`_make_fake_run` gained `**kwargs`
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_rule_glob.py` - deviation fix: `fake_run_review` spy gained `model=None` (see Deviations)
- `plugins/sec-overlay/skills/sec-overlay/SKILL.md` - documents `--model` in the review invocation block and the identical-value resume convention
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md` - documents all three fixes
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md` - documents the 7 new tests, the `**kwargs` fake-runner convention, and the test_rule_glob.py deviation
- `plugins/sec-overlay/CHANGELOG.md` - three `### Fixed` entries (1.68.4, 1.68.5, 1.68.6... see plugin.json below for exact sequence)
- `plugins/sec-overlay/.claude-plugin/plugin.json` - patch-bumped once per fix commit

## Decisions Made
- Zero-reviewable early return keeps writing the comments file from an unsealed `manifest.to_dict()` rather than sealing an empty manifest — `CoverageManifest.seal()` raises by design on an empty manifest (T-02-05).
- Production runner default changed to `partial(subprocess.run, timeout=timeout)` at the single `r = runner or ...` assignment, so every git call `run_review` makes inherits the kill deadline through the shared `r` variable with no other call-site change (including `_bounded_map`, which needed zero code change).
- Per-call subprocess timeout equals the declared `--timeout` (not a fraction of it) so the future-level timeout always fires first and `TIMEOUT_NOTE` bookkeeping stays deterministic.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed `test_rule_glob.py` regression from Task 2's `--model` wiring**
- **Found during:** Task 3 (full-suite verification step)
- **Issue:** `test_review_cli_parses_rule_and_exclude_and_reaches_run_review`'s `fake_run_review` spy had no `model` parameter. Task 2 added `model=args.model` to `main()`'s `run_review(...)` call, but `test_rule_glob.py` wasn't in Task 2's `<files>`/regression scope, so the spy raised `TypeError: fake_run_review() got an unexpected keyword argument 'model'` once Task 3's fix forced a full-suite run.
- **Fix:** Added `model=None` to `fake_run_review`'s keyword-only parameters to match `run_review`'s real signature.
- **Files modified:** `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_rule_glob.py`
- **Verification:** Full suite re-run after the fix: `2 failed, 1249 passed` — matches the recorded environmental baseline exactly.
- **Committed in:** `e6dcddc` (Task 3 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary to satisfy the plan's own acceptance criterion ("Full-suite run matches the recorded baseline"). No scope creep — the fix is a one-line test-double signature correction with no production code touched.

## Issues Encountered
None beyond the deviation above. All three tasks' RED tests failed exactly as designed against the pre-fix code (reproductions matched the plan's recorded evidence: 4.20s timeout overrun, `unrecognized arguments: --model`, null embedded seal), and all GREEN fixes passed on the first implementation attempt.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All three failed truths from `04-VERIFICATION.md` (OUT-01, SCALE-02, SCALE-03) are now observably true, each proved by a test that fails against the pre-fix code.
- Full suite: `2 failed, 1249 passed` — matches the recorded baseline; the 2 failures are the pre-existing environmental ones (gitignored bench corpus, excluded semgrep submodule).
- `WR-01`, `WR-02`, `IN-01` remain open by design (out of scope for this plan; `WR-03` was closed incidentally by Task 3's per-call subprocess timeout).
- No blockers for phase completion; ready for re-verification against `04-VERIFICATION.md`.

---
*Phase: 04-scale-resume-diff-output*
*Completed: 2026-08-20*

## Self-Check: PASSED

- FOUND: `.planning/phases/04-scale-resume-diff-output/04-04-SUMMARY.md`
- FOUND: `70aaf9d`, `728ff73`, `36b08d0`, `7b72c75`, `80074fd`, `e6dcddc`
