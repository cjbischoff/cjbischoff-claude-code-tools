---
phase: 03-rule-matching-review-modes
plan: 01
subsystem: sec-overlay
tags: [python, stdlib-only, rule-matching, llm-verdict-filter, tdd]

requires:
  - phase: 02-diff-scoped-review
    provides: "review_position_gate, diffhunks, file_select, review_coverage — the position-gate tracer this plan composes rule-doc resolution and reflection against"
provides:
  - "rule_glob.resolve_rule_doc — per-language rule-doc resolution by path pattern"
  - "reflection.apply_verdict — retract-only LLM-verdict filter with a code-enforced protected-subject veto"
  - "review --profile security|general CLI flag"
  - "review_ledger.json reflection_retractions/reflection_skipped keys, present even when empty"
affects: [03-rule-matching-review-modes]

actuals:
  tokens: 11600
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Stdlib-only **-aware glob matcher (segment walk + fnmatch.fnmatchcase) instead of raising the Python floor to 3.13 for pathlib.PurePath's whole-path matcher (D-01)"
    - "Retract-only LLM-verdict filter: model output can only remove something the code already submitted, never add/rank/rewrite (mirrors evidence.py's tool-receipt gate discipline)"
    - "Hardcoded frozenset veto (PROTECTED_SUBJECT_CLASSES) that no LLM verdict can override, enforced in code rather than only in the prompt (D-16)"
    - "Never-silent ledger: zero-case rendered explicitly (reflection_retractions: [], reflection_skipped: []) rather than omitted (D-14/D-15)"

key-files:
  created:
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/rule_glob.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/reflection.py
    - plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/default.md
    - plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/python.md
    - plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/README.md
  modified:
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_tracer.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/pyproject.toml
    - plugins/sec-overlay/skills/sec-overlay/helpers/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md
    - plugins/sec-overlay/CHANGELOG.md
    - plugins/sec-overlay/.claude-plugin/plugin.json

key-decisions:
  - "Kept the Python floor at 3.12 (D-01): rule_glob.glob_match hand-rolls a **-aware segment matcher instead of using the 3.13-only pathlib.PurePath.full_match."
  - "reflection.apply_verdict takes an already-parsed verdict mapping — no CLI call, no subprocess, no network import in helper code (D-13); dispatch to the LLM stays in SKILL.md."
  - "Governance completeness (README updates, CHANGELOG, version bump) for Task 1's shipping files was folded into Task 1's single GREEN commit rather than deferred, since the pre-commit hook blocks a commit missing them; Task 2's own governance-only additions got their own commit and version bump."

patterns-established:
  - "A retract-only filter pattern for any future LLM-verdict consumer: accept a parsed verdict, return (kept, retractions), never let the verdict add or reorder."
  - "rules/rule_docs/ as a directory of machine-consumed prompt payloads, distinct from human documentation — adding a doc requires adding its pattern to BUILTIN_PATH_RULE_MAP in the same commit."

requirements-completed: [RULE-01, RULE-05, REV-02]

coverage:
  - id: D1
    description: "A Python file in a diff resolves to the built-in python.md rule doc; an unmatched file falls back to default.md"
    requirement: "RULE-01"
    verification:
      - kind: unit
        ref: "tests/test_review_tracer.py::test_review_python_file_resolves_python_rule_doc"
        status: pass
      - kind: unit
        ref: "tests/test_review_tracer.py::test_review_unmatched_file_resolves_default_rule_doc"
        status: pass
    human_judgment: false
  - id: D2
    description: "expand_braces and glob_match match OCR's ported semantics: non-recursive single-group brace expansion, case-insensitive **-aware segment matching"
    requirement: "RULE-01"
    verification:
      - kind: unit
        ref: "tests/test_review_tracer.py (expand_braces / glob_match unit cases)"
        status: pass
    human_judgment: false
  - id: D3
    description: "reflection.apply_verdict removes exactly a submitted, verdict-named, non-protected finding; an unsubmitted id or a protected-class id is a no-op"
    requirement: "REV-02"
    verification:
      - kind: unit
        ref: "tests/test_review_tracer.py (apply_verdict retraction / unsubmitted-id / protected-class cases)"
        status: pass
    human_judgment: false
  - id: D4
    description: "review_ledger.json carries reflection_retractions and reflection_skipped as present empty lists on a zero-finding run, and report.md renders the ## Reflection retractions heading explicitly"
    requirement: "RULE-05"
    verification:
      - kind: unit
        ref: "tests/test_review_tracer.py::test_review_zero_findings_still_renders_reflection_sections"
        status: pass
    human_judgment: false
  - id: D5
    description: "--profile security is accepted on the review CLI and is the default; the Python floor and D-01 rationale are recorded in pyproject.toml and helpers/README.md"
    verification:
      - kind: unit
        ref: "tests/test_review_tracer.py (profile flag threaded through run_review)"
        status: pass
      - kind: other
        ref: "rg -n 'requires-python' pyproject.toml (D-01 comment present)"
        status: pass
    human_judgment: false

