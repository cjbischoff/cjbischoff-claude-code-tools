---
phase: 04-scale-resume-diff-output
plan: 03
subsystem: security-tooling
tags: [python, tdd, sec-overlay, review-coverage, cli, resume, sha-pinning]

requires:
  - phase: 04-scale-resume-diff-output (plan 02)
    provides: bounded review CLI (thread pool, per-unit timeout, review flags) that this plan resumes against
provides:
  - "A persisted model/profile identity on CoverageManifest (MANIFEST_VERSION 2), compared before any write on resume"
  - "check_resume_identity / ResumeIdentityError, refusing a mismatched resume with a non-zero exit naming the differing field"
  - "A resumed run's base_sha/head_sha sourced from the prior manifest, not from freshly-resolved --base/--head"
  - "Each persisted SHA round-tripped through resolve_ref_sha on resume, so a rewritten/GC'd SHA fails loudly instead of reading an empty diff"
affects: [sec-overlay-review-cli, sec-overlay-coverage-manifest]

actuals:
  tokens: 10916
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Identity/SHA checks placed strictly before the manifest's first write, proven by a byte-hash-unchanged test rather than by inspection"
    - "Resume-time validation reuses the existing exit-2 ValueError path instead of adding a second failure mode"

key-files:
  created: []
  modified:
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_coverage.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_coverage.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_cli.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_live.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md

key-decisions:
  - "Task 1 checkpoint resolved as option-a: identity lives on CoverageManifest itself (model/profile keyword fields, MANIFEST_VERSION 1 to 2), not a sibling artifact — one write, one atomic replace, identity travels with review_comments.json's embedded manifest for free."
  - "Task 3's fix is entirely in cli.py's SHA source selection on resume; diffscope.py needed no changes since every ref-consuming function there already takes a pre-resolved SHA string."
  - "A pre-existing test_review_live.py test that resumed one target across two profile values (to compare finding-filtering, not to model a resume) was split into two independent targets, since Task 2's identity gate correctly rejects that call as a genuine identity mismatch."

patterns-established:
  - "A resume-identity check on CoverageManifest.load() precedes the manifest's construction, guaranteeing a rejected resume writes nothing (verified by a byte-hash-unchanged test)."

requirements-completed: [SCALE-03]

coverage:
  - id: D1
    description: "A resumed review run compares persisted model identity and profile before any write, refusing a mismatch with a non-zero exit naming the differing field; a rejected resume leaves the prior manifest byte-identical."
    requirement: SCALE-03
    verification:
      - kind: unit
        ref: "tests/test_review_coverage.py -- resume-identity tests (model mismatch, profile mismatch, no-recorded-identity, byte-hash-unchanged-on-rejection, version-1 manifest still loads)"
        status: pass
    human_judgment: false
  - id: D2
    description: "A resumed run reads diffs and file text only at the SHAs the prior run sealed, round-tripped through resolve_ref_sha; a moved HEAD does not change what is read, and an unresolvable persisted SHA exits non-zero instead of reading an empty diff."
    requirement: SCALE-03
    verification:
      - kind: unit
        ref: "tests/test_cli.py::test_review_resume_reads_at_persisted_head_sha_despite_moved_head"
        status: pass
      - kind: unit
        ref: "tests/test_cli.py::test_review_resume_with_unresolvable_persisted_sha_fails_loudly"
        status: pass
      - kind: manual_procedural
        ref: "scratch git repo: run once with --profile security (rc 0), resume with --profile general (rc 2, stderr names 'profile changed from security to general')"
        status: pass
    human_judgment: false

duration: 18min
completed: 2026-08-20
status: complete
---

# Phase 4 Plan 3: Resume Identity and SHA-Pinning Summary

**A resumed review run now proves it is the same run — same model, same profile, same sealed SHAs — before it is allowed to add to prior coverage, closing the "resume under a different config launders coverage" gap (SCALE-03).**

## Performance

- **Duration:** 18 min (Task 2 RED to Task 3 GREEN; excludes the Task 1 decision-checkpoint pause from the prior segment)
- **Started:** 2026-08-20T12:08:32-06:00 (Task 2 RED commit)
- **Completed:** 2026-08-20T12:25:56-06:00 (Task 3 GREEN commit)
- **Tasks:** 2 code tasks (Task 1 was a checkpoint:decision, resolved option-a)
- **Files modified:** 8

## Accomplishments

- `CoverageManifest` gained keyword-only `model`/`profile` fields (`MANIFEST_VERSION` 1 to 2); `load()` reads both with a `.get` default so a version-1 manifest still loads.
- `check_resume_identity` / `ResumeIdentityError` refuse a mismatched resume before `run_review` constructs the manifest — the only ordering that makes "nothing persisted on rejection" true, proven by a test that hashes the prior artifact's bytes before and after a rejected resume.
- A resumed run's `base_sha`/`head_sha` now come from the prior manifest's sealed values instead of freshly resolving `--base`/`--head`; each persisted SHA is still round-tripped through `resolve_ref_sha`, so a rewritten or GC'd SHA fails the run (exit 2) instead of silently reading a different tree as an empty diff.
- Manual scratch-workspace check confirms end-to-end behavior: `--profile security` then resume with `--profile general` exits 2, stderr names `profile changed from 'security' to 'general'`.

