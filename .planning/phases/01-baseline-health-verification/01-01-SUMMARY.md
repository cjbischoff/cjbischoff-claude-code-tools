---
phase: 01-baseline-health-verification
plan: 01
subsystem: testing
tags: [pytest, ruff, ty, prek, uv, claude-plugin-validate, sec-overlay]

# Dependency graph
requires: []
provides:
  - "01-VERIFICATION.md: tool version block, VAL-01/02/03 receipts, triage ledger, approved remediation route"
  - "Triage ledger dispositioning every non-zero exit code from the delivered baseline (code defect / stale test / config / environmental)"
  - "Confirmed frozen-contract boundary (sec_overlay/models.py, sec_overlay/evidence.py) is untouched by any triaged fix"
affects: [02-baseline-remediation]

actuals:
  tokens: 2846
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Receipt discipline: every gate claim backed by quoted Command/Directory/Exit code/Output (tail) from a real run"
    - "uv run --locked --directory <pkg> <tool> to pin gate invocations to the helpers package without a persistent cd"

key-files:
  created:
    - .planning/phases/01-baseline-health-verification/01-VERIFICATION.md
  modified:
    - README.md
    - CHANGELOG.md

key-decisions:
  - "Recorded the real observed pytest failure (test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd) instead of the stale documented one (test_citations.py::test_all_mapped_ids_exist_in_seed), which now passes — receipts follow the actual run, not prior documentation"
  - "VAL-03's prek receipt cannot show conventional-commit-msg under --all-files (stages: [commit-msg] never fires under --all-files); recorded the honest single-hook receipt plus a config disposition rather than forcing a match to the plan's literal acceptance wording"
  - "Corrected the ty ledger row from a tail-sample claim to a full-output grep (161/161 diagnostics) before presenting the frozen-contract question at Task 3"
  - "Maintainer selected proceed-as-triaged: no triaged fix touches models.py or evidence.py, so Plan 02 executes the ledger's ruff (4 files) and ty (15 files) fixes under normal governance"

requirements-completed: [VAL-01, VAL-02, VAL-03]

coverage:
  - id: D1
    description: "VAL-01 plugin validation receipts (repo root + plugins/sec-overlay, two separate exit codes)"
    requirement: "VAL-01"
    verification:
      - kind: other
        ref: "claude plugin validate . (repo root, exit 0) and claude plugin validate . (plugins/sec-overlay, exit 0 with warnings) — quoted in 01-VERIFICATION.md"
        status: pass
    human_judgment: false
  - id: D2
    description: "VAL-02 sec-overlay quality gate receipts (pytest, ruff, ty) against the helpers package"
    requirement: "VAL-02"
    verification:
      - kind: other
        ref: "uv run --locked --directory plugins/sec-overlay/skills/sec-overlay/helpers {pytest -q, ruff check, ty check} — quoted in 01-VERIFICATION.md"
        status: pass
    human_judgment: false
  - id: D3
    description: "VAL-03 prek hook receipt at the repo root"
    requirement: "VAL-03"
    verification:
      - kind: other
        ref: "prek run --all-files (repo root, exit 0) — quoted in 01-VERIFICATION.md"
        status: pass
    human_judgment: false
  - id: D4
    description: "Triage ledger dispositioning every non-zero exit code, and the maintainer's remediation-route decision"
    verification: []
    human_judgment: true
    rationale: "The remediation-route selection (proceed-as-triaged vs escalate-frozen vs no-fix-needed) is a governance judgment about the frozen-contract boundary, not something a test can classify"

duration: 48min
completed: 2026-08-17
status: complete
---

# Phase 1 Plan 1: Baseline Health Verification Summary

**Ran VAL-01/02/03 against the delivered sec-overlay baseline, recorded 2 pytest failures, 4 ruff errors, and 161 ty diagnostics as real receipts, triaged all of them, and got maintainer approval to fix the code defects under normal governance in Plan 02.**

## Performance

- **Duration:** 48 min
- **Started:** 2026-08-17T05:56:04-06:00 (Task 1 commit)
- **Completed:** 2026-08-17T06:44:40-06:00 (Task 3 commit)
- **Tasks:** 3
- **Files modified:** 3 (`01-VERIFICATION.md` created, `README.md` and `CHANGELOG.md` updated)

## Accomplishments

- Captured VAL-01 receipts: `claude plugin validate .` at the repo root (exit 0) and inside `plugins/sec-overlay/` (exit 0 with 3 informational warnings) — two independent invocations, neither inferred from the other
- Captured VAL-02 receipts: `pytest -q` (exit 1, 2 failed / 816 passed), `ruff check` (exit 1, 4 errors), `ty check` (exit 1, 161 diagnostics) — all three via `uv run --locked` against the sec-overlay helpers package only
- Captured VAL-03 receipt: `prek run --all-files` (exit 0), with a recorded structural finding that `conventional-commit-msg` (a `stages: [commit-msg]` hook) cannot appear in `--all-files` output
- Built a 5-row Triage Ledger dispositioning every failure as `environmental` (2 pytest rows), `code defect` (ruff, ty), or `config` (prek), each with a rationale
- Confirmed against the full 161-line ty diagnostic output (not a tail sample) that no diagnostic names `sec_overlay/models.py` or `sec_overlay/evidence.py` — the frozen JSON-contract boundary (D-02) is untouched by any triaged fix
- Presented the ledger to the maintainer at the Task 3 checkpoint; maintainer selected `proceed-as-triaged`, recorded under a `## Remediation Route` heading in `01-VERIFICATION.md`

