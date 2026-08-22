---
phase: 02-diff-pipeline-positioning
verified: 2026-08-19T00:00:00Z
status: passed
score: 9/9 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 6/9
  gaps_closed:
    - "All reads pin to resolved commit SHAs; a base/head ref that fails to resolve exits 2 (DIFF-01, D-06/D-07)"
    - "The 5000-line diff-size cap and git-binary exclusion actually trigger from the real `sec-overlay review` CLI (DIFF-02/DIFF-03, D-10/D-11)"
    - "Every `needs-position-review` decline from `phase_gate.review_position_gate` is usable by `report.render_position_review_section` / `report.write_review_ledger` (POS-02, D-13)"
  gaps_remaining: []
  regressions: []
---

# Phase 2: Diff Pipeline & Positioning Verification Report

**Phase Goal:** Given a base/head ref pair, the harness deterministically identifies every
changed file, tracks per-file review coverage, and confirms exact hunk-anchored finding
locations without ever guessing a line.
**Verified:** 2026-08-19
**Status:** passed
**Re-verification:** Yes — after gap closure (02-REVIEW-FIX.md, 2026-08-17T21:40:00Z)

## Goal Achievement

This is a re-verification. The prior VERIFICATION.md (2026-08-17, `gaps_found`, 6/9) recorded
three failed must-haves, all matching code-review findings CR-01/CR-02/CR-03. 02-REVIEW-FIX.md
claims all three (plus two Warning-level anti-patterns, WR-01/WR-02) were fixed across five
commits. Per instructions, none of that claim was trusted — each of the three previously-failed
items was re-read at the source and live-reproduced against the current codebase in this
session, not just re-run through the existing unit tests.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Ref arguments validated against `^[A-Za-z0-9._/\-]+$`, leading `-` and empty string rejected before any git subprocess call | ✓ VERIFIED | `diffscope.py:9-31` `_REF_RE`/`validate_ref` unchanged from prior pass; `test_review_rejects_leading_dash_base_ref_with_exit_2` and `test_review_rejects_empty_base_ref_with_exit_2` re-run, both pass |
| 2 | All reads pin to resolved commit SHAs; an unresolvable ref exits 2, not 0 (previously FAILED — gap 1 / CR-02) | ✓ VERIFIED | `diffscope.py:35-51`: `resolve_ref_sha` now raises `ValueError(f"unresolvable ref: {ref!r}")` when `completed.returncode != 0`. **Live-reproduced in this session**, not just via the test suite: built a real git repo at `/tmp/vr02/repo`, called `cli.main(["review", "--base", "this-branch-does-not-exist-xyz", "--head", "HEAD", "--root", "/tmp/vr02/repo"])` directly against the real `subprocess.run` (no fake runner) — printed `error: unresolvable ref: 'this-branch-does-not-exist-xyz'` and returned `EXIT 2`. This is the exact scenario the prior verification reproduced as a false exit-0 |
| 3 | `file_select.py` deterministically splits changed files into reviewable/excluded-with-reason; deleted files excluded as `deleted`; closed 5-member reason enum | ✓ VERIFIED | Unchanged since prior pass; `test_file_select.py` (module-level) re-run, all pass |
| 4 | The 5000-line size cap and binary exclusion actually trigger from the real `sec-overlay review` CLI (previously FAILED — gap 2 / CR-03) | ✓ VERIFIED | `cli.py:198-199`: `run_review` now computes `diff_line_counts` (via `file_diff_line_count`, one call per record) and `excluded_binary` (via `binary_paths`) and calls `partition(records, diff_line_counts=diff_line_counts, binary_paths=excluded_binary)`. **Live-reproduced in this session**: injected a fake runner reporting a 5001-line `--unified=0` diff for `big.py`; `cli.run_review` returned exit 0 (vacuous success — no reviewable files) and wrote no `coverage_manifest.json`, i.e. `big.py` never reached the coverage manifest as reviewable. `test_review_excludes_oversized_diff_via_wired_diff_line_counts` (spies on the real `partition` call site) re-run, passes |
| 5 | Coverage manifest: one entry per reviewable file, `pending`→`in_review`→`done`\|`failed`; cannot seal `complete` while any entry is `pending`; `partial` names every unreviewed file | ✓ VERIFIED | Unchanged since prior pass; `test_review_coverage.py` (16 tests) re-run, all pass |
| 6 | `diffhunks.py` correctly classifies added/context lines from a unified diff, including CRLF and no-newline markers, using stdlib only | ✓ VERIFIED | Unchanged since prior pass; `test_diffhunks.py` re-run, passes; `positioning.py` still imports no `difflib` |
| 7 | `positioning.py` confirms a finding via hunk match → whole-file match → cross-file relocation, and declines to `needs-position-review` (never a guessed line) on ambiguity or zero matches | ✓ VERIFIED | Unchanged since prior pass; `test_positioning.py` re-run, passes |
| 8 | In review mode, `phase_gate.py` drops a finding whose resolved line lies outside every changed hunk with reason `outside-diff`; audit mode is unchanged | ✓ VERIFIED | `phase_gate.py:437-463` `review_position_gate`'s `dropped` path unchanged; `test_phase_gate.py`/`test_findings_gate.py` re-run, all pass — audit-mode gate untouched |
| 9 | Every `needs-position-review` decline is usable by the report/ledger writers (previously FAILED — gap 3 / CR-01) | ✓ VERIFIED | `phase_gate.py:445` now does `declines.append(result)` (the `PositionResult`), not the raw `Finding`. **Live-reproduced in this session**: constructed a real `Finding` with evidence matching no hunk/file line, ran it through `review_position_gate`, and piped the returned `declines` directly into `report.render_position_review_section` and `report.write_review_ledger` — both succeeded with no `AttributeError`, and the written `review_ledger.json` contains a `position_reviews` entry with `claimed_path`/`claimed_line`/`snippet`/`reason` fields populated. Additionally confirmed `cli.run_review` now actually calls `write_report(ws, dropped=dropped, position_reviews=declines, ...)` (cli.py:322-330) — in the prior pass this call did not exist at all for review mode; it is now present and unconditional (including the zero-drop/zero-decline case) |

