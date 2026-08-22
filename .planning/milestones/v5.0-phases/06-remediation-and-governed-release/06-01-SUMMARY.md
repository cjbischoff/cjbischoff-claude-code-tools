---
phase: 06-remediation-and-governed-release
plan: 01
subsystem: sec-overlay
tags: [cli, argparse, workspace-resolution, tdd, ci-governance, coderabbit]

requires:
  - phase: 05-end-to-end-verification-audit-review
    provides: "WR-01 defect entry in 05-DEFECTS.md; the resume-identity guard (SCALE-03, Phase 4) whose contract must not weaken"
provides:
  - "review --root guard: exits 2 (not a raw filesystem exception) for a missing, empty, or non-directory --root"
  - "review --workspace flag, resolving through load_paths(workspace=...) exactly like audit's flag, with sidecar fallback preserved"
  - "empirical answer: CodeRabbit does NOT auto-review a PR whose base is a non-default branch; @coderabbitai review must be triggered manually on every PR in this phase targeting docs/milestone-v5-diff-review"
  - "proven tracer for the phase's full governance rail: RED/GREEN commit pair, per-commit version bump, per-commit CHANGELOG entry, folder README co-update, branch, PR, merge"
affects: [06-02, 06-03, 06-04, 06-05]

actuals:
  tokens: 4465
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "resolve-or-fallback workspace resolution: `if workspace: load_paths(workspace=workspace) else: RepoMemory.for_target(...)` — same shape `audit` already used, reused verbatim rather than adding a second resolver"
    - "single guard predicate for multi-shaped bad input: `if not root or not Path(root).is_dir():` covers missing/empty/file-as-root in one branch instead of three"

key-files:
  created: []
  modified:
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_live.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_rule_glob.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md
    - plugins/sec-overlay/.claude-plugin/plugin.json
    - plugins/sec-overlay/CHANGELOG.md

key-decisions:
  - "Pushed docs/milestone-v5-diff-review to origin before opening the PR — the branch existed only locally and gh pr create requires both ends to exist remotely; no new commits, just publishing the existing branch."
  - "CodeRabbit's automatic review is restricted to the default branch (main) by .coderabbit.yaml; every PR in this phase against docs/milestone-v5-diff-review needs an explicit `@coderabbitai review` comment to get a walkthrough."
  - "Kept the two CodeRabbit test-strengthening nitpicks (assert --workspace CLI forwarding; assert the root guard fires before any git call) out of scope and logged them to deferred-items.md rather than expanding this plan, per user's approved option."

patterns-established:
  - "One guard predicate per multi-case validation, not one branch per case (root guard covers 3 failure shapes with a single `if`)."
  - "TDD RED/GREEN as two separate atomic commits, each independently carrying its own governance metadata (version bump + CHANGELOG entry + folder README), never batched into the following commit."

requirements-completed: [REL-01, REL-02]

coverage:
  - id: D1
    description: "review --root exits 2 with a one-line error message (no traceback) for a missing, empty, or file-as-root path, checked before any git subprocess runs"
    requirement: REL-01
    verification:
      - kind: unit
        ref: "tests/test_review_live.py#test_run_review_rejects_a_nonexistent_root_with_exit_2"
        status: pass
      - kind: unit
        ref: "tests/test_review_live.py#test_run_review_rejects_an_empty_root_with_exit_2"
        status: pass
      - kind: unit
        ref: "tests/test_review_live.py#test_run_review_rejects_a_file_as_root_with_exit_2"
        status: pass
    human_judgment: false
  - id: D2
    description: "review --workspace resolves through load_paths like audit's flag; omitting it still resolves the per-repo sidecar"
    requirement: REL-01
    verification:
      - kind: unit
        ref: "tests/test_review_live.py#test_run_review_uses_the_workspace_override_when_supplied"
        status: pass
      - kind: unit
        ref: "tests/test_review_live.py#test_run_review_falls_back_to_the_repo_sidecar_when_workspace_is_absent"
        status: pass
    human_judgment: false
  - id: D3
    description: "--workspace override routes around the SCALE-03 resume guard by giving a second profile its own workspace, without weakening the guard itself"
    requirement: REL-01
    verification:
      - kind: unit
        ref: "tests/test_review_live.py#test_review_workspace_override_permits_a_second_profile_without_weakening_the_resume_guard"
        status: pass
    human_judgment: false
  - id: D4
    description: "four governed commits, each with its own plugin.json bump and CHANGELOG entry, version strictly increasing 1.68.7 to 1.69.0 with no reuse or skip"
    requirement: REL-02
    verification:
      - kind: other
        ref: "git log --oneline docs/milestone-v5-diff-review..562b313 (4 task commits); git show --stat on each lists plugin.json and CHANGELOG.md"
        status: pass
    human_judgment: false
  - id: D5
    description: "PR opened against docs/milestone-v5-diff-review (not main), CodeRabbit outcome recorded honestly, merged only on explicit human approval"
    requirement: REL-02
    verification: []
    human_judgment: true
    rationale: "Checkpoint gate is blocking-human by design (Task 3, gate=blocking) — merge requires an explicit human decision, not an automated pass/fail."

