---
phase: 01-baseline-health-verification
plan: 02
subsystem: testing
tags: [ruff, ty, pytest, dataclasses, sec-overlay, plugin-governance]

requires:
  - phase: 01-baseline-health-verification (Plan 01)
    provides: the triage ledger (01-VERIFICATION.md) and the approved proceed-as-triaged remediation route
provides:
  - VAL-02 quality gates (ruff, ty) green with zero unaddressed findings against the sec-overlay helpers package
  - VAL-01 and VAL-03 confirmed green at baseline with no fix required
  - Frozen JSON-contract modules (models.py, evidence.py) verified byte-identical to phase start
affects: [02-diff-review-core]

actuals:
  tokens: 10165
  tasks: 2
  commits: 10

tech-stack:
  added: []
  patterns:
    - "dataclasses.replace(base, **kw) over dict-merge-then-Cls(**d) for typed test builders — preserves per-field ty checking that Cls(**dict[str, Any]) bypasses"
    - "Adapter-factory functions (_adapt_dict/_adapt_optional_dict) to unify a dict of differently-typed callables to one Callable[[object], ...] signature, adding real input validation at the same point the type fix lives"
    - "obj.get(key, _MISSING_SENTINEL) over `key in obj` + subscript when ty's in-operator narrowing fails to propagate through an isinstance-narrowed dict"

key-files:
  created: []
  modified:
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/stage_validate.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/workspace.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_citations.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_factcheck_baseline_envelope.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_bench.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_profile.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_rule_matcher.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_bucket_b.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_calibrate.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_patch_status.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_postflight.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_structural_index.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_prefilter.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_wiring.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/fixtures/graph_target/app/db.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/fixtures/graph_target/app/api.py
    - .planning/phases/01-baseline-health-verification/01-VERIFICATION.md

key-decisions:
  - "Stayed on docs/milestone-v5-diff-review rather than opening a new fix/* branch — the plan did not instruct a branch switch and Plan 01's commits already live on this branch."
  - "VAL-03's config-dispositioned row (conventional-commit-msg not exercised by --all-files) got no fix commit, per the maintainer's Remediation Route explicitly carrying it as a documented gap rather than an actionable defect, even though the generic Task 2 template language listed 'config' as an actionable disposition."
  - "Applied deviation Rule 2 (missing critical functionality) in stage_validate.py: the _adapt_dict/_adapt_optional_dict wrappers close a real crash-on-malformed-input gap (previously only _validate_runtime_test guarded against non-dict subagent output) while also satisfying ty — not purely a type-checker appeasement."

patterns-established:
  - "Test-builder dataclasses use dataclasses.replace(base, **kw) instead of dict-merge + Cls(**d), matching the file's Finding/CorpusEntry/ScanProfile precedent."

requirements-completed: [VAL-01, VAL-02, VAL-03]

coverage:
  - id: D1
    description: "ruff check sec_overlay/ bench/ tests/ exits 0 against the helpers package"
    requirement: "VAL-02"
    verification:
      - kind: unit
        ref: "uv run --locked --directory plugins/sec-overlay/skills/sec-overlay/helpers ruff check sec_overlay/ bench/ tests/"
        status: pass
    human_judgment: false
  - id: D2
    description: "ty check exits 0 against the helpers package (161 diagnostics -> 0)"
    requirement: "VAL-02"
    verification:
      - kind: unit
        ref: "uv run --locked --directory plugins/sec-overlay/skills/sec-overlay/helpers ty check"
        status: pass
    human_judgment: false
  - id: D3
    description: "pytest reports zero failures beyond the two documented environmental rows; no test collected count dropped (818 before and after)"
    requirement: "VAL-02"
    verification:
      - kind: unit
        ref: "uv run --locked --directory plugins/sec-overlay/skills/sec-overlay/helpers pytest -q"
        status: pass
    human_judgment: false
  - id: D4
    description: "claude plugin validate . exits 0 at repo root and inside plugins/sec-overlay/; prek run --all-files exits 0"
    requirement: "VAL-01, VAL-03"
    verification:
      - kind: unit
        ref: "claude plugin validate . && (cd plugins/sec-overlay && claude plugin validate .) && prek run --all-files"
        status: pass
    human_judgment: false
  - id: D5
    description: "Frozen JSON-contract modules (models.py, evidence.py) unchanged since phase start"
    requirement: "VAL-02"
    verification:
      - kind: unit
        ref: "git diff --name-only a4731cb..HEAD -- .../models.py .../evidence.py (empty output)"
        status: pass
    human_judgment: false