duration: 1h31m
completed: 2026-08-18
status: complete
---

# Phase 03 Plan 01: Rule-Doc Resolution + Reflection Filter Tracer Summary

**Stdlib-only per-language rule-doc glob resolver and a retract-only LLM-verdict filter, wired end to end through `sec-overlay review --profile security` and the review ledger**

## Performance

- **Duration:** 1h31m
- **Started:** 2026-08-18T10:15:43-06:00
- **Completed:** 2026-08-18T11:46:57-06:00
- **Tasks:** 2
- **Files modified:** 14

## Accomplishments
- `rule_glob.py`: brace expansion (`expand_braces`, non-recursive, single-group) + a hand-rolled `**`-aware, case-insensitive segment glob matcher (`glob_match`) resolving a changed file's path to its rule doc via `BUILTIN_PATH_RULE_MAP` (first match wins), falling back to `default.md`. Docs directory resolves from `Path(__file__)`, never cwd (T-03-01).
- `reflection.py`: `apply_verdict` is a retract-only filter — a verdict can only remove a finding the code already submitted, never add, rank, or rewrite one; `PROTECTED_SUBJECT_CLASSES` is a hardcoded veto no verdict can override (D-16, T-03-04).
- `cli.py`'s `run_review` gained `--profile` (`security`/`general`, default `security`), resolves each reviewable file's rule doc, and runs kept findings through `reflection.apply_verdict` inside a per-file `try`/`except` that records a `ReflectionSkip` and fails open (T-03-08).
- `report.py`'s `write_review_ledger`/`write_report` gained `reflection_retractions`/`reflection_skips`, rendered into the same `review_ledger.json` dict (no second artifact file) with an explicit zero-case rendering (D-14/D-15, T-03-05).
- `rules/rule_docs/python.md` and `default.md`: terse imperative checklist rule docs, ported from OCR's format; `rules/rule_docs/README.md` documents the directory and the "add a doc, add its pattern" rule (D-07).
- The Python floor stays at 3.12 (D-01), recorded as a comment above `requires-python` in `pyproject.toml` and in `helpers/README.md`'s module map.

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): failing rule-doc/reflection tests** - `cb2f7d7` (test)
2. **Task 1 (GREEN): wire rule-doc resolve + reflection filter** - `a7c04ee` (feat)
3. **Task 2: record D-01 floor + rule-docs governance** - `e058974` (feat)

**Plan metadata:** committed alongside this SUMMARY (see completion report)

