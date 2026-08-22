---
phase: 04-scale-resume-diff-output
plan: 01
subsystem: testing
tags: [python, sarif, sec-overlay, tdd, diff-review]

requires: []
provides:
  - "bundle.py: group_bundles gives ReviewUnit real grouping semantics (impl/test pairs, locale/config siblings, single-file fallback)"
  - "review_agent.parse_review_response: bundle_paths widens the focus rule so any bundle member's own path is kept and attributed correctly"
  - "cli.run_review: threads each ReviewUnit's membership into recorded_return_source via bundle_paths_by_path"
  - "sarif.py / review_comments.py: OUT-01/OUT-02 contracts now locked by dedicated tests (both modules were already correct from the tracer plan)"
affects: [04-02, 04-03]

actuals:
  tokens: 13776
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "ReviewUnit grouping: impl/test pairs and locale/config siblings share a unit; everything else is a one-file fallback unit"
    - "bundle_paths_by_path threading: cli builds a path->membership map once from group_bundles output, review_agent widens its focus rule from that map, single-file behavior preserved when bundle_paths is None"

key-files:
  created:
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/bundle.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_bundle.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_comments.py
  modified:
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_agent.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_agent.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_sarif.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md

key-decisions:
  - "Task 3 found sarif.py and review_comments.py already fully correct from the tracer plan (Task 1) — closed the test-coverage gap instead of touching implementation, per the plan's own instruction to close only a gap the tests expose."
  - "Fallback grouping key in bundle.py strips literal test/tests path segments before comparison so this repo's own tests/test_foo.py convention pairs with root-level foo.py; the doc records this does NOT generalize to helpers/sec_overlay/ vs helpers/tests/, which still land safely as single-member fallback units."
  - "Rewrote **kwargs-splat Finding test helpers (_finding(**overrides)) as explicit-parameter functions in test_sarif.py and test_review_comments.py after ty check flagged the heterogeneous dict splat as untypeable against the Finding dataclass constructor."

patterns-established:
  - "SARIF fingerprint is a byte-equality contract, not Unicode-canonical-equality: two visually-identical but differently-normalized evidence strings produce different fingerprints, on purpose, and this is now a locked test rather than an accident."

requirements-completed: [SCALE-01, OUT-01, OUT-02]

coverage:
  - id: D1
    description: "group_bundles groups reviewable files into ReviewUnits by real rules (impl/test pairs, locale/config siblings) instead of one-file-per-unit"
    requirement: SCALE-01
    verification:
      - kind: unit
        ref: "tests/test_bundle.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "parse_review_response's focus rule widens to bundle_paths so any member's own path is kept and attributed correctly, cli.run_review threads this end to end"
    requirement: SCALE-01
    verification:
      - kind: unit
        ref: "tests/test_review_agent.py"
        status: pass
      - kind: unit
        ref: "tests/test_review_tracer.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "review_comments.json carries exactly the 5 documented comment keys plus the embedded coverage manifest, including on an empty comment list"
    requirement: OUT-01
    verification:
      - kind: unit
        ref: "tests/test_review_comments.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every SARIF result carries a message-independent, byte-equality partialFingerprints entry; empty results carry no fingerprint key anywhere"
    requirement: OUT-02
    verification:
      - kind: unit
        ref: "tests/test_sarif.py"
        status: pass
    human_judgment: false

duration: 47min
completed: 2026-08-20
status: complete
---

# Phase 4 Plan 01: Bundle Grouping, Widened Focus Rule, and Diff-Output Contract Tests Summary

**Real `group_bundles` grouping semantics, a widened `bundle_paths` focus rule threaded end to end through `cli.run_review`, and locked test coverage proving the OUT-01/OUT-02 diff-anchored comment and SARIF fingerprint contracts.**

## Performance

- **Duration:** 47 min (first task commit to last task commit)
- **Started:** 2026-08-20T09:51:00-06:00
- **Completed:** 2026-08-20T10:37:47-06:00
- **Tasks:** 3/3 completed
- **Files modified:** 12 (across all 3 task commits)

## Accomplishments

- `bundle.group_bundles` now groups reviewable files by real rules — impl/test pairs (Python, Go, JS/TS conventions) and locale/config siblings sharing a directory — with everything else falling back to its own single-member unit; totality, order preservation, and deterministic `unit_id`s are all covered by 14 tests in `test_bundle.py`.
- `review_agent.parse_review_response` gained a keyword-only `bundle_paths` parameter that widens the focus rule: a `code_comment` naming any member of the reviewing unit becomes a `Finding` attributed to that entry's own path, not just the single file under review; `bundle_paths=None` preserves the pre-widening single-file behavior exactly.
- `cli.run_review` builds a `path -> membership` map from `group_bundles(selection.reviewable)` and threads it into `recorded_return_source` via `bundle_paths_by_path`, so real bundling is live end to end without changing the per-file dispatch loop's shape.
- `sarif.py` and `review_comments.py` needed no implementation change — both already satisfied their contracts from the tracer plan (Task 1). Task 3 closed the missing test coverage instead: 8 new tests lock the `partialFingerprints` contract (message-independence, file/cls/evidence sensitivity, empty-results, whitespace evidence, byte-equality on Unicode-equivalent strings) and a new `test_review_comments.py` locks the `review_comments.json` shape (5-key payload, embedded manifest, empty-list case).