duration: ~33min (commit span; session included a context-compaction boundary not reflected in wall-clock)
completed: 2026-08-17
status: complete
---

# Phase 1 Plan 2: Baseline Fix — VAL-02 Quality Gates and VAL-01/VAL-03 Verdicts Summary

**Fixed all 4 ruff lint errors and all 161 `ty` type diagnostics in the sec-overlay helpers package (test builders converted to `dataclasses.replace`, two graph-fixture stub bindings, one production adapter-pattern fix in `stage_validate.py`) while leaving the two documented environmental pytest failures and the frozen JSON contract untouched; confirmed VAL-01 and VAL-03 green at baseline with no fix required.**

## Performance

- **Duration:** ~33 min across the 10 fix/docs commits (session spanned a context compaction; total wall-clock time not tracked)
- **Tasks:** 2
- **Files modified:** 24 (18 helpers-package files, 3 sec-overlay plugin metadata files, 3 root-level docs files)

## Accomplishments

- `ruff check sec_overlay/ bench/ tests/` — 4 errors (`C408`x2, `RUF015`, `FLY002`) → 0
- `ty check` — 161 diagnostics across 15 files → 0
- `pytest -q` — 818 tests collected before and after; 816 pass / 2 environmental fail (unchanged, root-caused to gitignored corpus and a missing submodule, not code)
- VAL-01 (`claude plugin validate .`) confirmed exit 0 at repo root and inside `plugins/sec-overlay/`
- VAL-03 (`prek run --all-files`) confirmed exit 0; the one config-dispositioned row left as a documented structural limitation, not a bug
- Frozen JSON-contract modules `models.py` / `evidence.py` confirmed byte-identical to phase start across the full plan diff

## Task Commits

Task 1 (VAL-02 fixes), 7 fix commits (some landed before this session's continuation, all part of this plan's scope):

1. `db095dd` fix(sec-overlay): coerce str path via Workspace __init__
2. `381708c` fix(sec-overlay): pass sets to Exclusions test fixtures
3. `b776e26` fix(sec-overlay): clear last two ruff findings
4. `4fa044c` fix(sec-overlay): use dataclasses.replace in Finding test builders
5. `563079c` fix(sec-overlay): dataclasses.replace for bench/profile builders
6. `7a38879` fix(sec-overlay): narrow Optional results before dereference
7. `de805e3` fix(sec-overlay): use a class for the fake-runner test double
8. `609c421` fix(sec-overlay): adapt stage validators to a common signature
9. `74564a4` fix(sec-overlay): stub graph-fixture names ty flagged undefined

Task 2 (VAL-01/VAL-03 verdict, no code fix required):

10. `db92c76` docs(01): record VAL-01/VAL-03 no-fix-required verdict

**Plan metadata:** (this commit, made immediately after this SUMMARY)

_Note: no TDD red/green pairs — every fix was a type/structural correction to existing test/production code, not new behavior._

## Files Created/Modified

- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/stage_validate.py` — added `_adapt_dict`/`_adapt_optional_dict` to unify `_VALIDATORS`' callable signatures and reject non-dict subagent output with a validation error instead of crashing
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/workspace.py` — fixed prior VAL-02 ty finding (str→Path coercion in `Workspace.__init__`)
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report.py`, `test_citations.py`, `test_factcheck_baseline_envelope.py` — `Finding` test builders converted to `dataclasses.replace`
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_bench.py`, `test_profile.py` — `CorpusEntry`/`ScanProfile` builders converted to `dataclasses.replace`
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_rule_matcher.py`, `test_bucket_b.py`, `test_calibrate.py` — added `is not None` narrowing before dereferencing `X | None` results
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_patch_status.py` — fake-runner rewritten as a class so `ty` can type its `calls` attribute
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_postflight.py`, `test_structural_index.py` — ruff RUF015/FLY002 fixes
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/fixtures/graph_target/app/db.py`, `app/api.py` — added `cursor: Any = None` / `app: Any = None` stub bindings, placed to preserve every `test_graph.py`-pinned line number
- `.planning/phases/01-baseline-health-verification/01-VERIFICATION.md` — appended `## VAL-01 / VAL-03 Remediation` with the re-verified green receipts
- `plugins/sec-overlay/.claude-plugin/plugin.json` — patch-bumped 1.37.4 → 1.37.11 across the fix commits
- `plugins/sec-overlay/CHANGELOG.md` — one `### Fixed` entry per shipping-file fix commit
- Root `README.md`, root `CHANGELOG.md` — updated to reflect Plan 2 completion (repo-level doc-update-guard requirement for the `.planning/`-only commit)

