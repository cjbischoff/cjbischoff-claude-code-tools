---
phase: 05-end-to-end-verification-audit-review
plan: 01
subsystem: security-review-pipeline
tags: [sec-overlay, review-cli, diff-review, coverage-manifest, sidecar-workspace]

requires:
  - phase: 04-scale-resume-diff-output
    provides: bounded-concurrency review CLI with resume-identity pinning and diff-anchored output
provides:
  - Sanitized security- and general-profile review receipts proving `review` runs end to end on a real historical diff
  - A phase-level defect ledger (05-DEFECTS.md) seeded with five D-11 rows
  - A fixed cwd-scoping bug in `run_review`'s production git-subprocess runner
affects: [05-02, 05-03, 05-04, phase-6-planning]

actuals:
  tokens: 18948
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "SEC_OVERLAY_HOME override to run a second review profile against one target without disturbing the first profile's sealed sidecar workspace"

key-files:
  created:
    - .planning/phases/05-end-to-end-verification-audit-review/05-01-review-security-receipt.md
    - .planning/phases/05-end-to-end-verification-audit-review/05-01-review-general-receipt.md
    - .planning/phases/05-end-to-end-verification-audit-review/05-DEFECTS.md
  modified:
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_live.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md
    - plugins/sec-overlay/.claude-plugin/plugin.json
    - plugins/sec-overlay/CHANGELOG.md

key-decisions:
  - "Zero live findings from the CLI-only `review` run is a legitimate, by-design tracer outcome (D-13/D-15), not a gap requiring manual reviewer-subagent dispatch — AUD-06's completion criteria ground in CoverageManifest.seal() and apply_profile(), not genuine LLM findings."
  - "Task 2's general-profile run used a SEC_OVERLAY_HOME override to give it its own sidecar workspace, because `review`'s resume-identity guard (SCALE-03) rejects a second profile against a target's default sidecar and `review` has no `--workspace` flag (only `audit` does)."
  - "The security-kept ⊆ general-kept subset check passed vacuously (∅ ⊆ ∅); flagged as E-12 in 05-DEFECTS.md for Phase 6 to re-verify against a run with non-zero findings."

requirements-completed: [AUD-06]

coverage:
  - id: D1
    description: "A full `review` run (security profile) completes end to end on a real diff, with the coverage manifest sealed and both full SHAs recorded"
    requirement: "AUD-06"
    verification:
      - kind: manual_procedural
        ref: "05-01-review-security-receipt.md"
        status: pass
    human_judgment: false
  - id: D2
    description: "The identical SHA range re-run under the general profile, with the security-kept ⊆ general-kept superset contract checked"
    requirement: "AUD-06"
    verification:
      - kind: manual_procedural
        ref: "05-01-review-general-receipt.md"
        status: pass
    human_judgment: false
  - id: D3
    description: "Both receipts sanitized per D-07 before the first Phase 5 commit, reviewed and approved by a human at the Task 3 checkpoint"
    verification: []
    human_judgment: true
    rationale: "D-07 sanitization compliance is a judgment call on what counts as a leaked target-repo path or finding body; the plan requires explicit human sign-off before committing, which was obtained."

duration: ~1h27m (session-continuation span across a compaction boundary; not pure active-work time)
completed: 2026-08-20
status: complete
---

# Phase 5 Plan 01: Diff-Review Tracer Summary

**Both `review` profiles ran end to end on one real diff in a pinned target repo, sealing complete with zero live findings by design; a real cwd-scoping bug in the CLI's production git runner was found and fixed along the way.**

## Performance

