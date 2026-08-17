# Phase 1: Baseline Health Verification - Pattern Map

**Mapped:** 2026-08-16
**Files analyzed:** 1 deliberate (01-VERIFICATION.md) + N contingent (whatever gates flag)
**Analogs found:** 1/1 deliberate; contingent fixes classified by category below

This phase is verification-only: it runs three gate families (plugin validate, sec-overlay
pytest/ruff/ty, prek) and fixes whatever they flag. No file list is fixed in advance — CONTEXT.md
confirms "no specific requirements" beyond the gates themselves. This PATTERNS.md therefore maps
categories of likely fix targets to their closest analogs, so the planner/implementer has a
pattern to copy the moment a gate names a file.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|---------------|
| `01-VERIFICATION.md` (new, evidence doc) | test/report | batch (command → exit code → tail) | none in-repo (no prior phase evidence doc); pattern derived from D-05/D-06/D-07/D-08 in CONTEXT.md | no analog |
| Any `sec_overlay/*.py` module flagged by ruff/ty (excluding `models.py`, `evidence.py` — frozen, D-02) | utility/service | transform | `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/normalize.py` | role-match (small, single-purpose transform module — representative style for docstrings/typing) |
| Any `tests/test_*.py` flagged by pytest | test | request-response (call fn, assert output) | `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_normalize.py` | exact (pytest, plain-function style, no fixtures needed for pure-transform modules) |
| `plugins/sec-overlay/skills/sec-overlay/helpers/pyproject.toml` (if ruff/ty config needs adjustment) | config | batch | itself (already read in full) | exact — edit in place, do not add new sections beyond what a lint failure requires |
| `.pre-commit-config.yaml` / `scripts/hooks/*.sh` (if prek fails) | config/utility | event-driven (git hook) | `scripts/hooks/pre-commit-check.sh` (itself, 91 lines) | exact — edit in place |
| `plugins/sec-overlay/CHANGELOG.md` entry for each fix commit | doc | append-only | existing `## 1.37.2 - 2026-08-16` entry block | exact |
| `plugins/sec-overlay/.claude-plugin/plugin.json` version bump | config | CRUD (single field) | itself, current `"version": "1.37.2"` | exact |

## Pattern Assignments

### `01-VERIFICATION.md` (evidence doc)

**No in-repo analog exists.** Build directly from CONTEXT.md's decisions (D-05 through D-08),
which fully specify the structure:

- One version block (ruff, ty, pytest, python, claude CLI versions — D-07)
- One section per gate (VAL-01 plugin validate x2 per D-15, VAL-02 pytest/ruff/ty, VAL-03 prek)
  quoting: exact command run, exit code, decisive tail lines of output (D-06)
- A fix ledger table only if fixes were needed: `gate | failure | fix summary | commit SHA` (D-08)
- Every claim quotes real command output — never asserts without a quoted receipt (see
  "Receipt discipline" in CONTEXT.md's Established Patterns, and the sec-overlay skill's own
  `evidence.is_tool_receipt()` convention at `sec_overlay/evidence.py` — same philosophy: an
  assertion needs a mechanical receipt, not narrative).

### `sec_overlay/*.py` fix (utility/transform module)

**Analog:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/normalize.py` (32 lines)

**Import pattern** (whole file, lines 1-5):
```python
"""Normalize raw detector output: dedup overlapping candidates, assign stable ids."""

from __future__ import annotations