**Score:** 9/9 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `sec_overlay/diffscope.py` | ref validation, SHA resolution (raising on unresolvable), ChangedFile records, diff text/line-count/binary helpers | ✓ VERIFIED | `resolve_ref_sha` now checks `completed.returncode`; all helper functions unchanged and correct |
| `sec_overlay/file_select.py` | partition into reviewable/excluded with closed reason enum, size cap, binary exclusion | ✓ VERIFIED | Module correct; now actually invoked with `diff_line_counts=`/`binary_paths=` from `cli.py`, closing the prior wiring gap |
| `sec_overlay/review_coverage.py` | coverage manifest state machine, atomic writes, two-state seal | ✓ VERIFIED | Unchanged; tests pass |
| `sec_overlay/diffhunks.py` | unified-diff hunk parser | ✓ VERIFIED | Unchanged; tests pass |
| `sec_overlay/positioning.py` | never-guess four-rung ladder | ✓ VERIFIED | Unchanged; tests pass |
| `sec_overlay/phase_gate.py` | review-mode position gate (kept/dropped/declines), audit-mode untouched | ✓ VERIFIED | `declines` now correctly holds `PositionResult`; dead `UNRESOLVED_POSITION_REASON` constant removed (WR-01 fixed); `DROP_REASONS` shrunk to the one real reason |
| `sec_overlay/report.py` | position-review section + dropped-findings section + review ledger | ✓ VERIFIED | Now actually composed with `review_position_gate`'s real output, both in a new integration test and live-reproduced in this session |
| `sec_overlay/cli.py` `review` verb | exit 0/2/3 contract, wiring every stage together | ✓ VERIFIED | Exit-2 fires for unresolvable refs (live-reproduced); size-cap/binary wiring present; `write_report` now called for every review run; stale docstring (WR-02) corrected to match the implemented behavior |
| `tests/` per-module test files | tracer + full-behavior tests | ✓ VERIFIED (exist, pass) | 1176 passed / 2 pre-existing environmental failures unrelated to this phase (documented in plugin CLAUDE.md: gitignored bench corpus, excluded semgrep submodule) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `cli.py` review verb | `diffscope.validate_ref` → `resolve_ref_sha` | ref resolution before any diff call | ✓ WIRED | Both format validation and existence validation (returncode check) now raise `ValueError`, caught by `run_review`'s `except ValueError` and mapped to exit 2 |
| `diffscope.changed_file_records` | `file_select.partition` | `Selection.excluded` (named in output) | ✓ WIRED | Now wired for status-based exclusions AND size cap / binary — `cli.py:198-199` computes and passes both kwargs |
| `diffscope.file_diff_text` → `diffhunks.parse_hunks` → `positioning.resolve_position` → `phase_gate.review_position_gate` | one path through positioning | ✓ WIRED | Confirmed by `test_review_tracer.py` and direct read of `cli.py`'s per-file loop |
| `phase_gate.review_position_gate` (declines) | `report.render_position_review_section` / `write_review_ledger` | `PositionResult` list | ✓ WIRED | Type now matches; live-reproduced composition with no adapter; `cli.py:322-330` now actually calls `write_report(..., position_reviews=declines, ...)` unconditionally for every review run |
| `CoverageManifest.seal` | `cli.main` | exit code 0/3 | ✓ WIRED | Unchanged; `manifest.seal()`'s return value still maps correctly to exit 0/3 |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Unresolvable-but-well-formed ref exits 2 (real git subprocess, no fake) | `cli.main(["review", "--base", "this-branch-does-not-exist-xyz", "--head", "HEAD", "--root", "/tmp/vr02/repo"])` against a real freshly-init'd repo | `error: unresolvable ref: 'this-branch-does-not-exist-xyz'` / `EXIT 2` | ✓ PASS |
| Oversized diff never reaches the coverage manifest as reviewable | Injected fake runner reporting 5001-line `--unified=0` diff for `big.py`; called `cli.run_review` directly | `EXIT 0`; no `coverage_manifest.json` written (vacuous success, `big.py` excluded before manifest.add) | ✓ PASS |
| A `needs-position-review` decline composes with `report.render_position_review_section`/`write_review_ledger` | Constructed a `Finding` with unmatched evidence, ran `review_position_gate`, passed `declines` to both report functions | `render_position_review_section` returned a non-empty section; `write_review_ledger` wrote `review_ledger.json` with a populated `position_reviews` entry (`claimed_path`, `claimed_line`, `snippet`, `reason`) — no `AttributeError` | ✓ PASS |
| Targeted regression tests for the three closed gaps | `uv run pytest -q -k "test_resolve_ref_sha_raises_on_nonzero_returncode or test_review_exit_2_on_unresolvable_but_valid_ref or test_review_excludes_oversized_diff_via_wired_diff_line_counts or needs_position_review"` | 6 passed | ✓ PASS |
| Full pytest suite (run once) | `uv run --locked pytest -q` | 1176 passed, 2 failed (pre-existing environmental: missing bench corpus, missing semgrep submodule — documented, unrelated to this phase) | ✓ PASS (module-level) |
| Lint clean | `uv run --locked ruff check sec_overlay/ tests/` | All checks passed | ✓ PASS |
| WR-01 dead code removed | `grep -n "UNRESOLVED_POSITION_REASON" sec_overlay/phase_gate.py` | No matches | ✓ PASS |
| WR-02 stale docstring corrected | Read `cli.py:104` docstring | "Batches over every reviewable changed file and implements exit codes 2 and 3." — matches implementation | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DIFF-01 | 02-01, 02-02 | Ref validation + SHA-pinned reads | ✓ SATISFIED | Gap 1 closed — unresolvable ref now raises and exits 2, live-reproduced |
| DIFF-02 | 02-01, 02-02 | `ChangedFile` records with path/old_path/status/diff text | ✓ SATISFIED | Records correct; the size-cap/binary safeguards now reach `file_select` from the real CLI (gap 2 closed) |
| DIFF-03 | 02-01, 02-03, 02-05 | `file_select.py` deterministic split; coverage manifest | ✓ SATISFIED | Manifest state machine and exclusion wiring both confirmed |
| DIFF-04 | 02-01, 02-03 | Coverage manifest states + seal contract | ✓ SATISFIED | `review_coverage.py` + tests, unchanged and passing |
| POS-01 | 02-01, 02-04 | `diffhunks.py` parse/added_line_numbers/line_in_hunk | ✓ SATISFIED | `diffhunks.py` + tests, unchanged and passing |
| POS-02 | 02-04 | Never-guess positioning ladder + decline visibility in report/ledger (D-13) | ✓ SATISFIED | Ladder logic unchanged; decline visibility now works end to end (gap 3 closed) |
| POS-03 | 02-01, 02-05 | Review-mode position gate drops `outside-diff`; audit mode unchanged | ✓ SATISFIED | `phase_gate.py` dropped-list path + audit-mode regression tests, unchanged and passing |