## Decisions Made

- Stayed on `docs/milestone-v5-diff-review` rather than opening a new `fix/*` branch — the plan did not instruct a branch switch and Plan 01's commits already live on this branch.
- VAL-03's `config`-dispositioned row got no fix commit: the maintainer's Remediation Route (`01-VERIFICATION.md` line 121-125, selected `proceed-as-triaged`) explicitly states this row "carries no proposed fix and stays as documented" — overriding the generic Task 2 template language that lists `config` as an actionable disposition category.
- Applied deviation Rule 2 in `stage_validate.py`: the adapter wrappers close a real crash-on-malformed-input gap (previously only `_validate_runtime_test` guarded against non-dict subagent output), not purely a type-checker appeasement.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added dict-shape validation to 5 of 7 `_VALIDATORS` entries in `stage_validate.py`**
- **Found during:** Task 1, fixing the `ty` `unsupported-operator`/type-mismatch diagnostic on `_VALIDATORS`' union-callable signature
- **Issue:** `validate_stage(stage, obj)` accepts untrusted subagent JSON of unknown shape; 6 of 7 registered validators assumed a `dict` and would raise `AttributeError` on non-dict input, while only `_validate_runtime_test` guarded inline
- **Fix:** Added `_adapt_dict`/`_adapt_optional_dict` factories that isinstance-check before delegating, unifying every `_VALIDATORS` value to `Callable[[object], list[str]]` and turning the crash into a normal validation error
- **Files modified:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/stage_validate.py`
- **Verification:** `ty check` clean; `pytest tests/test_stage_validate.py -q` — 5 passed; no behavior change for well-formed dict input
- **Committed in:** `609c421`

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** The fix was required to resolve the `ty` finding in scope; the added validation is a direct, minimal consequence of the type-safety fix, not scope creep.

## Issues Encountered

- Two failed attempts at stubbing `app` in `tests/fixtures/graph_target/app/api.py` before landing on the correct fix: appending `app = None` at the end of the file left the decorator reference (which executes at module-definition time, before the appended line) still unresolved; a subsequent `Write` accidentally introduced an extra blank line, shifting `def handler` off its pinned line 4. Both were caught before commit by re-reading the file and cross-checking against `test_graph.py`'s pinned `file:line` assertions. Resolved by repurposing existing blank-line padding in place (no line-count change) rather than inserting new lines.
- A first pass at running `ruff check` directly against `tests/fixtures/` surfaced an `I001` import-order finding; investigation showed `plugins/sec-overlay/skills/sec-overlay/helpers/pyproject.toml` has `extend-exclude = ["fixtures", "rules"]`, so `fixtures/` is out of scope for the actual Task 1 verify command (`ruff check sec_overlay/ bench/ tests/`) and always was — no fix was needed there; reverted the unnecessary import reorder that would have shifted the fixture's pinned line numbers.
- `ty`'s `in`-operator narrowing failed to propagate through an already-isinstance-narrowed `dict` in `stage_validate.py`, producing a `Top[dict[Unknown, Unknown]].__getitem__(key: Never)` error on `"payloads" in obj` + subscript; fixed with `obj.get("payloads", _MISSING)` using a private sentinel, carefully preserving the "key absent" vs "key present with `None`" distinction that a naive `is not None` rewrite would have collapsed.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

Phase 1 (Baseline Health Verification) is complete: all three gate families (VAL-01, VAL-02, VAL-03) are green, the frozen JSON contract is confirmed untouched, and every fix is committed with its rationale in git history. Phase 2 (diff-review core) can build on this package without inheriting a known defect.

No blockers.

---
*Phase: 01-baseline-health-verification*
*Completed: 2026-08-17*

## Self-Check: PASSED

All 10 claimed commit hashes found in `git log --oneline --all`. All 4 spot-checked claimed
files (`01-02-SUMMARY.md`, `stage_validate.py`, `db.py`, `api.py`, `01-VERIFICATION.md`) exist
on disk.
