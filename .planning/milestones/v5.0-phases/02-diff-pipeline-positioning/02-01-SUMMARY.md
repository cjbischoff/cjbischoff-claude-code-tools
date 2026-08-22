---
phase: 02-diff-pipeline-positioning
plan: 01
subsystem: security-tooling
tags: [python, cli, git-diff, unified-diff, stdlib-only, sec-overlay]

requires:
  - phase: 01-baseline-health-verification
    provides: existing `sec_overlay` package structure, `Workspace`, `coverage.py`, `models.py`, `phase_gate.py` audit-mode path
provides:
  - "`sec-overlay review --base <ref> --head <ref> --root <path>` CLI verb"
  - "`diffscope.validate_ref` / `resolve_ref_sha` / `changed_file_records` / `file_diff_text`"
  - "`file_select.partition` (path allowlist + exclusion reasons)"
  - "`review_coverage.CoverageManifest` (pending/in_review/done/failed state machine, atomic-write persistence, seal-or-raise)"
  - "`diffhunks.parse_hunks` / `added_line_numbers` / `line_in_hunk` (stdlib unified-diff parser)"
  - "`positioning.resolve_position` returning `PositionResult` (exact-match only, no fuzzy matching)"
  - "`phase_gate.review_position_gate` (additive review-mode gate beside the untouched audit-mode path)"
  - "`Workspace.artifacts` property"
affects: [02-02-diff-pipeline-positioning, 02-03-diff-pipeline-positioning, 02-04-diff-pipeline-positioning, 02-05-diff-pipeline-positioning]

actuals:
  tokens: 11603
  tasks: 3
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Injectable `runner=subprocess.run` kwarg threaded through every diffscope git call, overridable in tests via `monkeypatch.setattr(subprocess, \"run\", fake_run)`"
    - "Resolve-both-refs-to-SHA-before-any-other-git-call (D-06/D-07), closing a ref-repoint TOCTOU window"
    - "review-mode gate lives beside, not inside, the audit-mode gate in `phase_gate.py` — zero-line diff on the audit path"
    - "`CoverageManifest.seal()` raises rather than silently downgrading an unfinished (`pending`/`in_review`) entry to `partial`"

key-files:
  created:
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/file_select.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_coverage.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/diffhunks.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/positioning.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_tracer.py
  modified:
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/workspace.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/diffscope.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phase_gate.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_workspace.py

key-decisions:
  - "Coverage manifest lives at `artifacts/coverage_manifest.json` with `{version, base_sha, head_sha, seal, files: [{path, state, note}]}` shape (Task 1 checkpoint, option-a, resolved before this segment)."
  - "`PositionResult` is a phase-owned frozen dataclass, not a `models.FindingStatus` member — `models.py` stays frozen for this plan."
  - "`positioning.py` uses exact consecutive-string matching only; no `difflib` import, so no fuzzy match can be reported as an exact location."

patterns-established:
  - "Tracer-first wiring: one changed file, one hunk, one finding, through every new/extended module, before any plan expands a stage in isolation."

requirements-completed: [DIFF-01, DIFF-02, DIFF-03, DIFF-04, POS-01, POS-03]

coverage:
  - id: D1
    description: "`sec-overlay review --base <sha> --head <sha>` on a single-changed-file diff exits 0 and seals the coverage manifest `complete`"
    requirement: "DIFF-01"
    verification:
      - kind: unit
        ref: "tests/test_review_tracer.py#test_review_one_changed_file_exits_zero_and_seals_complete"
        status: pass
    human_judgment: false
  - id: D2
    description: "`diffscope` resolves both refs to SHAs before any other git call and returns `ChangedFile` records"
    requirement: "DIFF-02"
    verification:
      - kind: unit
        ref: "tests/test_diffscope.py"
        status: pass
      - kind: unit
        ref: "tests/test_review_tracer.py#test_validate_ref_rejects_leading_dash"
        status: pass
    human_judgment: false
  - id: D3
    description: "`file_select.partition` splits changed files into reviewable/excluded without importing `Finding`"
    requirement: "DIFF-03"
    verification:
      - kind: unit
        ref: "tests/test_review_tracer.py#test_review_one_changed_file_exits_zero_and_seals_complete (exercises partition via the CLI path)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Coverage manifest holds one entry per reviewable file, both resolved SHAs, and raises rather than sealing over an unfinished entry"
    requirement: "DIFF-04"
    verification:
      - kind: unit
        ref: "tests/test_review_tracer.py#test_review_one_changed_file_exits_zero_and_seals_complete"
        status: pass
    human_judgment: false
  - id: D5
    description: "`diffhunks.parse_hunks`/`added_line_numbers` parse a unified diff with stdlib only"
    requirement: "POS-01"
    verification:
      - kind: unit
        ref: "tests/test_review_tracer.py#test_parse_hunks_and_added_line_numbers"
        status: pass
    human_judgment: false
  - id: D6
    description: "`phase_gate.review_position_gate` drops a finding whose confirmed line falls outside the diff, keeps an in-hunk finding, and leaves the audit-mode gate untouched"
    requirement: "POS-03"
    verification:
      - kind: unit
        ref: "tests/test_review_tracer.py#test_review_position_gate_keeps_in_hunk_finding"
        status: pass
      - kind: unit
        ref: "tests/test_phase_gate.py (audit-mode regression)"
        status: pass
    human_judgment: false