from sec_overlay.models import Finding
```
`from __future__ import annotations` + a one-line module docstring + absolute `sec_overlay.`
imports (never relative `../`) is the house style — match it in any edited module.

**Docstring pattern** (lines 12-21): Google-style, full `Args:`/`Returns:` — required per global
`code-quality.md` for any public function. Match this shape exactly for any new/changed public
function signature.

**Core transform pattern** (lines 22-31): pure function, typed `list[Finding] -> list[Finding]`,
no I/O, no exceptions raised for expected input — matches the "trust internal invariants" rule.
Any repaired module should stay this narrow: pure computation, no new abstractions.

### `tests/test_*.py` fix

**Analog:** `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_normalize.py` (28 lines)

Plain pytest functions (no classes, no fixtures for pure-transform tests), a private `_f(...)`
helper builder for constructing model instances tersely, one behavior asserted per test function,
test names describe behavior (`test_dedup_by_file_line_class_keeps_highest_severity`) — matches
the global TDD naming rule. Per D-03 (CONTEXT.md), only change a test's assertion when it is
provably wrong; otherwise fix production code.

### `pyproject.toml` config fix (if ruff/ty flags a config issue)

**File:** `plugins/sec-overlay/skills/sec-overlay/helpers/pyproject.toml` (already read in full,
630 bytes) — edit in place. Existing exclusions (`extend-exclude = ["fixtures", "rules"]` for ruff,
same for `[tool.ty.src]`) show the pattern for adding a narrow, justified exclusion rather than a
blanket ignore. D-09/D-11 (CONTEXT.md) forbid adding version pins or a `requires-python` floor
this phase — any fix here is config-only, no new dependency.

### `.pre-commit-config.yaml` / hook script fix (if prek fails)

**Analog:** `scripts/hooks/pre-commit-check.sh` (91 lines) — itself. `set -euo pipefail`, explicit
`safe_grep` wrapper distinguishing "no match" (rc 1, expected) from a real failure (rc > 1, fatal),
errors written to stderr with an `error:` / `fix:` two-line pair. Match this error-message shape
for any hook fix.

## Shared Patterns

### Frozen-contract boundary (hard constraint, not a style choice)
**Source:** CONTEXT.md D-02
**Applies to:** every fix in this phase
```
Fixes must not touch models.py or evidence.py (frozen JSON contract, byte-mirrored by a Go port).
If a fix requires a change to a frozen file, stop and escalate to the user.
```
Check `git diff --cached --name-only` before every commit in this phase for these two paths.

### Governance / commit pattern
**Source:** root `CLAUDE.md`, `plugins/sec-overlay/CHANGELOG.md` recent entries, `git log` on
`plugins/sec-overlay/`
```
fix(sec-overlay): <imperative summary, under 50 chars>
```
Recent real examples: `fix(sec-overlay): persist fence baseline, add advance`,
`fix(sec-overlay): split red-team adversary gate path (O-65)`. Every fix touching a sec-overlay
shipping file bumps `plugin.json`'s patch version (D-04, no batching exception) and adds a
`### Fixed` bullet to `plugins/sec-overlay/CHANGELOG.md` in the same commit. A commit that edits
a file under a folder with its own `README.md` (`helpers/`, `agents/`, `references/`) must stage
that folder's `README.md` too — enforced by `scripts/hooks/pre-commit-check.sh`, do not bypass
with `--no-verify` (forbidden repo-wide).

### Known pre-existing environmental failures (not phase-1 defects)
**Source:** `plugins/sec-overlay/CLAUDE.md`, `plugins/sec-overlay/skills/sec-overlay/CLAUDE.md`
Two pytest failures are documented as environment-only, not code defects: missing bench corpus
(`bench/corpus_seed/*.json`, gitignored) trips `test_bench.py::test_seed_corpus_is_valid` and
`test_citations.py::test_all_mapped_ids_exist_in_seed`. Do not "fix" by committing corpus/seed
data — record as environmental in `01-VERIFICATION.md` if still present, per the maintainer notes.

### Test/lint/type-check invocation
**Source:** `plugins/sec-overlay/CLAUDE.md` "Developing the skill"
```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest -q
uv run ruff check sec_overlay/ bench/ tests/
uv run ty check
```
Matches CONTEXT.md D-10 (run pytest via `uv run` from the helpers directory) and D-13 (ruff/ty
scope is the helpers package only).

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `01-VERIFICATION.md` | evidence/report doc | batch | First phase-evidence doc in this repo; build from CONTEXT.md's D-05–D-08 spec directly, no prior example to copy |

## Metadata

**Analog search scope:** `plugins/sec-overlay/skills/sec-overlay/helpers/` (pyproject.toml,
sec_overlay/, tests/), `.pre-commit-config.yaml`, `scripts/hooks/`, `plugins/sec-overlay/CHANGELOG.md`,
`plugins/sec-overlay/.claude-plugin/plugin.json`, git log on `plugins/sec-overlay/`
**Files scanned:** ~10 (pyproject.toml, normalize.py, test_normalize.py, pre-commit-check.sh,
plugin.json, CHANGELOG.md, both plugin CLAUDE.md files, module/test directory listings)
**Pattern extraction date:** 2026-08-16
