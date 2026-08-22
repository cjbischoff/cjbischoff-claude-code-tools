---
phase: 02-diff-pipeline-positioning
plan: 05
subsystem: sec-overlay/helpers
tags: [review-gate, position-gate, coverage-manifest, exit-codes]
dependency-graph:
  requires: ["02-04"]
  provides:
    - "phase_gate.review_position_gate three-way split (kept, dropped, declined)"
    - "report.render_dropped_findings_section + review ledger dropped entries"
    - "cli.run_review seal-to-exit-code mapping (0 / 2 / 3)"
  affects:
    - "plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py"
tech-stack:
  added: []
  patterns:
    - "Per-file try/except isolates a parse failure into CoverageManifest.fail() instead of crashing the run."
key-files:
  created: []
  modified:
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phase_gate.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_phase_gate.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_cli.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report.py
decisions:
  - "A partial seal has no organic trigger today (file_diff_text and parse_hunks cannot raise on real input), so the per-file try/except in run_review is a defensive isolation mechanism (Rule 2), and every partial-seal test drives it by monkeypatching cli.parse_hunks."
metrics:
  duration: "1 session"
  completed: 2026-08-17
actuals:
  tokens: 88000
  tasks: 3
  commits: 6
status: complete
---

# Phase 02 Plan 05: Position Gate, Drop Ledger, Exit Codes Summary

Review-mode findings now pass through a three-way position gate, every drop and decline is
recorded in both the report and the ledger, and a partial coverage seal exits 3 with each
unfinished file named.

## What This Plan Built

**Task 1 — position gate three-way split** (`6c201a9`, `20e9a54`). `review_position_gate` now
returns three separate lists instead of one: findings inside a changed hunk, findings outside
every hunk (`DroppedFinding`, reason `outside-diff`), and findings the gate could not place
(reason `unresolved-position`, `needs-position-review`). A finding on the line immediately
before or after a hunk boundary drops; the first and last changed lines themselves pass. Audit
mode is untouched — `findings_gate.py` and `phase_gate._line_in_range` show a zero-line diff
against the commit that closed plan 02-04.

**Task 2 — dropped-findings report and ledger** (`58f9904`, `32f3892`). `report.py` renders a
dedicated "Dropped Findings" markdown section from the drop list and writes the same list into
`artifacts/review_ledger.json` under `dropped`. The markdown row count and the ledger entry
count are asserted equal in tests, so neither output can lose a drop the other kept.

**Task 3 — seal-to-exit-code mapping** (`f66d71b`, `a062d29`). `run_review`'s per-file loop
wraps `parse_hunks(file_diff_text(...))` in a `try`/`except Exception`; a failure calls
`manifest.fail(path, note=str(exc))` and moves to the next file instead of crashing the run.
After the loop: seal `complete` (including zero reviewable files) returns 0; seal `partial`
prints one `unfinished file: <path> (state=<state>, note=<note>)` line per non-`done` manifest
entry and returns 3. The pre-existing exit-2 path for an invalid `base`/`head` ref still runs
first, ahead of file selection and manifest work.

## Deviations From Plan

### Auto-fixed Issues

**1. [Rule 2 - missing critical functionality] Added a failure path around `parse_hunks`**
- **Found during:** Task 3
- **Issue:** `CoverageManifest.seal()` can only return `"partial"` if at least one entry
  reaches `failed`, but no code called `manifest.fail(...)` anywhere. `PLAN.md`'s Task 3
  requires exit 3 on a partial seal to be reachable and tested, which is impossible without a
  failure path.
- **Fix:** Wrapped the `parse_hunks`/`file_diff_text` call in `run_review`'s per-file loop in a
  `try`/`except Exception`, calling `manifest.fail(path, note=str(exc))` on failure. Neither
  `file_diff_text` (returns `stdout` unconditionally, `check=False`) nor `parse_hunks` (a pure
  string-parsing loop with every int conversion guarded by `or 1`) raises on real input today —
  this is a defensive isolation boundary for any future failure in that call, not a fix for an
  observed bug. Tests reach the `partial` branch by monkeypatching `cli.parse_hunks` to raise
  for chosen paths.
- **Files modified:** `sec_overlay/cli.py`
- **Commit:** `a062d29`

Or: no other deviations across Tasks 1 and 2 — both matched `PLAN.md`'s `<action>`/`<files>`
specs directly.

## Verification

- `uv run pytest tests/test_phase_gate.py tests/test_report.py tests/test_cli.py -q` — all
  pass, including the 7 new `test_cli.py` tests added for Task 3.
- `uv run pytest -k "exit_0 or exit_2 or exit_3" -q` — 6 tests match, all pass (plan required
  ≥3).
- `uv run pytest -k "partial and (name or print or unfinished)" -q` — 2 tests match, all pass
  (plan required ≥1).
- `rg "max-diff-lines"` and `rg "import logging"` inside `cli.py` — zero matches; the CLI flag
  is deferred to Phase 4 and no logging import was added.
- `pyproject.toml`'s `project.dependencies` — unchanged, stays `[]`.
- `uv run ruff check sec_overlay/ tests/` — clean.
- `uv run ty check sec_overlay/` — clean.
- `uv run pytest -q` (full suite) — 1019 passed, 2 failed. Both failures are the pre-existing
  environmental gaps (missing bench corpus, missing semgrep rules submodule) documented in
  `plugins/sec-overlay/skills/sec-overlay/CLAUDE.md` §1 — not caused by this plan.
- `git diff HEAD~6 -- .../models.py .../evidence.py .../findings_gate.py` — zero lines, across
  the full 6-commit span of this plan. The frozen milestone contracts are untouched.

## Known Stubs

None.

## Threat Flags

None. All new surface in this plan (the position gate's three-way split, the drop ledger, the
exit-3 path) is covered by the plan's own STRIDE register (T-02-18 through T-02-23, T-02-12,
T-02-SC), not newly discovered surface outside it.

## Self-Check: PASSED

- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py` — FOUND
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phase_gate.py` — FOUND
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py` — FOUND
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_cli.py` — FOUND
- Commits `6c201a9`, `20e9a54`, `58f9904`, `32f3892`, `f66d71b`, `a062d29` — all FOUND in
  `git log --oneline --all`.