duration: unavailable (session resumed from a compacted transcript with no captured PLAN_START_TIME)
completed: 2026-08-21
status: complete
---

# Phase 06 Plan 01: WR-01 root guard + review --workspace override (D-03) Summary

**`review --root` now exits 2 for a missing/empty/non-directory path instead of raising, and `review --workspace` resolves through `load_paths` exactly like `audit`'s flag — both shipped as the phase's tracer through the full governance rail (RED/GREEN commits, per-commit version bump, CHANGELOG, README, PR, CodeRabbit, merge).**

## Performance

- **Duration:** unavailable — session spanned a context compaction with no captured start timestamp
- **Tasks:** 3 (Task 1 tracer/TDD, Task 2 auto/TDD, Task 3 checkpoint)
- **Files modified:** 7 (cli.py, two READMEs, two test files, plugin.json, CHANGELOG.md)

## Accomplishments

- WR-01 fixed: `run_review` guards `--root` with a single `if not root or not Path(root).is_dir():` predicate ahead of any workspace or git subprocess call, exiting 2 with `error: --root must be an existing directory (got ...)`.
- `review --workspace` added, mirroring `audit`'s existing flag: an explicit override resolves via `load_paths(workspace=...)`; omitting it falls back to the pre-existing `RepoMemory.for_target` sidecar. The SCALE-03 resume-identity guard is provably unaffected — it reads the resolved workspace's manifest regardless of resolution path.
- Full governance rail proven end to end for the phase: branch off `docs/milestone-v5-diff-review`, four atomic commits each carrying its own `plugin.json` bump and `CHANGELOG.md` entry, PR against the milestone branch, CodeRabbit review, human-approved merge.
- **Empirical answer for plans 02-04:** CodeRabbit's automatic review only fires on the repo's default branch (`main`) per `.coderabbit.yaml` (`Auto reviews are disabled on base/target branches other than the default branch`). A PR against `docs/milestone-v5-diff-review` gets a "Review skipped" notice, not a walkthrough, until someone comments `@coderabbitai review`. Every PR plans 02-04 open against this same base branch needs that manual trigger — it will not happen on its own.

## Task Commits

1. **Task 1 (tracer/TDD): WR-01 root guard**
   - RED: `dbac919` (`test(06-01): pin WR-01 --root guard, 3 failing tests`) — plugin.json 1.68.7 → 1.68.8
   - GREEN: `dfa112c` (`fix(06-01): reject a bad --root with exit 2 (WR-01)`) — plugin.json 1.68.8 → 1.68.9
2. **Task 2 (auto/TDD): `review --workspace` (D-03)**
   - RED: `9da359c` (`test(06-01): pin review --workspace override (D-03)`) — plugin.json 1.68.9 → 1.68.10
   - GREEN: `3354f44` (`feat(06-01): add review --workspace override (D-03)`) — plugin.json 1.68.10 → 1.69.0
3. **Task 3 (checkpoint:human-verify, gate=blocking):** PR #23, merged on explicit human approval — `562b313` (merge commit)

**Plan metadata:** commit pending (this SUMMARY + STATE/ROADMAP/REQUIREMENTS updates)

_Note: both TDD tasks used exactly two commits each — RED then GREEN, no REFACTOR needed._

## Files Created/Modified

- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py` — root-existence guard in `run_review`; `workspace` keyword-only parameter; `--workspace` on the `review` subparser; dispatch threads `args.workspace` through
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md` — narrative paragraphs for both the WR-01 guard and the `--workspace` override
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_live.py` — 6 new tests (3 WR-01 cases, 3 `--workspace` cases); one pre-existing test updated to `mkdir()` its roots explicitly
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_rule_glob.py` — `fake_run_review` spy gained `workspace=None` to match the new keyword-only parameter
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md` — narrative entries documenting all 6 new tests and the spy fix
- `plugins/sec-overlay/.claude-plugin/plugin.json` — version 1.68.7 → 1.69.0 across four bumps
- `plugins/sec-overlay/CHANGELOG.md` — four new entries (1.68.8, 1.68.9, 1.68.10, 1.69.0)

## Decisions Made

- Pushed `docs/milestone-v5-diff-review` to `origin` before opening the PR (it existed only locally; no new commits, just publishing it) — required for `gh pr create` to resolve the base ref.
- Triggered CodeRabbit manually with `@coderabbitai review` rather than waiting indefinitely, once the automatic-review-skipped notice made clear it would never fire on its own for this base branch.
- Left the two CodeRabbit nitpicks (assert `--workspace` CLI forwarding in `test_rule_glob.py`; assert the WR-01 guard fires before any git call) unaddressed in this plan — logged to `deferred-items.md` per the user's approved merge-as-is option, since both are new test-strengthening ideas rather than defects in delivered behavior.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `Path("").is_dir()` normalizes to cwd and reports True**
- **Found during:** Task 1 GREEN implementation
- **Issue:** The naive guard `not Path(root).is_dir()` passed for an empty-string `root`, since `Path("")` normalizes to `Path(".")` (the CWD, which exists).
- **Fix:** Changed the guard to `if not root or not Path(root).is_dir():`, catching the empty string via its falsiness before constructing a `Path`.
- **Files modified:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py`
- **Verification:** `test_run_review_rejects_an_empty_root_with_exit_2` passes.
- **Committed in:** `dfa112c`

