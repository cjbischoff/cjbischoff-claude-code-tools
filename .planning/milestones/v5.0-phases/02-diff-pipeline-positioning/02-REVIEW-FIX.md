---
phase: 02-diff-pipeline-positioning
fixed_at: 2026-08-17T21:40:00Z
review_path: .planning/phases/02-diff-pipeline-positioning/02-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report

**Fixed at:** 2026-08-17T21:40:00Z
**Source review:** .planning/phases/02-diff-pipeline-positioning/02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5
- Fixed: 5
- Skipped: 0

## Fixed Issues

### CR-01: `review_position_gate` appends the raw `Finding` to `declines` instead of `PositionResult`

**Files modified:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phase_gate.py`,
`plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_phase_gate.py`,
`plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report.py`,
`plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md`,
`plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md`,
`plugins/sec-overlay/.claude-plugin/plugin.json`, `plugins/sec-overlay/CHANGELOG.md`
**Commit:** `2ab4cb5`
**Applied fix:** `declines.append(finding)` changed to `declines.append(result)` in
`review_position_gate`'s `needs-position-review` branch, so `declines` holds the
`PositionResult` `resolve_position` returned instead of the raw `Finding`. Updated the existing
unit test's assertion shape and added a cross-module integration test proving a real decline
composes directly into `report.write_report(position_reviews=...)` with no adapter. Version
bumped 1.48.0 -> 1.48.1.

### CR-02: `resolve_ref_sha` ignores `completed.returncode`

**Files modified:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/diffscope.py`,
`plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_diffscope.py`,
`plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_cli.py`,
`plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md`,
`plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md`,
`plugins/sec-overlay/.claude-plugin/plugin.json`, `plugins/sec-overlay/CHANGELOG.md`
**Commit:** `b00d0c1`
**Applied fix:** `resolve_ref_sha` now raises `ValueError(f"unresolvable ref: {ref!r}")` when
`completed.returncode != 0`, reusing the existing exit-2 exception path in `run_review`. Added
unit tests at the `diffscope.py` level (success strips stdout; nonzero returncode raises) and an
integration test at the `cli.py` level proving a syntactically valid but nonexistent ref now
exits 2 instead of silently proceeding with an empty SHA. Version bumped 1.48.1 -> 1.48.2.

### CR-03: `run_review` calls `partition(records)` without `diff_line_counts=`/`binary_paths=`

**Files modified:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py`,
`plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_cli.py`,
`plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md`,
`plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md`,
`plugins/sec-overlay/.claude-plugin/plugin.json`, `plugins/sec-overlay/CHANGELOG.md`
**Commit:** `3dbf975`
**Applied fix:** `run_review` now computes `diff_line_counts` (via `file_diff_line_count`, one
call per changed file) and `excluded_binary` (via `binary_paths`) before calling
`partition(records, diff_line_counts=diff_line_counts, binary_paths=excluded_binary)`. Added a
regression test spying on `cli.partition` to capture the returned `Selection` and assert a fake
>5000-line diff lands in `selection.excluded` with reason `too-large`, not `reviewable`.
Corrected a now-stale README sentence claiming the no-kwarg `partition(records)` call "still
works unchanged." Version bumped 1.48.2 -> 1.48.3.

### WR-01: `UNRESOLVED_POSITION_REASON` is defined and exported but never used

**Files modified:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phase_gate.py`,
`plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md`,
`plugins/sec-overlay/.claude-plugin/plugin.json`, `plugins/sec-overlay/CHANGELOG.md`
**Commit:** `a7fdb50`
**Applied fix:** Chose the second option from the review's Fix section — removed the unused
`UNRESOLVED_POSITION_REASON` constant and shrank `DROP_REASONS` to
`frozenset({OUTSIDE_DIFF_REASON})`. Verified no test or other module referenced the removed
symbol (`rg` across `tests/` and `sec_overlay/` returned no other hits). Updated a README
sentence that described `DROP_REASONS` as "the two reasons the gate can emit," which was itself
inaccurate before this fix. No new test needed — dead-code removal, no behavior change; existing
`test_phase_gate.py` (41 tests) still passes. Version bumped 1.48.3 -> 1.48.4.

### WR-02: `run_review`'s docstring claims already-implemented behavior is future work

**Files modified:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py`,
`plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md`,
`plugins/sec-overlay/.claude-plugin/plugin.json`, `plugins/sec-overlay/CHANGELOG.md`
**Commit:** `3285926`
**Applied fix:** Replaced the stale "Wires exactly one changed file through every layer (the
tracer path) — batching over multiple files and exit codes 2/3 arrive in 02-02 and 02-05"
sentence with "Batches over every reviewable changed file and implements exit codes 2 and 3,"
matching the implementation already present in the function body. Kept the still-accurate note
that finding-source integration into `review` mode is future work. Docstring-only change; no new
test needed. Version bumped 1.48.4 -> 1.48.5.

## Skipped Issues

None — all findings were fixed.

## Verification

Full suite run from `plugins/sec-overlay/skills/sec-overlay/helpers` after all five commits:
`uv run --locked pytest -q` -> 1024 passed, 2 failed (both pre-existing, environmental:
`test_bench.py::test_seed_corpus_is_valid` and
`test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd`, per the skill
`CLAUDE.md` — gitignored bench corpus and excluded semgrep submodule). `uv run --locked ruff
check sec_overlay/ tests/` -> all checks passed. Verification ran inside the isolated worktree
(`.claude/worktrees/rf-02-7854-1786998542`, branch `gsd-reviewfix/02-7854`); the cleanup tail
fast-forwards `docs/milestone-v5-diff-review` to the same five commits, so the results are
reproducible from the main checkout after teardown.

---

_Fixed: 2026-08-17T21:40:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