- **Duration:** ~1h27m (18:47–20:14 local, spanning a mid-session compaction; not a pure active-work measurement)
- **Tasks:** 2 completed (Task 3 was the checkpoint that gated this plan's commits, not separate execution work)
- **Files modified:** 10 (3 created this session's tracked evidence, 7 touched by the cwd-fix task)

## Accomplishments

- Proved the `sec_overlay.cli` `review` command runs end to end against a real, pinned target repo (`mando` at `5f477d8c14..d06ce30d32`) in both `security` and `general` profiles, each sealing the coverage manifest `complete` with 14 of 15 changed files reviewable (one `.mdc` file excluded as `not-allowlisted`, `file_select.py:26-38,193-196`).
- Found and fixed a real production bug: `run_review`'s uninjected git-subprocess runner carried no `cwd`/`-C` binding to `--root`, so every `diffscope.py` git call silently ran against the CLI process's own working directory instead of the target repo — producing a silently-empty, falsely-sealed manifest when invoked from anywhere other than `--root`. Fixed with a one-line `cwd=root` addition to the shared runner (`cli.py:335`), proven by a new regression test using a real, uninjected `subprocess.run` against a temp git repo (RED confirmed before the fix, GREEN after).
- Confirmed the target repo's tracked tree and `HEAD` were byte-identical before and after every run this plan made (read-only against `mando` throughout).
- Recorded five D-11 defect-ledger rows in `05-DEFECTS.md`: the fixed cwd bug (blocker, fixed-here), the D-05 mixing-criterion deferral (no diff range in `mando`'s history mixes `app/` and `functions/` within the 5–30 file bound — `functions/` has only 5 commits total, all pre-dating any candidate range), the reviewer-dispatch-not-exercised deferral (D-13/D-15 — expected for a CLI-only tracer), the missing `--workspace` flag on `review` (surfaced by Task 2's profile collision), and the E-12 vacuous-superset-contract flag (∅ ⊆ ∅ needs re-verification against real findings in Phase 6).

## Task Commits

1. **Task 1: Security-profile tracer review + cwd bug fix** — `841c5d8` (fix) — includes the RED→GREEN regression test, the one-line runner fix, three cascading README updates, and the sec-overlay plugin version bump (1.68.6 → 1.68.7)
2. **Task 2: General-profile review + subset comparison** — no dedicated code commit; its output (`05-01-review-general-receipt.md`) was held uncommitted per plan design until Task 3's approval, then committed alongside Task 1's receipt and the defect ledger

**Plan metadata:** `e25c0b6` (docs: commit the three sanitized evidence files after Task 3's human sanitization sign-off)

## Key Files

- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py` — `cwd=root` added to the production git-subprocess runner
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_live.py` — new regression test with a real, uninjected runner against a temp git repo
- `.planning/phases/05-end-to-end-verification-audit-review/05-01-review-security-receipt.md` — sanitized security-profile receipt
- `.planning/phases/05-end-to-end-verification-audit-review/05-01-review-general-receipt.md` — sanitized general-profile receipt with the subset comparison
- `.planning/phases/05-end-to-end-verification-audit-review/05-DEFECTS.md` — the phase's D-11 defect ledger, seeded with five rows

## Decisions Made

- Zero live findings from the CLI-only run is by design (D-13/D-15), not a defect — see AUD-06 grounding in `05-RESEARCH.md`.
- Used `SEC_OVERLAY_HOME` (Task 2, Rule 3 auto-fix) to give the general-profile run its own sidecar workspace, since `review` exposes no `--workspace` override and the SCALE-03 resume-identity guard rejects a second profile against the default sidecar.
- Recorded, not silently re-ran, the vacuous superset-contract pass as E-12 for Phase 6 to close.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed `run_review`'s git-subprocess runner silently scoping to process cwd instead of `--root`**
- **Found during:** Task 1, preparing the first live security-profile run
- **Issue:** `partial(subprocess.run, timeout=timeout)` carried no `cwd=root`; `diffscope.py`'s git calls issue no `-C <path>` of their own, so every call ran against the CLI process's own working directory. Invoking `review` from outside `--root` (the real, non-test invocation path) silently produced an empty changed-file set and a zero-file sealed manifest with no error.
- **Fix:** Added `cwd=root` to the shared runner at `cli.py:335`; wrote a failing regression test first (`test_run_review_scopes_git_calls_to_root_not_process_cwd`, real uninjected runner, real temp git repo), confirmed RED, then GREEN after the fix.
- **Files modified:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py`, `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_live.py`, plus three cascading README updates (`helpers/README.md`, `helpers/sec_overlay/README.md`, `helpers/tests/README.md`) and the plugin version bump to `1.68.7`.
- **Verification:** Full test suite (1250 passed, 2 pre-existing unrelated environmental failures), `ruff check` clean, `ty check` clean; then confirmed against the real target repo — the `--prepare` run correctly found all 14 real changed files post-fix versus 0 pre-fix.
- **Committed in:** `841c5d8`

**2. [Rule 3 - Blocking] Used `SEC_OVERLAY_HOME` to give Task 2's general-profile run its own sidecar workspace**
- **Found during:** Task 2, first attempt at the general-profile run
- **Issue:** `review` has no `--workspace` flag (only `audit` does); the SCALE-03 resume-identity guard (`review_coverage.check_resume_identity`) rejected the general-profile run against Task 1's already-sealed security-profile sidecar with exit `2`, `resume rejected: profile changed from 'security' to 'general'`.
- **Fix:** Set `SEC_OVERLAY_HOME=<target-repo-root>/.sec-overlay-general` for the one command, giving the general run a separate, durable, target-adjacent workspace (same identity-derived slug, confirming both runs target the same repo) without touching Task 1's original sidecar.
- **Files modified:** none (environment-variable override only)
- **Verification:** General run sealed `complete`, same SHAs, 14/14 files done, 0 kept findings — same shape as Task 1's security run.
- **Committed in:** n/a (no code change; documented as a defect-ledger row in `05-DEFECTS.md` since `review`'s missing `--workspace` flag is a real CLI gap for Phase 6 to consider)

---

**Total deviations:** 2 auto-fixed (1 bug fix under Rule 1, 1 blocking-issue workaround under Rule 3). No architectural changes, no Rule 4 escalations.
**Impact on plan:** The Rule 1 fix was essential — without it, this tracer's security run would have silently produced a false-empty, falsely-sealed manifest with no error, which is exactly the kind of run-blocker D-10 scopes Phase 5 to fix. The Rule 3 workaround unblocked Task 2 without any code change; the underlying CLI gap is deferred to Phase 6.

## Issues Encountered

- File-count reconciliation (15 total changed files vs. 14 reviewable) required reading `file_select.py`'s actual `ALLOWED_EXTENSIONS`/exclusion logic rather than assuming; grounded the receipt's exclusion count in verified code (`file_select.py:26-38,193-196`) instead of inference.
- `rtk`'s transparent `find`→`fd` rewrite hid the `.sec-overlay` sidecar directory (dotfile) during investigation; worked around with `/bin/ls -la` and direct Python file reads.

## Next Phase Readiness

- Plans 05-02 through 05-04 (full audit run, finding-integrity readback, artifact-coverage readback) can proceed against the same pinned target and SHA range.
- `05-DEFECTS.md` now exists and carries five rows for Phase 6 to triage: the `review --workspace` gap, the D-05 mixing-criterion deferral, the reviewer-dispatch deferral, and the E-12 superset-contract flag (all `deferred`); the cwd bug is `fixed-here` and closed.

## Self-Check: PASSED

- FOUND: `05-01-review-security-receipt.md`
- FOUND: `05-01-review-general-receipt.md`
- FOUND: `05-DEFECTS.md`
- FOUND: `05-01-SUMMARY.md`
- FOUND commit `841c5d8` (fix: cwd-scoping bug)
- FOUND commit `e25c0b6` (docs: sanitized receipts)
- FOUND commit `2b4936e` (docs: this SUMMARY.md)

---
*Phase: 05-end-to-end-verification-audit-review*
*Plan: 01*
*Completed: 2026-08-20*