**2. [Rule 1 - Bug] WR-01 guard broke a pre-existing test's implicit auto-vivification assumption**
- **Found during:** Task 1 GREEN implementation, full-suite run
- **Issue:** `test_exit_codes_unchanged_invalid_ref_partial_seal_complete`'s `partial`/`complete` roots relied on `Workspace.ensure()`'s `mkdir(parents=True)` side effect to spring a nonexistent directory into existence — the new guard now rejects that directory before `Workspace.ensure()` ever runs.
- **Fix:** Updated the test to `mkdir()` `partial_root`/`complete_root` explicitly before calling `run_review`.
- **Files modified:** `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_live.py`
- **Verification:** Full `test_review_live.py tests/test_cli.py` suite passes, zero regressions.
- **Committed in:** `dfa112c`

**3. [Rule 1 - Bug] `test_rule_glob.py`'s `fake_run_review` spy didn't accept the new `workspace` kwarg**
- **Found during:** Task 2 GREEN implementation, full-suite run
- **Issue:** Once the `review` dispatch branch started passing `workspace=args.workspace`, `test_review_cli_parses_rule_and_exclude_and_reaches_run_review`'s local monkeypatched spy raised `TypeError: fake_run_review() got an unexpected keyword argument 'workspace'` — the same class of gap the tests README already documents for the prior `model=None` addition.
- **Fix:** Added `workspace=None` to the spy's signature.
- **Files modified:** `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_rule_glob.py`
- **Verification:** Full suite: `1257 passed, 1 deselected` (only the known environmental `test_bench.py` failure remains).
- **Committed in:** `3354f44`

**4. [Rule 3 - Blocking] `docs/milestone-v5-diff-review` did not exist on the remote**
- **Found during:** Task 3, opening the PR
- **Issue:** `gh pr create --base docs/milestone-v5-diff-review ...` failed with `Base ref must be a branch` / `No commits between` because the base branch was local-only.
- **Fix:** `git push -u origin docs/milestone-v5-diff-review` (publishing the existing branch, no new commits), then retried `gh pr create` successfully.
- **Files modified:** none (git ref publication only)
- **Verification:** PR #23 opened successfully against the pushed base.
- **Committed in:** n/a (ref push, not a code commit)

---

**Total deviations:** 4 auto-fixed (3 Rule 1 bugs, 1 Rule 3 blocking issue)
**Impact on plan:** All four were necessary consequences of the WR-01 guard and the `--workspace` wiring surfacing latent assumptions elsewhere in the suite, plus one environment-publication gap. No scope creep — nothing outside this plan's two defects was touched.

## Issues Encountered

**Honest discrepancy vs. the plan's predicted RED failure mode:** the plan's Task 1 `<action>` states "The first test must fail with a `FileNotFoundError` today" for the nonexistent-root case. The actual pre-fix behavior observed was different: a missing root was silently auto-vivified by `Workspace.ensure()`'s `mkdir(parents=True)` side effect (no crash at that point), and the run failed later with an unrelated "unresolvable ref" message. The `FileNotFoundError` the plan predicted was actually the failure mode for the **empty-string** root case (`subprocess.run(cwd="")`), not the missing-root case. All three tests still failed pre-fix (RED confirmed) and pass post-fix (GREEN confirmed) — only the specific exception-per-case mapping differed from the plan's prediction. Documented in `plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md`.

**CodeRabbit-on-milestone-base outcome (the flagged assumption this plan existed to resolve):** confirmed empirically — see Accomplishments above. Recorded here rather than assumed, per the plan's explicit instruction, for plans 02-04 to build on without re-litigating.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `--workspace` is now available on `review`, unblocking D-12's dispatched multi-profile run in Plan 05.
- The full governance rail (branch → per-commit bump/changelog/README → PR → CodeRabbit → merge) is proven working end to end; plans 02-04 can follow the identical pattern.
- Plans 02-04 must each manually trigger `@coderabbitai review` on their PRs against `docs/milestone-v5-diff-review` — automatic review will not fire on this base branch.
- Two CodeRabbit test-strengthening nitpicks are deferred (see `deferred-items.md`): asserting `--workspace` CLI forwarding in `test_rule_glob.py`, and asserting the WR-01 guard fires before any git call. Neither blocks correctness; either can be picked up by a later plan that touches those files.

---
*Phase: 06-remediation-and-governed-release*
*Completed: 2026-08-21*