## Task Commits

Each task was committed atomically:

1. **Task 1: Tracer — wire bundling and diff comments end to end** - `6b671d2` (feat, committed before this session)
2. **Task 2: Real `group_bundles` grouping semantics and widened focus rule** - `b250048` (feat)
3. **Task 3: Lock OUT-01/OUT-02 contracts with new test coverage** - `fc42aa3` (test)

## Files Created/Modified

- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/bundle.py` - `group_bundles`/`ReviewUnit`, real grouping rules
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_agent.py` - `parse_review_response`'s `bundle_paths`, `recorded_return_source`'s `bundle_paths_by_path`
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py` - `run_review` threads bundle membership into the review source
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_bundle.py` - 14 tests for `group_bundles`
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_agent.py` - 3 tests for `bundle_paths` widening
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_sarif.py` - 8 tests for the `partialFingerprints` contract
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_comments.py` - 5 tests for the `review_comments.json` contract (new file)
- `plugins/sec-overlay/skills/sec-overlay/helpers/README.md` - module map updated for real grouping semantics and both new test files
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md` - narrative test-suite changelog updated for all 3 tasks
- `plugins/sec-overlay/.claude-plugin/plugin.json` - version 1.62.0 -> 1.63.1
- `plugins/sec-overlay/CHANGELOG.md` - 1.63.0 and 1.63.1 entries

## Decisions Made

- Task 3 investigation found no implementation gap in `sarif.py`/`review_comments.py` — both were already complete from the tracer plan. Per the plan's own instruction ("write failing tests first, then close any implementation gap the tests expose"), no gap existed to close, so only tests and docs changed.
- Rewrote the `Finding(**overrides)`-style test helpers in `test_sarif.py` and `test_review_comments.py` as explicit-parameter functions after `ty check` flagged the heterogeneous-dict splat as untypeable against the `Finding` dataclass constructor (50 `invalid-argument-type` diagnostics). This is a test-only change with no behavior difference; `ty check` is now clean.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] `ty check` failure from `**dict`-splat Finding constructors**
- **Found during:** Task 3 (writing `_finding(**overrides)` helpers in `test_sarif.py` and `test_review_comments.py`)
- **Issue:** `ty` cannot verify a `Finding(**heterogeneous_dict)` call against the dataclass's typed fields, producing 50 `invalid-argument-type` diagnostics across both files — this would have failed the plan's own `<verify>` gate (`uv run ty check`).
- **Fix:** Rewrote both helpers to take explicit named parameters with defaults instead of a `**overrides` dict splat, then construct `Finding(...)` with named arguments. No test assertions or call sites changed in behavior.
- **Files modified:** `tests/test_sarif.py`, `tests/test_review_comments.py`
- **Verification:** `uv run ty check` → "All checks passed!"; `uv run pytest tests/test_sarif.py tests/test_review_comments.py -q` → all pass
- **Committed in:** `fc42aa3` (part of Task 3 commit)

---

**Total deviations:** 1 auto-fixed (Rule 3)
**Impact on plan:** Test-authoring detail only; no scope creep, no production code touched.

## Issues Encountered

- **doc-update-guard hook (prek) required updating 3 separate nested README.md files for Task 2's commit** (`helpers/README.md`, `helpers/sec_overlay/README.md`, `helpers/tests/README.md`) since it checks the immediate folder of every staged file independently. Task 3 only required 2 (`helpers/README.md` — explicit plan acceptance criterion — and `helpers/tests/README.md`, since `sec_overlay/*.py` files were unchanged for Task 3).
- **A nested `.git` directory was discovered inside `plugins/sec-overlay/skills/sec-overlay/helpers/`** (branch `main`, unrelated 2-commit history `240b4f0`/`46b59db`), separate from and shadowing the marketplace repo's own history when a git command's cwd is inside `helpers/`. This is pre-existing, out of scope for this plan, and was never touched — all git operations in this plan ran from the marketplace repo root. Flagged here for a maintainer to investigate and likely delete; it is not referenced by `.gitmodules` and is not tracked by the outer repo.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`group_bundles`, the widened `bundle_paths` focus rule, and the OUT-01/OUT-02 output contracts are all implemented, tested, and documented. Phase 4 plans 02 and 03 (per `04-PATTERNS.md`) can build on this bundling and output foundation without further changes to `bundle.py`, `sarif.py`, or `review_comments.py`.

## Self-Check: PASSED

All created files and all 3 task commit hashes verified present on disk / in git history.