## Task Commits

Each task was committed atomically (both tasks carried `tdd="true"`, so each has a RED and GREEN commit):

1. **Task 2 RED: resume-identity gate tests** - `7096f5a` (test)
2. **Task 2 GREEN: reject a resumed run whose model/profile changed** - `70e4ed3` (feat)
3. **Task 3 RED: SHA-pinning-on-resume tests** - `d84422f` (test)
4. **Task 3 GREEN: pin resumed reads to the prior run's sealed SHAs** - `cf0bad9` (feat)

_Task 1 was a `checkpoint:decision` (no commit) resolved as option-a in the prior execution segment._

## Files Created/Modified

- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_coverage.py` - `MANIFEST_VERSION` 2, `CoverageManifest.__init__`/`to_dict`/`load` gain `model`/`profile`, `ResumeIdentityError`, `check_resume_identity`
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py` - `run_review` gains a model identity parameter, performs the identity check pre-write, and on resume sources `base_sha`/`head_sha` from the prior manifest before round-tripping each through `resolve_ref_sha`
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_coverage.py` - resume-identity tests (match, model mismatch, profile mismatch, no-recorded-identity, byte-hash-unchanged-on-rejection, version-1-manifest-still-loads)
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_cli.py` - SHA-pinning-on-resume tests (moved HEAD, unresolvable persisted SHA)
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_live.py` - profile-comparison test split into two independent targets (Rule 1 auto-fix; see Deviations)
- `plugins/sec-overlay/skills/sec-overlay/helpers/README.md`, `sec_overlay/README.md`, `tests/README.md` - doc updates tracking the above, in the same commits per plugin governance

## Decisions Made

- **Task 1 (checkpoint, resolved before this segment):** option-a — identity lives on `CoverageManifest` itself, not a sibling artifact. One write, one atomic replace; identity reaches every consumer of `review_comments.json`'s embedded manifest with no extra wiring. Cost accepted: `MANIFEST_VERSION` 1 to 2, two new keys in `to_dict()`.
- No architectural deviation in Task 3: confirmed by full read of `diffscope.py` that every ref-consuming function (`changed_file_records`, `file_diff_line_count`, `binary_paths`, `file_diff_text`, `file_text_at_ref`) already takes a pre-resolved SHA string, so the fix is entirely in which SHA `cli.py` selects and passes down.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Split a pre-existing test broken by Task 2's own identity gate**
- **Found during:** Task 3, full-suite regression check (`uv run pytest -q`)
- **Issue:** `test_review_live.py::test_profile_split_null_dereference_security_excludes_general_includes` called `run_review` twice against the same target with two different `profile` values, intending to compare finding-filtering output — not to model a resume. Task 2's `check_resume_identity` gate (committed earlier in this plan) correctly rejected the second call as a genuine identity mismatch (`rc == 2` instead of the expected `0`).
- **Fix:** Split the test into two independent target directories (`tmp_path / "security"`, `tmp_path / "general"`), each with its own `_record_return` call and its own workspace lookup, so the two `run_review` calls are genuinely independent runs rather than a resume.
- **Files modified:** `tests/test_review_live.py`
- **Verification:** `uv run pytest tests/test_review_live.py -q` → 13 passed; full suite back down to the 2 known baseline failures.
- **Committed in:** `cf0bad9` (part of Task 3's GREEN commit)

**2. [Rule 1 - Bug] Corrected a stale RED-phase note in tests/README.md**
- **Found during:** Task 3, editing `tests/README.md`'s Task 2 paragraph
- **Issue:** The paragraph still read "currently failing (RED phase; `ResumeIdentityError`/`check_resume_identity` do not exist yet)" even though Task 2's GREEN commit (`70e4ed3`) had already landed before this segment began.
- **Fix:** Removed the stale clause while editing that same paragraph region.
- **Files modified:** `tests/README.md`
- **Committed in:** `d84422f`/`cf0bad9`

---

**Total deviations:** 2 auto-fixed (2 Rule 1)
**Impact on plan:** Both fixes were directly caused by this plan's own earlier changes (Task 2's identity gate; a stale doc note from Task 2). No scope creep — the product behavior (the identity gate itself) was preserved as designed; only the pre-existing test's setup and a documentation note were corrected.

## Issues Encountered

None beyond the deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- SCALE-03 is fully closed: identity persistence, pre-write comparison, and SHA-pinning on resume are all implemented, tested, and verified manually against a scratch git repo.
- `models.py` and `evidence.py` remain untouched; `helpers/pyproject.toml` still declares zero runtime dependencies.
- Full suite (`uv run pytest -q`): 1242 passed, 2 failed (both pre-existing environmental failures — missing semgrep rules submodule, gitignored bench corpus seed — not a regression from this plan).
- `uv run ruff check sec_overlay/ bench/ tests/` and `uv run ty check`: clean.
- No blockers for the next phase.

---
*Phase: 04-scale-resume-diff-output*
*Completed: 2026-08-20*

## Self-Check: PASSED
