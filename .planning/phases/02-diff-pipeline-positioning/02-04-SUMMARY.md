---
phase: "02"
plan: "04"
subsystem: sec-overlay diff review pipeline
tags: [positioning-ladder, never-guess, report, ledger, sec-overlay]
dependency graph:
  requires: [DIFF-03, DIFF-04]
  provides: [POS-01, POS-02]
  affects: [report.py to_markdown wiring (deferred to 02-05)]
tech-stack:
  added: []
  patterns:
    - closed-vocabulary decline reasons instead of confidence scores
    - exact consecutive-line matching only, no fuzzy fallback
    - frozen dataclass __post_init__ structural validation
    - separate JSON ledger artifact to protect a frozen milestone contract
key-files:
  created:
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_positioning.py
  modified:
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/positioning.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phase_gate.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_tracer.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md
    - plugins/sec-overlay/.claude-plugin/plugin.json
    - plugins/sec-overlay/CHANGELOG.md
decisions:
  - The review ledger is a separate artifact (artifacts/review_ledger.json), not a new
    FindingStatus member, because models.py is the frozen milestone contract and a new enum
    member would break the Go port's byte mirror.
  - PositionResult carries the original claimed snippet on every result, including declines, so
    the report can show the claim without a second file lookup.
metrics:
  duration: "one session"
  completed: "2026-08-17"
actuals:
  tokens: 46000
  tasks: 3
  commits: 2
status: complete
---

# Phase 02 Plan 04: Never-guess positioning ladder and decline visibility Summary

Builds the four-rung positioning ladder that confirms or declines a finding's claimed file
location against the diff (POS-01), and surfaces every decline in both the markdown report and a
machine-readable JSON ledger (POS-02, D-13).

## What this plan built

`positioning.py`'s `resolve_position(claimed_path, claimed_line, snippet, hunks_by_path,
file_text_by_path)` runs four rungs in order and stops at the first one that holds: a hunk match
in the claimed file returns `exact`; a whole-file match in the claimed file outside every hunk
returns `relocated`/`whole-file-match`; a match in exactly one other changed file returns
`relocated`/`cross-file-match`; anything else declines with `needs-position-review` and a reason
drawn from a closed vocabulary (`no-snippet`, `no-hunk-match`, `ambiguous-multiple-matches`,
`cross-file-ambiguous`). Two or more matches at any rung decline instead of picking one.
`_match_consecutive` does exact, whitespace-stripped, case-sensitive consecutive-line matching —
no `difflib.SequenceMatcher`, no proximity window, no confidence score anywhere in the module.
`PositionResult` is a frozen dataclass whose `__post_init__` refuses a decline that carries a line
number and refuses a confirmed result missing one; it also carries the original claimed `snippet`
on every result, including declines.

`report.py` gained two additive functions. `render_position_review_section(results)` renders a
`## Position review required` markdown table, one row per declined finding (claimed path, claimed
line, snippet, reason), with pipe characters escaped and newlines collapsed in the snippet cell so
a decline can never corrupt the table into a hidden row; an empty list still renders the heading
plus an explicit none-required line. `write_review_ledger(ws, *, position_reviews, dropped)`
writes `artifacts/review_ledger.json` through the same `_atomic_write` shape `review_coverage.py`
uses, with `position_reviews`/`dropped` keys always present even when both are empty. Neither
function is wired into `to_markdown` or `write_report` yet — plan 02-05 does that wiring once the
drop ledger exists.

`test_positioning.py` (30 tests) covers every rung, every decline reason, rung-order precedence,
determinism, and that a confirmed result never carries an approximate line. `test_report.py`
gained 9 tests (8 match the plan's `-k "position"` filter, one more than the required 6) covering
the section renderer's escaping/collapsing behavior and the ledger writer's round-trip, atomicity
across repeated calls, and empty-input shape.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] Fixed `review_position_gate` signature mismatch**
- **Found during:** Task 2, after `resolve_position` gained its `file_text_by_path` parameter
- **Issue:** `phase_gate.py`'s `review_position_gate` called `resolve_position` positionally with
  the old four-argument signature, breaking on the plan's own signature change.
- **Fix:** added an optional `file_text_by_path` parameter to `review_position_gate` (default
  `None`, which disables the ladder's whole-file and cross-file rungs), threading it through to
  `resolve_position`.
- **Files modified:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phase_gate.py`,
  `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_tracer.py`
- **Commit:** `056c58d`

**2. [Rule 2 - Missing critical functionality] Added `snippet` field to `PositionResult`**
- **Found during:** Task 3, while writing `render_position_review_section`
- **Issue:** the plan's Task 3 done criterion requires the report to show "the claimed path, the
  claimed line, the snippet, and the decline reason" for every decline, but the plan's Artifacts
  section for `PositionResult` (written for Task 1) did not list a `snippet` field — without it,
  Task 3 has no way to render the snippet without a second lookup.
- **Fix:** added a `snippet: str | None = None` field, carried through on every `resolve_position`
  result including declines.
- **Files modified:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/positioning.py`
- **Commit:** `056c58d`

## Verification

- `uv run pytest -q` (from `plugins/sec-overlay/skills/sec-overlay/helpers/`): 991 passed, 2
  failed. Both failures are the pre-existing environmental gaps documented in the skill
  `CLAUDE.md` §1 (gitignored bench corpus, excluded semgrep submodule) — untested by design in a
  clean checkout, not caused by this plan.
- `uv run ruff check sec_overlay/ tests/`: all checks passed.
- `git diff HEAD~3 -- sec_overlay/models.py sec_overlay/evidence.py sec_overlay/coverage.py`:
  0 lines — the frozen milestone contracts are untouched across this plan's full task span.
- `uv run pytest tests/test_report.py tests/test_report_split.py -q`: 56 passed.
- `uv run pytest -k "position" -q`: 8 passed (plan requires 6 or more).
- `uv run pytest -k "empty or none" -q`: 2 passed.
- `inspect.signature(write_review_ledger)` parameters include `dropped` and `position_reviews`.

## Known Stubs

None — `render_position_review_section` and `write_review_ledger` are complete, tested
implementations. They are intentionally not wired into `to_markdown`/`write_report` yet; that
wiring is explicit scope for plan 02-05, not a stub in this plan's own deliverables.

## Threat Flags

None — the new surface is a pure position-matching function and two additive report/ledger
writers operating on data already produced earlier in the pipeline. No new network endpoint, auth
path, or trust boundary is introduced.

## Self-Check: PASSED

- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/positioning.py`: FOUND
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py`: FOUND
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phase_gate.py`: FOUND
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_positioning.py`: FOUND
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report.py`: FOUND
- Commit `056c58d`: FOUND (`git log --oneline --all | grep 056c58d`)
- Commit `aef0a62`: FOUND (`git log --oneline --all | grep aef0a62`)