duration: 2h35m
completed: 2026-08-17
status: complete
---

# Phase 2 Plan 1: End-to-end review-mode tracer Summary

**`sec-overlay review` CLI verb wiring one changed file, one hunk, one finding through diffscope, file_select, review_coverage, diffhunks, positioning, and phase_gate — sealing a `complete` coverage manifest, stdlib-only, zero frozen-contract diff**

## Performance

- **Duration:** 2h35m
- **Started:** 2026-08-17 (session start, pre-compaction)
- **Completed:** 2026-08-17
- **Tasks:** 3 (1 checkpoint:decision, 2 auto/tracer)
- **Files modified:** 15 (across both task commits, including governance docs)

## Accomplishments
- `sec-overlay review --base <ref> --head <ref> --root <path>` runs end to end on a single-file diff, exits 0, and leaves `artifacts/coverage_manifest.json` sealed `complete` with both resolved SHAs.
- New stdlib-only modules `file_select.py`, `review_coverage.py`, `diffhunks.py`, `positioning.py`, each with the minimal correct shape the tracer needs — no throwaway code, nothing later plans must rewrite.
- `diffscope.py` and `phase_gate.py` extended additively; `changed_files()`, `head_sha()`, `_line_in_range`, and every audit-mode symbol are byte-identical to `HEAD~1`.
- `coverage.py`, `models.py`, `evidence.py` — the three frozen milestone contracts — show a zero-line diff for this plan (confirmed via `git diff HEAD~1`).
- `PositionResult` established as the phase's own result type; no `difflib` import in `positioning.py`, so no fuzzy match can be reported as an exact position.
- `Workspace.artifacts` property added, TDD (red/green), covering the four stated behaviors (path, override-independence, `ensure()` creation, `ensure()` idempotency).

## Task Commits

Each task was committed atomically:

1. **Task 1: Confirm coverage manifest location and shape** — resolved via checkpoint:decision (option-a accepted) prior to this execution segment; no code commit for this task.
2. **Task 2: Add the artifacts directory to Workspace** — `77ad9ff` (feat)
3. **Task 3: End-to-end review of one changed file — tracer path** — `912b807` (feat)

**Plan metadata:** pending (this commit)

## Files Created/Modified

- `sec_overlay/workspace.py` — `artifacts` property (`root / "artifacts"`), added to `ensure()`'s directory list.
- `sec_overlay/diffscope.py` — `_REF_RE`, `validate_ref`, `resolve_ref_sha`, `ChangedFile`, `changed_file_records`, `file_diff_text` (all additive; `changed_files()`/`head_sha()` untouched).
- `sec_overlay/file_select.py` (new) — `ALLOWED_EXTENSIONS`, `DEFAULT_EXCLUDE_GLOBS`, `DEFAULT_MAX_DIFF_LINES`, `EXCLUSION_REASONS`, `ExcludedFile`, `Selection`, `partition`.
- `sec_overlay/review_coverage.py` (new) — `MANIFEST_FILENAME`, `STATES`, `SEALS`, `FileCoverage`, `CoverageTransitionError`, `CoverageManifest` (`add`/`start`/`finish`/`fail`/`seal`/`failed_entries`/`path`/`to_dict`/`load`, atomic-write persistence).
- `sec_overlay/diffhunks.py` (new) — `_HUNK_RE`, `Hunk`, `parse_hunks`, `added_line_numbers`, `line_in_hunk`, `hunk_for_line`.
- `sec_overlay/positioning.py` (new) — `POSITION_DECISIONS`, `DECLINE_REASONS`, `PositionResult`, `resolve_position`, `_match_consecutive`.
- `sec_overlay/phase_gate.py` — `OUTSIDE_DIFF_REASON`, `DroppedFinding`, `review_position_gate` (additive; audit-mode path untouched).
- `sec_overlay/cli.py` — `review` subparser (`--base` required, `--head` default `HEAD`, `--root`) and dispatch branch.
- `tests/test_workspace.py` — four new behaviors for `Workspace.artifacts`.
- `tests/test_review_tracer.py` (new) — 6 tests covering the full tracer path.
- Governance set staged with both commits: `sec_overlay/README.md`, `helpers/README.md`, `tests/README.md`, `plugin.json` (1.37.11 → 1.39.0 across the two commits), `CHANGELOG.md`.

## Decisions Made