## Files Created/Modified
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/rule_glob.py` - brace expansion, `**`-aware glob match, `resolve_rule_doc`
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/reflection.py` - retract-only verdict filter, protected-subject veto
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py` - `--profile` flag, rule-doc resolution + reflection wired into `run_review`
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py` - reflection keys in the ledger, `## Reflection retractions` section
- `plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/default.md` / `python.md` - built-in rule docs
- `plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/README.md` - directory documentation (D-07)
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_tracer.py` - 9 new tests extending the Phase 2 tracer test
- `plugins/sec-overlay/skills/sec-overlay/helpers/pyproject.toml` - D-01 comment above `requires-python`
- `plugins/sec-overlay/skills/sec-overlay/helpers/README.md`, `helpers/sec_overlay/README.md`, `helpers/tests/README.md` - module-map and test-inventory updates
- `plugins/sec-overlay/CHANGELOG.md`, `plugins/sec-overlay/.claude-plugin/plugin.json` - two entries (1.49.0, 1.50.0), version bumped from 1.48.7 to 1.50.0

## Decisions Made
- Floor stays 3.12; custom `**` matcher instead of the 3.13-only whole-path matcher (D-01).
- Reflection filter takes a pre-parsed verdict mapping — no subprocess/network import in helper code; LLM dispatch stays in `SKILL.md` (D-13).
- Governance updates (READMEs, CHANGELOG, version bump) required for Task 1's shipping files were folded into Task 1's GREEN commit rather than left for Task 2, because the pre-commit hook rejects a commit that changes a folder's tracked files without also staging that folder's README — see Deviations.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Fixed a test fixture path that could never exercise the code under test**
- **Found during:** Task 1 (RED phase, writing Test 2)
- **Issue:** The plan's Test 2 examples a `docs/notes.rst` file resolving to `default.md`. `file_select.py`'s `ALLOWED_EXTENSIONS` allowlist excludes `.rst`, so a `.rst` path is filtered out before it ever reaches `resolve_rule_doc` through the real `run_review` end-to-end path (D-09) — the test as literally specified would pass for the wrong reason (an excluded file never resolving anything) rather than proving the fallback-to-default behavior.
- **Fix:** Changed the fixture path from `docs/notes.rst` to `src/App/Handler.rb` — allowlisted (reaches `rule_glob`) but unmatched by `BUILTIN_PATH_RULE_MAP` (falls back to `default.md`), which is what the test needed to prove.
- **Files modified:** `tests/test_review_tracer.py`
- **Verification:** `test_review_unmatched_file_resolves_default_rule_doc` passes and exercises the real fallback path.
- **Committed in:** `a7c04ee` (Task 1 GREEN commit)

**2. [Rule 2 - Missing Critical] Added README/CHANGELOG/version-bump updates required by the repo's pre-commit hook**
- **Found during:** Task 1 (before commit)
- **Issue:** The repo's `pre-commit-check.sh` hook rejects a commit that changes files inside `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/` and `helpers/tests/` without also staging those folders' `README.md`, and rejects any shipping-file change without a `CHANGELOG.md` entry and a `plugin.json` version bump. Task 1's `<files>` list did not include these (they were assigned to Task 2), but Task 1's own new files (`rule_glob.py`, `reflection.py`) are shipping files that trip the hook immediately.
- **Fix:** Updated `helpers/sec_overlay/README.md` and `helpers/tests/README.md` describing the two new modules and the nine new tests; added a `1.49.0` CHANGELOG entry; bumped `plugin.json` from `1.48.7` to `1.49.0` (minor, `feat`).
- **Files modified:** `helpers/sec_overlay/README.md`, `helpers/tests/README.md`, `CHANGELOG.md`, `plugin.json`
- **Verification:** `git commit` succeeded with the pre-commit hook active (no `--no-verify`).
- **Committed in:** `a7c04ee` (Task 1 GREEN commit)

---

**Total deviations:** 2 auto-fixed (1 test-fixture correction, 1 governance completeness)
**Impact on plan:** Both were required for the commit to be correct and to land at all under the repo's enforced hooks. No scope creep — no behavior beyond the plan's `must_haves` was added.

## Issues Encountered
`uv run ty check` reports 9 `unresolved-attribute: stdout on type R` diagnostics in `tests/test_review_tracer.py`'s `_make_fake_run` fixture helper (lines 71, 73) and in `test_diffscope.py`. These predate this plan, are outside this plan's `<files>` scope (a fixture typing gap unrelated to `rule_glob`/`reflection`), and are unchanged by any commit in this plan — confirmed via `git diff --stat` showing no changes to those lines. Left as-is per the deviation-rules scope boundary (out-of-scope pre-existing issues are not auto-fixed).

## Known Stubs
- `reflection.apply_verdict` is called from `cli.run_review` with an always-empty verdict (`{}`) in this tracer slice. No finding source is wired into `sec-overlay review` yet — plan 03-01 proves the composition point (position gate → reflection filter → ledger), not a live LLM call. The verdict argument becomes non-empty once a later plan in this phase wires an actual review-agent dispatch (`SKILL.md`, per D-13, keeps that dispatch out of helper code). This is intentional scope for the tracer task, not an oversight — see the plan's objective ("prove the architecture end to end on one path").

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The two riskiest architectural seams for Phase 3 — where rule-doc resolution attaches to `run_review`, and how a retract-only reflection filter composes after the position gate — are settled and tested. Later plans in this phase can extend `BUILTIN_PATH_RULE_MAP` with more languages and add the remaining three resolution layers (D-07/D-02) without re-deriving the wiring.
- No blockers. The empty-verdict stub above is the one open item a later plan in this phase must close by wiring a real review-agent verdict into `apply_verdict`.

---
*Phase: 03-rule-matching-review-modes*
*Completed: 2026-08-18*

## Self-Check: PASSED
- FOUND: `.planning/phases/03-rule-matching-review-modes/03-01-SUMMARY.md`
- FOUND: `plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/README.md`
- FOUND commit: `cb2f7d7` (RED)
- FOUND commit: `a7c04ee` (GREEN)
- FOUND commit: `e058974` (Task 2 closeout)
- FOUND commit: `6b75973` (SUMMARY + STATE/ROADMAP/REQUIREMENTS metadata)