No orphaned requirements: all 7 IDs declared across Phase 2 plans (`DIFF-01` through `POS-03`)
match REQUIREMENTS.md's Phase 2 row exactly (REQUIREMENTS.md lines 27-51, 190-196, all marked
`[x]`/`Complete`), and no additional Phase-2-mapped ID exists beyond these 7.

### Anti-Patterns Found

None in the current source. The two Warning-level findings from the prior verification
(`UNRESOLVED_POSITION_REASON` dead code at `phase_gate.py:383-384`; stale `run_review` docstring
at `cli.py:88-89`) are both confirmed fixed (WR-01, WR-02 above). No `TBD`/`FIXME`/`XXX` debt
markers found in any phase-modified file (`diffscope.py`, `cli.py`, `phase_gate.py`,
`file_select.py`, `report.py`, `review_coverage.py`, `positioning.py`, `diffhunks.py`).

### Human Verification Required

None. All three previously-failed items were reproduced programmatically against the current
codebase in this session (real git subprocess for gap 1, direct function composition for gaps 2
and 3), not merely re-read from the fix report or re-run through pre-existing tests.

### Gaps Summary

None remaining. All three gaps from the 2026-08-17 verification are closed and independently
live-reproduced in this session, not just accepted from 02-REVIEW-FIX.md's narrative:

1. **CR-02 (DIFF-01) — closed.** `resolve_ref_sha` now raises `ValueError` when
   `completed.returncode != 0`. Reproduced against a real repo and a real `subprocess.run` call
   (no fake runner): a nonexistent ref now exits 2 with a clear error, matching ROADMAP.md
   Success Criterion 1.
2. **CR-03 (DIFF-02/DIFF-03) — closed.** `run_review` now computes `diff_line_counts` and
   `binary_paths` and passes both into `partition()`. Reproduced with an injected 5001-line diff:
   the oversized file is excluded before it ever reaches the coverage manifest.
3. **CR-01 (POS-02) — closed.** `review_position_gate` now appends the `PositionResult`, not the
   raw `Finding`, to `declines`. Reproduced end to end: a real decline composes directly into
   `report.render_position_review_section` and `write_review_ledger` with no adapter and no
   `AttributeError`. `cli.run_review` now also actually calls `write_report` for every review run
   (previously it discarded `review_position_gate`'s result entirely), so this path is no longer
   dormant — it fires on every real invocation.

No regressions found: every truth verified as passing in the prior report (module-level
`file_select`, `review_coverage`, `diffhunks`, `positioning`, `phase_gate`'s dropped path, ref
format validation) was re-checked against the current source and re-run through its test suite;
all still hold. The full suite's two failures are the same pre-existing environmental gaps noted
in both the prior verification and 02-REVIEW-FIX.md (gitignored bench corpus, excluded semgrep
submodule) — unrelated to this phase and unchanged in count.

All five Phase 2 ROADMAP Success Criteria hold against the current codebase. Phase goal achieved.

---

_Verified: 2026-08-19_
_Verifier: Claude (gsd-verifier)_
