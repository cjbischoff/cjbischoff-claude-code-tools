---
phase: 02-diff-pipeline-positioning
plan: "02"
subsystem: sec-overlay file selection
tags: [diff-scoping, allowlist, exclusion-reasons]
requires: [diffscope.ChangedFile]
provides: [file_select.partition, file_select.ExcludedFile, file_select.EXCLUSION_REASONS]
affects: [sec_overlay.cli]
tech-stack:
  added: []
  patterns: [fnmatch glob exclusion, closed reason enum via dataclass __post_init__]
key-files:
  created:
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_file_select.py
  modified:
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/file_select.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md
    - plugins/sec-overlay/.claude-plugin/plugin.json
    - plugins/sec-overlay/CHANGELOG.md
decisions:
  - "partition's new keyword parameters (diff_line_counts, binary_paths, max_diff_lines) default to no-op values so cli.py's existing partition(records) call site needs no change."
  - "fnmatch approximates doublestar; the gap (no true zero-or-more-segment **, no brace groups) is named in a ponytail comment and held honest by a parametrized glob test, not silently accepted."
metrics:
  duration: "1 session"
  completed: "2026-08-17"
actuals:
  tokens: 9953
  tasks: 3
  commits: 3
status: complete
---

# Phase 02 Plan 02: Diff Pipeline Positioning — File Selection Summary

Ported open-code-review's 86-extension allowlist and 40 default-exclude globs into
`file_select.py`, then closed the exclusion-reason enum and wired binary-path and
diff-line-size-cap checks into `partition`.

## What Was Built

**Task 1** (commit `7da9981`, completed before this session): ref validation, SHA
pinning, and the exit-code-2 contract in `diffscope.py` and `cli.py`.

**Task 2** (commit `de74299`): `file_select.py` gained the full 86-extension
`ALLOWED_EXTENSIONS` allowlist and the 40-pattern `DEFAULT_EXCLUDE_GLOBS` tuple,
both ported verbatim from open-code-review's JSON allowlist sources. Added
`_normalize_path` to undo git's `core.quotepath` octal-escape quoting of
non-ASCII paths, and `_is_generated` to check a path against the glob set with
`fnmatch.fnmatch`. `tests/test_file_select.py` is new: 57 tests covering the
allowlist, the glob set (each glob checked against its own worked example, not
only through the OR'd `_is_generated` helper), path normalization, and the
empty-input case.

**Task 3** (commit `e9a65a7`): `EXCLUSION_REASONS` is now a closed
`frozenset[str]` of five reasons (`deleted`, `binary`, `generated`,
`not-allowlisted`, `too-large`). `ExcludedFile.__post_init__` raises
`ValueError` on construction if `reason` is outside that set. `partition`
gained three keyword-only parameters — `diff_line_counts`, `binary_paths`,
`max_diff_lines` (default `DEFAULT_MAX_DIFF_LINES = 5000`) — and now checks, in
order, deleted status, the binary-path set, the generated-file globs, the
extension allowlist, then the diff-line cap (`>`, so a file at exactly the cap
is reviewable). Six new tests cover the boundary, binary-precedence-over-
allowlist, the enum rejection, and a six-record fixture walk asserting every
excluded file's reason is in the closed enum.

## Deviations from Plan

None - plan executed exactly as written. Both tasks matched their `<action>`
blocks; all corrections made during execution were to the new test file's
example paths (fnmatch's literal-substring requirement for `**` segments), not
to the delivered logic.

## Known Stubs

None. `grep -rn "TODO\|FIXME\|placeholder\|coming soon\|not available"` against
`file_select.py` and `test_file_select.py` found no matches.

## Verification

- `uv run pytest -q` (from `plugins/sec-overlay/skills/sec-overlay/helpers`):
  911 passed, 2 known environmental failures (`test_bench.py`,
  `test_preflight.py` — missing local bench corpus and rules submodule,
  documented in the skill CLAUDE.md, unaffected by this plan).
- `uv run ruff check sec_overlay/ tests/`: clean.
- `uv run pytest tests/test_review_tracer.py -q`: 6 passed — confirms
  `cli.py`'s existing `partition(records)` call site is unaffected by the new
  keyword-only parameters.

## Self-Check: PASSED

- FOUND: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/file_select.py`
- FOUND: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_file_select.py`
- FOUND commit `7da9981`
- FOUND commit `de74299`
- FOUND commit `e9a65a7`