- Coverage manifest shape and path confirmed at the Task 1 checkpoint: `artifacts/coverage_manifest.json`, `{version, base_sha, head_sha, seal, files: [{path, state, note}]}` (option-a — kept `version` for Phase 4's manifest-format gate).
- `PositionResult` kept as a phase-owned frozen dataclass rather than extending `models.FindingStatus`, preserving the frozen-milestone-contract invariant.
- `positioning.py` implements exact consecutive-line matching only (no `difflib`), per RESEARCH.md Pitfall 2 — a fuzzy match must never be reported as an exact position.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `_REF_RE` allowlist pattern did not reject a leading dash**
- **Found during:** Task 3 (writing `test_validate_ref_rejects_leading_dash`, which the plan's own `<behavior>` section requires)
- **Issue:** The plan's literal pattern `^[A-Za-z0-9._/-]+$` places `-` inside the character class, so a ref like `-oProxyCommand=...` matches the pattern and is NOT rejected — directly contradicting the plan's own stated intent ("a ref beginning with a dash fails the pattern, which is what keeps it from reaching git as an option") and T-02-01's mitigation text in the threat register.
- **Fix:** Changed the pattern to `^(?!-)[A-Za-z0-9._/-]+$` — a negative lookahead rejecting any ref starting with `-`, while keeping `-` legal elsewhere in the ref (branch names like `feature-x` still validate).
- **Files modified:** `sec_overlay/diffscope.py`
- **Verification:** `tests/test_review_tracer.py::test_validate_ref_rejects_leading_dash` passes; full `test_diffscope.py` suite still passes (no regression on existing valid refs).
- **Committed in:** `912b807` (Task 3 commit)

**2. [Rule 2 - Missing critical functionality] `CoverageManifest.seal()` did not raise on an unfinished entry**
- **Found during:** Task 3, threat-model compliance check before finalizing — T-02-05 (Repudiation, `CoverageManifest.seal`, severity high, disposition `mitigate`) requires `seal()` to raise rather than seal over a `pending`/`in_review` entry, so a run can never claim coverage it did not perform.
- **Issue:** The initial implementation only branched on `complete` (all `done`) vs. `partial` (anything else), silently downgrading a `pending`/`in_review` entry to `partial` alongside a legitimately `failed` entry — masking the difference between "some files failed review" and "the run never finished."
- **Fix:** `seal()` now raises `CoverageTransitionError` if any entry is `pending` or `in_review`; `partial` is reserved for the case where every entry reached a terminal state (`done` or `failed`) with at least one `failed`.
- **Files modified:** `sec_overlay/review_coverage.py`
- **Verification:** Re-ran the full plan test/lint suite after the fix — 6/6 tracer tests pass, ruff clean, no regressions.
- **Committed in:** `912b807` (Task 3 commit)

**3. [Rule 3 - Blocking] Missing `review` dispatch branch in `cli.py::main()`**
- **Found during:** Task 3, first test run (`test_review_one_changed_file_exits_zero_and_seals_complete` asserted `rc == 0`, got `rc == 1`)
- **Issue:** The `review` argparse subparser was wired but `main()`'s dispatch `if args.cmd == ...` chain had no `"review"` branch, so every invocation fell through to `return 1` without calling `run_review` at all.
- **Fix:** Added `if args.cmd == "review": return run_review(args.base, args.head, args.root)` before the final fallback `return 1`.
- **Files modified:** `sec_overlay/cli.py`
- **Verification:** All 6 tracer tests pass after the fix.
- **Committed in:** `912b807` (Task 3 commit)

---

**Total deviations:** 3 auto-fixed (1 Rule 1, 1 Rule 2, 1 Rule 3).
**Impact on plan:** All three were necessary for correctness (Rule 1, Rule 3) or for a stated threat-model mitigation (Rule 2). No scope creep — no file outside the plan's `files_modified` list was touched, and no signature or return-type listed in the plan changed.

## Issues Encountered

None beyond the three deviations above, all resolved within the task.

Two pre-existing environmental test failures were confirmed present and unrelated to this plan (`tests/test_bench.py::test_seed_corpus_is_valid`, `tests/test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd` — gitignored bench corpus and excluded semgrep submodule on a clean checkout), explicitly permitted by this plan's own `<verification>` block and by `plugins/sec-overlay/CLAUDE.md`. No action taken.

## Known Stubs

None. `ALLOWED_EXTENSIONS` in `file_select.py` holds only the extensions the tracer fixture needs (deliberately partial per the plan's own scope note — "expanded to the full ported list in 02-02" — not a stub requiring a signature change, per the plan's non-negotiable clause).

## Threat Flags

None. All new surface (`review` CLI verb, git ref handling, manifest writes) is explicitly covered by the plan's own `<threat_model>` STRIDE register (T-02-01 through T-02-06, T-02-SC).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plans 02-02 through 02-05 can now expand `file_select.py` (full extension/exclusion list), `review_coverage.py` (failure paths beyond the tracer's happy path), `diffhunks.py`/`positioning.py` (multi-hunk, multi-file, ambiguous-match cases), and `phase_gate.py` (exit codes 2/3) against an already-proven, production-quality spine.
- `PositionResult` is settled as the review-position contract — no `models.FindingStatus` change needed, removing the phase's single riskiest open question before further plans build on it.
- No blockers.

---
*Phase: 02-diff-pipeline-positioning*
*Completed: 2026-08-17*

## Self-Check: PASSED

All 11 created/modified files confirmed present on disk; both task commit hashes (`77ad9ff`, `912b807`) confirmed present in `git log --all`.
