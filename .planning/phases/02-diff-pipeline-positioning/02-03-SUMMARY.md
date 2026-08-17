---
phase: "02"
plan: "03"
subsystem: sec-overlay diff review pipeline
tags: [coverage-manifest, hunk-parser, state-machine, sec-overlay]
dependency graph:
  requires: [DIFF-02]
  provides: [DIFF-03, DIFF-04]
  affects: [cli.py review command]
tech-stack:
  added: []
  patterns:
    - single transition-table state machine (_ALLOWED_TRANSITIONS)
    - frozen dataclass with tuple fields for a provably pure parser
key-files:
  created:
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_coverage.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_diffhunks.py
  modified:
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_coverage.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/diffhunks.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md
    - plugins/sec-overlay/.claude-plugin/plugin.json
    - plugins/sec-overlay/CHANGELOG.md
decisions:
  - CoverageTransitionError extends RuntimeError, not ValueError, matching the plan's Artifacts
    section verbatim.
  - seal() raises on an empty manifest instead of vacuously returning "complete" — a run must
    never claim coverage it did not perform (T-02-05).
metrics:
  duration: "one session"
  completed: "2026-08-17"
actuals:
  tokens: 21000
  tasks: 3
  commits: 1
status: complete
---

# Phase 02 Plan 03: Coverage manifest state machine and hunk parser Summary

Completes the `CoverageManifest` state machine (DIFF-03) and the unified-diff hunk parser
(DIFF-04) to full behavior, replacing the tracer-stage versions from plan 02-02.

## What this plan built

`review_coverage.py`'s `CoverageManifest` now gates every state change through one
`_ALLOWED_TRANSITIONS` table (`pending` → `in_review`/`failed`; `in_review` → `done`/`failed`;
`done`/`failed` terminal). `seal()` returns `"complete"` when every entry is `done`, `"partial"`
when some are `failed`, and raises `CoverageTransitionError` when any entry is still
`pending`/`in_review`, or when the manifest has no entries at all — a run must never claim
coverage it did not perform.

`diffhunks.py`'s `parse_hunks` builds an immutable `Hunk` (frozen dataclass, tuple-typed
`added`/`deleted`/`context` fields) through an internal mutable `_MutableHunk` builder, so the
finished parser output is provably pure. New `hunk_for_line(hunks, line)` returns the containing
`Hunk` or `None`.

`test_review_coverage.py` (23 tests) and `test_diffhunks.py` (18 tests) cover every legal and
illegal transition, the empty-manifest seal refusal, atomic-write round-tripping through `load`,
CRLF and no-newline-marker handling, and a three-path lifecycle plus a contiguous `line_in_hunk`
sweep proving the parser and the membership check agree over a full hunk range.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed a trailing spurious context line in the hunk parser**
- **Found during:** Task 2, GREEN phase
- **Issue:** `diff_text.replace("\r\n", "\n").split("\n")` produced a trailing empty-string
  element when the diff text ended in a newline; the parser appended it as a spurious context
  line.
- **Fix:** switched to `diff_text.splitlines()`, which normalizes CRLF and does not produce a
  trailing empty element.
- **Files modified:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/diffhunks.py`
- **Commit:** `21f54fc`

**2. [Rule 1 - Bug] Fixed `run_review` crashing on a zero-file diff**
- **Found during:** Task 1, after the empty-manifest `seal()` raise landed
- **Issue:** `cli.py`'s `run_review` unconditionally called `manifest.seal()`; on a diff with zero
  reviewable files this now raised `CoverageTransitionError` instead of returning cleanly. This
  file is not in the plan's `files_modified` list, but the fix is a direct regression from this
  plan's own Task 1 change.
- **Fix:** added `if not selection.reviewable: return 0` before `manifest.seal()`, so a review
  with nothing to review exits 0 (vacuous success) rather than crashing.
- **Files modified:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py`
- **Commit:** `21f54fc`

**3. [Rule 4-adjacent, resolved by plan text] `CoverageTransitionError` base class**
- **Found during:** carried over from the prior session as an open question
- **Resolution:** the plan's Artifacts section specifies `CoverageTransitionError(RuntimeError)`
  verbatim (`.planning/phases/02-diff-pipeline-positioning/02-03-PLAN.md:92`); changed the base
  class from `ValueError` to `RuntimeError` to match. No test depends on the specific base class.
- **Commit:** `21f54fc`

## Verification

- `uv run pytest -q` (from `plugins/sec-overlay/skills/sec-overlay/helpers/`): 952 passed, 2
  failed. Both failures are the pre-existing environmental gaps documented in the skill
  `CLAUDE.md` §1 (gitignored bench corpus, excluded semgrep submodule) — untested by design in a
  clean checkout, not caused by this plan.
- `uv run ruff check sec_overlay/ tests/`: clean.
- `git diff HEAD~2 -- sec_overlay/coverage.py sec_overlay/models.py sec_overlay/evidence.py`:
  0 lines — the frozen milestone contracts are untouched.
- `git diff HEAD~1 -- tests/test_review_tracer.py`: 0 lines — unchanged, as the plan required.

## Known Stubs

None — plan 02-03 completes `CoverageManifest` and `parse_hunks` to full behavior; no stub values
remain in the touched modules.

## Threat Flags

None — the changed surface (an internal state machine and a pure parser) does not add new
network endpoints, auth paths, or trust boundaries beyond what the plan's threat register
(T-02-05 through T-02-12) already covers.

## Self-Check: PASSED

- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_coverage.py`: FOUND
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/diffhunks.py`: FOUND
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py`: FOUND
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_coverage.py`: FOUND
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_diffhunks.py`: FOUND
- Commit `21f54fc`: FOUND (`git log --oneline --all | grep 21f54fc`)
