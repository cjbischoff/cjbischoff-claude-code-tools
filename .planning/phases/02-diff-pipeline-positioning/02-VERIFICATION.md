---
phase: 02-diff-pipeline-positioning
verified: 2026-08-17T00:00:00Z
status: gaps_found
score: 6/9 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "All reads pin to resolved commit SHAs; a base/head ref that fails to resolve exits 2 (DIFF-01, D-06/D-07)"
    status: failed
    reason: >
      `diffscope.resolve_ref_sha` calls `git rev-parse --verify` with `check=False` and
      returns `completed.stdout.strip()` without ever inspecting `completed.returncode`
      (sec_overlay/diffscope.py:35-49). A well-formed but nonexistent ref (passes the
      `validate_ref` allowlist, fails to resolve in git) silently becomes `""` instead of
      raising `ValueError`. `cli.run_review` only catches `ValueError` around ref
      resolution (cli.py:110-116), so no exception is ever raised for this case.
      `changed_file_records("", "", ...)` then returns zero records, and
      `if not selection.reviewable: return 0` (cli.py:126-127) short-circuits before
      `CoverageManifest.seal()` is ever called — the run reports exit 0 / "success" while
      having validated nothing. Live-reproduced during this verification: `cli.main(["review",
      "--base", "this-branch-does-not-exist-xyz", "--head", "HEAD", "--root", d])` returned
      `0` and wrote no `coverage_manifest.json`. This is code-review finding CR-02
      (02-REVIEW.md), confirmed still present — no commit exists after the 2026-08-17T20:07:31Z
      review timestamp.
    artifacts:
      - path: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/diffscope.py
        issue: "resolve_ref_sha ignores completed.returncode (lines 35-49)"
      - path: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py
        issue: "run_review's empty-reviewable shortcut (line ~126) bypasses seal() and returns 0 even when ref resolution silently failed"
    missing:
      - "resolve_ref_sha must raise ValueError when completed.returncode != 0"
      - "A test with a fake runner returning nonzero for `rev-parse --verify` asserting cli.main returns exit code 2"

  - truth: "The 5000-line diff-size cap and git-binary exclusion actually trigger from the real `sec-overlay review` CLI (DIFF-02/DIFF-03, D-10/D-11)"
    status: failed
    reason: >
      `file_select.partition()` accepts `diff_line_counts=` and `binary_paths=` keyword
      arguments specifically to enforce the size cap and binary exclusion, and
      `diffscope.py` ships `file_diff_line_count()` and `binary_paths()` to supply them.
      `cli.run_review`'s only call site is `selection = partition(records)`
      (cli.py:119) — neither keyword argument is passed. Confirmed by reading the current
      source (unchanged since the 02-REVIEW.md CR-03 finding) and by grepping
      `tests/test_cli.py` for `diff_line_counts`/`binary_paths`: zero matches. Every changed
      file is therefore always treated as zero-diff-lines and non-binary in the actual CLI
      path, regardless of real size or binary content. The module-level behavior
      (`file_select.py`'s own unit tests) is correct; only the production wiring is broken.
    artifacts:
      - path: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py
        issue: "run_review calls partition(records) without diff_line_counts= or binary_paths= (line 119)"
    missing:
      - "run_review must compute diff_line_counts and binary_paths via diffscope's helpers and pass them into partition()"
      - "A test_cli.py case with a fake runner reporting an oversized or binary diff, asserting the file lands in selection.excluded via the review subcommand"

  - truth: "Every `needs-position-review` decline from `phase_gate.review_position_gate` is usable by `report.render_position_review_section` / `report.write_review_ledger` (POS-02, D-13)"
    status: failed
    reason: >
      `report.py`'s `position_reviews` parameter is typed `list[PositionResult]` and both
      consumers (`render_position_review_section`, `write_review_ledger`) dereference
      `PositionResult`-only fields (`claimed_path`, `claimed_line`, `snippet`, `reason`).
      `phase_gate.review_position_gate` appends the raw `finding` object (a `models.Finding`)
      to `declines`, not the `PositionResult` (phase_gate.py:446). `Finding` has none of these
      attributes. Live-reproduced during this verification: constructing a `Finding` whose
      evidence does not match any hunk/file text, running it through
      `review_position_gate`, and passing `declines` into
      `report.render_position_review_section` raised
      `AttributeError: 'Finding' object has no attribute 'snippet'`.
      `test_phase_gate.py:398` (`test_needs_position_review_is_a_decline_not_a_drop_or_keep`)
      locks in the current (incompatible) shape by asserting `declines == [finding]`, and
      `test_report.py`'s `position_reviews=` tests always construct an independent
      `PositionResult` directly — the two paths are never composed in any test. This is
      currently latent (cli.py's `run_review` calls `review_position_gate([], hunks_by_path)`
      with an empty finding list and discards the return value entirely — no finding source
      is wired into review mode yet, and `report.write_report`/`write_review_ledger` are never
      called for review mode today), but the defect will fire the moment a later phase wires a
      real finding source through this gate into the report, which is the explicit purpose
      02-04's objective states ("declines must be impossible to miss"). This is code-review
      finding CR-01 (02-REVIEW.md), confirmed still present.
    artifacts:
      - path: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phase_gate.py
        issue: "review_position_gate appends the raw Finding to declines instead of the PositionResult (line 446)"
      - path: plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_phase_gate.py
        issue: "test at line 398 locks in the incompatible Finding-shaped declines contract"
    missing:
      - "review_position_gate must append `result` (the PositionResult), not `finding`, to declines"
      - "An integration test piping review_position_gate's declines directly into report.write_report(position_reviews=...)"
---

# Phase 2: Diff Pipeline & Positioning Verification Report

**Phase Goal:** Given a base/head ref pair, the harness deterministically identifies every
changed file, tracks per-file review coverage, and confirms exact hunk-anchored finding
locations without ever guessing a line.
**Verified:** 2026-08-17
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Ref arguments validated against `^[A-Za-z0-9._/\-]+$`, leading `-` and empty string rejected before any git subprocess call | ✓ VERIFIED | `diffscope.py:9-30` `_REF_RE`/`validate_ref`; `test_cli.py:36-50` (`test_review_rejects_leading_dash_base_ref_with_exit_2`, `test_review_rejects_empty_base_ref_with_exit_2`) both pass |
| 2 | All reads pin to resolved commit SHAs; an unresolvable ref exits 2, not 0 | ✗ FAILED | See gap 1. `resolve_ref_sha` ignores `returncode`; live-reproduced false exit 0 for a nonexistent ref |
| 3 | `file_select.py` deterministically splits changed files into reviewable/excluded-with-reason; deleted files excluded as `deleted`; closed 5-member reason enum | ✓ VERIFIED | `file_select.py` `partition`/`EXCLUSION_REASONS`; `test_file_select.py` covers deleted/binary/generated/not-allowlisted/too-large at module level |
| 4 | The 5000-line size cap and binary exclusion actually trigger from the real `sec-overlay review` CLI | ✗ FAILED | See gap 2. `cli.py:119` calls `partition(records)` with no `diff_line_counts=`/`binary_paths=`; live source read confirms the CLI's only caller never supplies them |
| 5 | Coverage manifest: one entry per reviewable file, `pending`→`in_review`→`done`\|`failed`; cannot seal `complete` while any entry is `pending`; `partial` names every unreviewed file | ✓ VERIFIED | `review_coverage.py:115-130` `seal()` raises on `pending`/`in_review`/empty; `test_review_coverage.py` (16 tests) all pass; `cli.py`'s partial branch prints `unfinished file: ...` per non-`done` entry |
| 6 | `diffhunks.py` correctly classifies added/context lines from a unified diff, including CRLF and no-newline markers, using stdlib only | ✓ VERIFIED | `diffhunks.py`; `test_diffhunks.py` passes; `grep -c 'import difflib' positioning.py` = 0 confirms no fuzzy stdlib matcher anywhere in the ladder |
| 7 | `positioning.py` confirms a finding via hunk match → whole-file match → cross-file relocation, and declines to `needs-position-review` (never a guessed line) on ambiguity or zero matches | ✓ VERIFIED | `positioning.py` four-rung ladder; `test_positioning.py` passes; code review corroborates ("holds up to direct inspection and its unit tests") |
| 8 | In review mode, `phase_gate.py` drops a finding whose resolved line lies outside every changed hunk with reason `outside-diff`; audit mode is unchanged | ✓ VERIFIED | `phase_gate.py:437-462` `review_position_gate`'s `dropped` list; `git diff HEAD~1 -- sec_overlay/models.py sec_overlay/evidence.py` style checks and `test_findings_gate.py` continue to pass, confirming audit-mode paths untouched |
| 9 | Every `needs-position-review` decline is usable by the report/ledger writers, so a decline is "impossible to miss" once wired to a real finding source | ✗ FAILED | See gap 3. `review_position_gate` returns raw `Finding` objects in `declines`; `report.py` requires `PositionResult`. Live-reproduced `AttributeError: 'Finding' object has no attribute 'snippet'` |

**Score:** 6/9 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `sec_overlay/diffscope.py` | ref validation, SHA resolution, ChangedFile records, diff text/line-count/binary helpers | ⚠️ PARTIAL | All functions exist and are individually correct in isolation, but `resolve_ref_sha` has an unchecked-returncode defect (gap 1) |
| `sec_overlay/file_select.py` | partition into reviewable/excluded with closed reason enum, size cap, binary exclusion | ✓ VERIFIED (module) / ✗ ORPHANED (wiring) | Module correct; not called with the arguments needed to exercise size cap/binary exclusion in production (gap 2) |
| `sec_overlay/review_coverage.py` | coverage manifest state machine, atomic writes, two-state seal | ✓ VERIFIED | `review_coverage.py`, `test_review_coverage.py` |
| `sec_overlay/diffhunks.py` | unified-diff hunk parser | ✓ VERIFIED | `diffhunks.py`, `test_diffhunks.py` |
| `sec_overlay/positioning.py` | never-guess four-rung ladder | ✓ VERIFIED | `positioning.py`, `test_positioning.py` |
| `sec_overlay/phase_gate.py` | review-mode position gate (kept/dropped/declines), audit-mode untouched | ⚠️ PARTIAL | `dropped` path correct; `declines` path returns the wrong type (gap 3) |
| `sec_overlay/report.py` | position-review section + dropped-findings section + review ledger | ⚠️ ORPHANED (for declines) | Functions correct against directly-constructed `PositionResult`; never composed with `review_position_gate`'s actual output in any test or in `cli.py` (which never calls these functions for review mode at all) |
| `sec_overlay/cli.py` `review` verb | exit 0/2/3 contract, wiring every stage together | ✗ STUB (contract) | Exit-2 contract does not fire for unresolvable refs (gap 1); size cap/binary wiring missing (gap 2) |
| `tests/test_review_tracer.py` and per-module test files | tracer + full-behavior tests | ✓ VERIFIED (exist, pass) | 1019 passed / 2 pre-existing environmental failures unrelated to this phase |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `cli.py` review verb | `diffscope.validate_ref` → `resolve_ref_sha` | ref resolution before any diff call | ⚠️ PARTIAL | Format validation wired; existence validation (returncode check) missing — invalid-but-well-formed ref never raises |
| `diffscope.changed_file_records` | `file_select.partition` | `Selection.excluded` (named in output) | ⚠️ PARTIAL | Wired for status-based exclusions (deleted, not-allowlisted); NOT wired for size cap / binary (missing kwargs) |
| `diffscope.file_diff_text` → `diffhunks.parse_hunks` → `positioning.resolve_position` → `phase_gate.review_position_gate` | one path through positioning | ✓ WIRED | Confirmed by `test_review_tracer.py` and direct read of `cli.py`'s per-file loop |
| `phase_gate.review_position_gate` (declines) | `report.render_position_review_section` / `write_review_ledger` | `PositionResult` list | ✗ NOT_WIRED | Type mismatch (gap 3); also never actually called together in `cli.py` — review mode doesn't call `report.write_report`/`write_review_ledger` at all yet |
| `CoverageManifest.seal` | `cli.main` | exit code 0/3 | ✓ WIRED | `cli.py`'s seal-to-exit-code mapping matches `manifest.seal()`'s return value, for the case where `seal()` is actually reached |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Unresolvable-but-well-formed ref exits 2 | `cli.main(["review", "--base", "this-branch-does-not-exist-xyz", "--head", "HEAD", "--root", d])` run live in this repo's checkout | Returned `0`; no `artifacts/coverage_manifest.json` written | ✗ FAIL |
| A `needs-position-review` decline composes with `report.render_position_review_section` | Constructed a `Finding` with unmatched evidence, ran `review_position_gate`, passed `declines` to `report.render_position_review_section` | `AttributeError: 'Finding' object has no attribute 'snippet'` | ✗ FAIL |
| `partition()` size-cap/binary kwargs reach the CLI | `grep -n "diff_line_counts\|binary_paths" sec_overlay/cli.py tests/test_cli.py` | Zero matches in either file | ✗ FAIL |
| Full pytest suite | `uv run pytest -q` | 1019 passed, 2 failed (pre-existing environmental gaps: missing bench corpus, missing semgrep submodule — documented in plugin CLAUDE.md, unrelated to this phase) | ✓ PASS (module-level) |
| `positioning.py` never imports `difflib` | `grep -v '^#' sec_overlay/positioning.py \| grep -c 'import difflib'` | `0` | ✓ PASS |
| Frozen contracts untouched | `git diff HEAD~1 -- sec_overlay/models.py sec_overlay/evidence.py` (spot check against most recent commit) | Empty | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DIFF-01 | 02-01, 02-02 | Ref validation + SHA-pinned reads | ✗ BLOCKED | Gap 1 — unresolvable ref never raises, exit-2 contract does not fire |
| DIFF-02 | 02-01, 02-02 | `ChangedFile` records with path/old_path/status/diff text | ✗ BLOCKED | Records themselves are correct; the size-cap/binary safeguards `diffscope.py` was built to feed `file_select` never reach it (gap 2) |
| DIFF-03 | 02-01, 02-03, 02-05 | `file_select.py` deterministic split; coverage manifest | ⚠️ PARTIAL | Manifest state machine SATISFIED; the exclusion side is BLOCKED by gap 2's CLI wiring |
| DIFF-04 | 02-01, 02-03 | Coverage manifest states + seal contract | ✓ SATISFIED | `review_coverage.py` + tests |
| POS-01 | 02-01, 02-04 | `diffhunks.py` parse/added_line_numbers/line_in_hunk | ✓ SATISFIED | `diffhunks.py` + tests |
| POS-02 | 02-04 | Never-guess positioning ladder + decline visibility in report/ledger (D-13) | ⚠️ PARTIAL | Ladder logic SATISFIED; decline visibility BLOCKED by gap 3 |
| POS-03 | 02-01, 02-05 | Review-mode position gate drops `outside-diff`; audit mode unchanged | ✓ SATISFIED | `phase_gate.py` dropped-list path + audit-mode regression tests |

No orphaned requirements: all 7 IDs declared in Phase 2 plans (`DIFF-01` through `POS-03`) match REQUIREMENTS.md's Phase 2 row exactly, and no additional Phase-2-mapped ID exists in REQUIREMENTS.md beyond these 7.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `sec_overlay/phase_gate.py` | 383-384 | `UNRESOLVED_POSITION_REASON` defined and exported but never assigned anywhere (dead code in `DROP_REASONS`) | ⚠️ Warning | Misleads a future reader into believing this reason is reachable (02-REVIEW.md WR-01) |
| `sec_overlay/cli.py` | 88-89 | `run_review`'s docstring claims batching/exit-codes-2/3 are future work ("arrive in 02-02 and 02-05") while the function body already implements both | ⚠️ Warning | Stale doc will mislead the next maintainer (02-REVIEW.md WR-02) |

No `TBD`/`FIXME`/`XXX` debt markers found in the phase's modified files.

### Human Verification Required

None. All three gaps above were reproduced programmatically (live execution against the actual repo, not just static reading), so no item requires human judgment to resolve.

### Gaps Summary

Every individual module built in this phase (`diffscope`, `file_select`, `review_coverage`,
`diffhunks`, `positioning`, `phase_gate`'s drop path) is internally correct and covered by
passing unit tests — the phase's per-module test suites (1019 passed) back this up, and this
verification's own reading of each module confirms the code review's characterization.

The phase fails at exactly the three seams the code review (02-REVIEW.md, reviewed
2026-08-17T20:07:31Z) identified as critical, and this verification found no commit after that
review that addresses any of them:

1. **CR-02 (gap 1, DIFF-01):** `resolve_ref_sha` never checks the subprocess return code, so
   an unresolvable-but-well-formed ref silently becomes an empty-string SHA rather than
   raising. `cli.run_review`'s ref-resolution try/except only catches `ValueError`, which
   never fires here, and the resulting empty diff short-circuits to exit 0 before
   `CoverageManifest.seal()` is ever reached. Live-reproduced in this verification: a
   nonexistent ref returns exit 0 with no manifest written. This directly contradicts
   ROADMAP.md's Phase 2 Success Criterion 1 ("reads pin to resolved commit SHAs") and the
   `run_review` docstring's own documented "2 on an invalid base/head ref (D-06)" contract.

2. **CR-03 (gap 2, DIFF-02/DIFF-03):** `cli.run_review` calls `file_select.partition(records)`
   with neither `diff_line_counts=` nor `binary_paths=`, so the 5000-line size cap and
   git-binary exclusion — both of which `diffscope.py` ships dedicated helper functions to
   support — can never trigger from the actual `sec-overlay review` command, regardless of
   how large or binary a changed file really is. This is a silent-coverage-hole class defect:
   exactly the failure mode the phase's own threat model (T-02-03) and prohibitions were
   written to prevent, and it is currently live in the only production call site.

3. **CR-01 (gap 3, POS-02):** `phase_gate.review_position_gate` appends the raw `Finding` to
   its `declines` list, but `report.py`'s `position_reviews` parameter is typed
   `list[PositionResult]` and dereferences `PositionResult`-only fields. Live-reproduced
   `AttributeError` when composing the two. This is currently dormant because `cli.py`
   discards `review_position_gate`'s result entirely and never calls `report.write_report`/
   `write_review_ledger` for review mode yet (finding-source wiring is explicitly deferred to
   a later plan) — but the defect is locked in by a test (`test_phase_gate.py:398`) that
   asserts the incompatible shape, so it will not be caught by the existing suite when a later
   phase wires a real finding source through this exact path.

None of these three gaps is deferred to a later phase in ROADMAP.md — Phase 2's own Success
Criteria and the plans' own must_haves claim this exact behavior, not later phases. Phase 3/4
extend rule matching, resume, and scale; they do not re-touch `resolve_ref_sha`,
`partition`'s call site, or `review_position_gate`'s return shape. These are phase-2-owned
defects, not scope handed to Phase 3+.

---

_Verified: 2026-08-17_
_Verifier: Claude (gsd-verifier)_