## Task Commits

Each task was committed atomically:

1. **Task 1: VAL-01 plugin validation receipts** - `18d01c3` (docs)
2. **Task 2: VAL-02 + VAL-03 receipts and Triage Ledger** - `363cb00` (docs)
3. **Task 3: Ty-row correction + Remediation Route decision** - `85655e6` (docs)

_No plan-metadata commit is listed separately — see "Final commit" note below._

## Files Created/Modified

- `.planning/phases/01-baseline-health-verification/01-VERIFICATION.md` - Tool version block, VAL-01/02/03 gate receipts, Triage Ledger, Remediation Route decision
- `README.md` - `.planning/` Directory Guide row updated to describe the evidence document's growing scope, then the approved remediation route
- `CHANGELOG.md` - Three `### Added` entries under `## Unreleased`: VAL-01 receipts, VAL-02/VAL-03 receipts + ledger, remediation route

## Decisions Made

- Recorded the real observed pytest failure instead of the stale one documented in `01-PATTERNS.md` and both plugin `CLAUDE.md` files (`test_citations.py::test_all_mapped_ids_exist_in_seed` now passes in isolation; `test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd` fails instead, due to a missing `rules/semgrep/` vendored ruleset with no `.gitmodules` registered)
- Did not force the VAL-03 receipt to match the plan's literal "both hook ids" acceptance wording — `prek run --all-files` structurally never fires a `stages: [commit-msg]` hook; recorded the honest single-hook receipt plus a `config` ledger row and a `<flagged_assumptions>` cross-reference for the maintainer to confirm
- Corrected the ty ledger row before presenting Task 3: replaced a tail-sample claim ("None of these files is models.py or evidence.py") with a full-output grep across all 161 diagnostics and all 14 touched files, since Task 3's entire purpose is confirming that exact boundary
- Maintainer selected `proceed-as-triaged` at the Task 3 checkpoint — no ledger row touches the frozen contract, so Plan 02 executes the ruff (4 files) and ty (15 files) fixes under normal governance; the two environmental pytest rows and the one config row stay as documented, unfixed gaps

## Deviations from Plan

None affecting scope or the frozen-contract prohibition — one factual correction and one honest-recording call, both documented above under Decisions Made:

**1. [Rule 1 - factual correction] Ty ledger touched-file list was under-verified before Task 3**
- **Found during:** Task 3 preparation (after Task 2's commit, before presenting the checkpoint)
- **Issue:** The ty row's rationale asserted "None of these files is models.py or evidence.py" based on a spot-check of a handful of `file:line` examples visible in tail output, not the full 161-diagnostic output
- **Fix:** Re-ran `ty check`, greped the complete output for `models.py`/`evidence.py` (zero matches) and for all touched filenames, and rewrote the ledger row with the full 14-file breakdown and diagnostic counts per file
- **Files modified:** `.planning/phases/01-baseline-health-verification/01-VERIFICATION.md`
- **Verification:** `grep -nE 'models\.py|evidence\.py'` against the full `ty check` output returned no matches
- **Committed in:** `85655e6` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 factual correction, Rule 1)
**Impact on plan:** No scope creep; no fix landed, no frozen file touched, no gate weakened. The correction made the Task 3 checkpoint's presented evidence accurate before the maintainer decided on it.

## Issues Encountered

- The plan's own `<flagged_assumptions>` anticipated the VAL-02 environmental-boundary and VAL-03 hook-coverage ambiguities; both resolved without escalation — VAL-02 by recording the real (not documented) failure honestly, VAL-03 by recording the structural `--all-files`/`commit-msg` limitation as a `config` disposition instead of treating it as a broken gate.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 02 (baseline remediation) is scoped and unblocked: fix the 4 ruff lint errors and the ty diagnostics across the 15 files listed in the Triage Ledger, under normal governance (version bump + changelog entry for the sec-overlay plugin, since `skills/sec-overlay/helpers/` files are shipping files). No frozen-contract escalation is needed. The two environmental pytest failures and the VAL-03 config finding are documented, not fixed — Plan 02 should decide whether to leave them as-is or regenerate the missing fixtures (`bench/corpus_seed/` data, `rules/semgrep/` vendored ruleset), consistent with the `no-fix-needed` option's stated cost.

---
*Phase: 01-baseline-health-verification*
*Completed: 2026-08-17*
