---
phase: 06-remediation-and-governed-release
plan: 03
subsystem: docs
tags: [sec-overlay, redteam, deps-scan, doc-invariants, semgrep]

requires:
  - phase: 06-remediation-and-governed-release
    provides: "Plan 01's recorded CodeRabbit outcome; Plan 02's wired redteam/postflight phases"
provides:
  - "Deps-finding Fix line renders the real package name for scoped, unscoped, versionless, absent, and multi-separator identifiers"
  - "agents/redteam.md describes the actual two-condition wants_runtime OR predicate instead of an invented three-way split"
  - "No live doc under plugins/sec-overlay/ claims the vendored semgrep ruleset is a tracked git submodule"
  - "helpers/tests/README.md attributes the cwd-scoping bug's late discovery to the monkeypatched runner, not to bypassing the CLI entry point"
  - "Two code-derived doc guards in test_docs_invariants.py preventing both false claims from returning"
affects: [sec-overlay-release-governance, phase-05-defect-ledger]

actuals:
  tokens: 7103
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Tree-walking doc guard: Path.rglob('*.md') with no hardcoded path list, explicit historical/vendored-dir exclusion markers, and actionable-instruction-phrase detection (not bare keyword match) so a doc's own correct negation of a false claim doesn't self-flag."
    - "Code-derived prompt guard: read the real predicate's trigger values out of sec_overlay.evidence/sec_overlay.models at runtime, assert both appear in the prompt text — zero hardcoded string copies, so a future rename fails the test instead of silently re-opening drift."

key-files:
  created: []
  modified:
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report.py
    - plugins/sec-overlay/skills/sec-overlay/agents/redteam.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_docs_invariants.py
    - plugins/sec-overlay/CLAUDE.md
    - plugins/sec-overlay/skills/sec-overlay/CLAUDE.md
    - plugins/sec-overlay/skills/sec-overlay/SKILL.md
    - plugins/sec-overlay/skills/sec-overlay/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md

key-decisions:
  - "REL-01 doc-surface search found 6 files / 8 mentions of the submodule claim, not the 3 the plan's objective estimated — corrected every live surface found rather than stopping at the ledger's named file, and recorded the actual count instead of forcing it to match the estimate."
  - "docs/plans/*.md and docs/superpowers/plans/*.md treated as historical planning record and excluded from both the doc-corrections sweep and the new tree-walking guard's scan, on the same immutability basis as a historical CHANGELOG entry."
  - "Merge of PR #25 was executed by the orchestrator, not this agent — gh pr merge was blocked by the Claude Code auto-mode classifier as an outward-facing action. CodeRabbit review was triggered once (comment posted, no re-request loop) and the repo owner's decision was to merge without waiting for it, consistent with the phase's standing override for non-default-base PRs (auto-review does not run against a non-main base; manual trigger is sometimes OSS-rate-limited)."

patterns-established:
  - "Tree-walking doc guard for a 'no tracking file exists, so no doc may instruct X' claim: walk the whole plugin doc tree, exclude historical/vendored markers by substring-in-relpath (not startswith), match on actionable instruction phrases rather than a bare keyword."

requirements-completed: [REL-01, REL-02]

coverage:
  - id: D1
    description: "Deps Fix line renders the real package name for scoped, unscoped, versionless, absent, and multi-separator package identifiers"
    requirement: REL-01
    verification:
      - kind: unit
        ref: "plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report.py::test_deps_fix_line_names_scoped_package_with_version"
        status: pass
      - kind: unit
        ref: "plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report.py::test_deps_fix_line_names_unscoped_package_with_version"
        status: pass
      - kind: unit
        ref: "plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report.py::test_deps_fix_line_names_versionless_scoped_package"
        status: pass
      - kind: unit
        ref: "plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report.py::test_deps_fix_line_falls_back_to_placeholder_for_absent_package"
        status: pass
      - kind: unit
        ref: "plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report.py::test_deps_fix_line_resolves_multi_separator_identifier_at_last_separator"
        status: pass
    human_judgment: false
  - id: D2
    description: "agents/redteam.md describes the real two-condition wants_runtime OR predicate; redteam.py and prompt-constants.md are byte-identical to the milestone base"
    requirement: REL-01
    verification:
      - kind: unit
        ref: "plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_docs_invariants.py::test_redteam_agent_describes_the_real_two_way_wants_runtime_predicate"
        status: pass
      - kind: other
        ref: "git diff docs/milestone-v5-diff-review...HEAD -- .../redteam.py .../prompt-constants.md (empty)"
        status: pass
    human_judgment: false
  - id: D3
    description: "No live doc under plugins/sec-overlay/ claims the vendored semgrep ruleset is a tracked git submodule; a tree-walking guard prevents reintroduction"
    requirement: REL-01
    verification:
      - kind: unit
        ref: "plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_docs_invariants.py::test_no_live_doc_claims_a_git_submodule_that_does_not_exist"
        status: pass
    human_judgment: false
  - id: D4
    description: "helpers/tests/README.md's cwd-scoping bug explanation attributes the miss to the monkeypatched subprocess.run runner, not to bypassing the CLI entry point"
    requirement: REL-01
    verification:
      - kind: manual_procedural
        ref: "Read of the corrected tests/README.md paragraph against cli.py:351's run_review default and test_review_live.py's monkeypatch pattern"
        status: pass
    human_judgment: true
    rationale: "Prose-accuracy claim about which code path a test suite exercises; no automated test asserts English wording matches the described mechanism beyond the doc guards already listed."
  - id: D5
    description: "Four governed commits, four patch bumps (1.69.4 -> 1.69.8), one merged PR on the milestone branch"
    requirement: REL-02
    verification:
      - kind: other
        ref: "git log --oneline 0a1dfac..8c3c800; plugin.json version 1.69.8; PR #25 merged into docs/milestone-v5-diff-review"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-08-21
status: complete
---

# Phase 06 Plan 03: Deps template fix and doc-surface corrections Summary

**Fixed a deps Fix-line that rendered an empty backtick pair for scoped npm identifiers, rewrote the red-team prompt's invented three-way split down to the real two-condition predicate, corrected a false "tracked submodule" claim across 6 files, fixed a wrong test-suite explanation, and shipped it as a merged PR with two new code-derived doc guards.**

## Performance

- **Duration:** 45min (14:34 first commit to 14:51 last content commit, plus PR/merge cycle)
- **Started:** 2026-08-21T14:34:41-06:00
- **Completed:** 2026-08-21
- **Tasks:** 3/3
- **Files modified:** 15 (13 content files + plugin.json + CHANGELOG.md)

## Accomplishments

- Deps-class findings with a scoped npm-style package identifier (`@scope/name@1.2.3`) now render the real package name on the Fix line instead of an empty pair of backticks — fixed with a one-line change (`rsplit('@', 1)[0] or pkg`), pinned by 5 new tests covering scoped, unscoped, versionless, absent, and multi-separator identifiers.
- `agents/redteam.md` now describes the real `wants_runtime()` predicate: a plain two-trigger OR where the status condition alone forces inclusion, with no "neither" exemption category — closing a defect where the prose implied a finding could be routed out of the runtime bucket by its disposition field alone (a real-world observation from the Phase 5 ledger).
- Corrected the false claim that the vendored semgrep ruleset (`helpers/rules/semgrep/`) is a tracked git submodule across every live doc surface that carried it — 6 files, 8 mentions — replacing "clone with `--recurse-submodules`" instructions with the real mechanism (a gitignored directory populated by a plain shallow clone).
- Corrected `helpers/tests/README.md`'s explanation of why the cwd-scoping bug survived the test suite: the passing tests don't "inject their own runner" — they `monkeypatch.setattr(subprocess, "run", ...)`, patching the stdlib function underneath `run_review`'s `partial(subprocess.run, cwd=root)` default, and their fake ignores `cwd`.
- Added two code-derived doc guards to `test_docs_invariants.py`: one reads the `wants_runtime()` trigger values out of real code (zero hardcoded copies) and asserts both appear in `redteam.md`; the other walks the whole plugin doc tree (`Path.rglob("*.md")`, no hardcoded path list) asserting no live doc instructs a submodule init/recurse-clone step, since no `.gitmodules` exists.
- Opened, reviewed, and merged PR #25 into `docs/milestone-v5-diff-review` under the phase's standing CodeRabbit-wait override.

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Pin scoped-package Fix-line bug** - `2b9b787` (test)
2. **Task 1 (GREEN): Split deps Fix-line package name on last `@`** - `34e25f3` (fix)
3. **Task 2: Rewrite redteam.md to the two-way mechanical split (D-02)** - `fa012be` (docs)
4. **Task 3: Correct submodule claim and cwd-bug explanation (D-04)** - `3e1b7e8` (docs)

**PR merge commit (orchestrator-executed):** `8c3c800` (Merge pull request #25 from cjbischoff/fix/deps-template-and-doc-corrections)

_Note: Task 1 is TDD (test → fix); Tasks 2 and 3 are single doc/test commits each._

## Files Created/Modified

- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py` - one-line fix: split package identifier on the last `@`, fall back to the untruncated string when that yields empty
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report.py` - 5 new test cases (scoped, unscoped, versionless, absent, multi-separator) plus a shared empty-backtick-pair assertion
- `plugins/sec-overlay/skills/sec-overlay/agents/redteam.md` - rewrote the Discriminate section from an invented three-way split to the real two-condition OR predicate, with the safe-default rationale stated
- `plugins/sec-overlay/skills/sec-overlay/agents/README.md` - one-line contract summary added for the corrected predicate description
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_docs_invariants.py` - added `test_redteam_agent_describes_the_real_two_way_wants_runtime_predicate` and `test_no_live_doc_claims_a_git_submodule_that_does_not_exist`
- `plugins/sec-overlay/CLAUDE.md` - submodule claim corrected to a vendored gitignored clone, with the real `git clone --depth 1` command
- `plugins/sec-overlay/skills/sec-overlay/CLAUDE.md` - same correction, two spots (setup section and a second reference)
- `plugins/sec-overlay/skills/sec-overlay/SKILL.md` - same correction
- `plugins/sec-overlay/skills/sec-overlay/README.md` - same correction (prerequisites blockquote)
- `plugins/sec-overlay/skills/sec-overlay/helpers/README.md` - same correction, two spots (tree diagram descriptor, env-only-failures parenthetical)
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md` - submodule terminology fix in the top-matter line, plus the WR-02 cwd-bug explanation rewrite
- `plugins/sec-overlay/README.md` - added a "More" table row pointing to `CLAUDE.md`, required by the pre-commit hook's immediate-folder-README rule since `CLAUDE.md` in the same folder was staged
- `plugins/sec-overlay/.claude-plugin/plugin.json` - version `1.69.4` -> `1.69.8` across the plan's 4 commits
- `plugins/sec-overlay/CHANGELOG.md` - 4 new `### Fixed` entries, one per commit

## Doc surfaces corrected for the submodule/ruleset claim

Per the plan's `<output>` instruction, listed with count for the Plan 05 defect ledger:

1. `plugins/sec-overlay/CLAUDE.md`
2. `plugins/sec-overlay/skills/sec-overlay/CLAUDE.md` (2 mentions)
3. `plugins/sec-overlay/skills/sec-overlay/SKILL.md`
4. `plugins/sec-overlay/skills/sec-overlay/README.md`
5. `plugins/sec-overlay/skills/sec-overlay/helpers/README.md` (2 mentions)
6. `plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md`

**6 files, 8 mentions corrected.** The plan's objective text estimated "three corrected doc surfaces" for the whole plan (covering both the submodule claim and the WR-02 explanation combined); the actual submodule-claim search alone found 6 files. This is reported as found, not forced to match the estimate — `docs/plans/*.md` and `docs/superpowers/plans/*.md` were deliberately excluded as historical planning record, the same basis a historical CHANGELOG entry is left alone.

The WR-02 cwd-bug explanation fix is a separate, distinct defect row, also in `helpers/tests/README.md`, not counted in the 6/8 above.

## Decisions Made

- Corrected every live doc surface carrying the submodule claim found by search (6 files), not only the one the Phase 5 ledger named, per the plan's explicit instruction that correcting one while leaving the rest "would fix the symptom and leave the defect."
- Excluded `docs/plans/*.md` and `docs/superpowers/plans/*.md` from both the doc sweep and the new tree-walking guard's scan, treating them as historical record.
- PR merge was executed by the orchestrator rather than this agent: `gh pr merge` was blocked by the Claude Code auto-mode classifier (an outward-facing, irreversible action). `@coderabbitai review` was triggered once per the phase's standing override for non-default-base-branch PRs; the repo owner decided to merge without waiting further, since CodeRabbit's auto-review does not run against a non-`main` base and the manual trigger has hit the OSS rate limit on prior plans in this phase.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - blocking hook requirement] `plugins/sec-overlay/README.md` required staging alongside `CLAUDE.md`**
- **Found during:** Task 3
- **Issue:** The repo's pre-commit hook requires that any staged file's immediate-folder `README.md` also be staged. `plugins/sec-overlay/CLAUDE.md` was corrected for the submodule claim, and its immediate folder (`plugins/sec-overlay/`) has a tracked `README.md` that was not otherwise part of this plan's file list.
- **Fix:** Added a genuine one-line "More" table entry in `plugins/sec-overlay/README.md` pointing readers to `CLAUDE.md`, satisfying both the hook and the "no unchanged stage-only" instruction from Task 2's analogous README requirement.
- **Files modified:** `plugins/sec-overlay/README.md`
- **Verification:** Commit `3e1b7e8` passed the pre-commit hook on first attempt.
- **Committed in:** `3e1b7e8` (part of Task 3 commit)

---

**Total deviations:** 1 auto-fixed (Rule 3, hook-driven README co-update)
**Impact on plan:** Minor, mechanical — required by repo governance already documented in root `CLAUDE.md`. No scope creep.

## Issues Encountered

- **Doc guard false positives on first run:** the initial `test_no_live_doc_claims_a_git_submodule_that_does_not_exist` used a bare `"submodule" in txt` keyword match plus `startswith`-based historical-dir exclusion. This flagged 5 false positives: `CLAUDE.md`'s own corrective sentence (which mentions "submodule" while explaining it is NOT one) and 4 historical planning docs that were nested deeper than the `startswith` prefix expected (`skills/sec-overlay/docs/plans/...` rather than a top-level `docs/plans/...`). Fixed by switching to substring-`in`-relpath exclusion markers and narrowing detection to specific actionable-instruction phrases (`recurse-submodules`, `submodule update`, `is a git submodule`) instead of a bare keyword. Re-ran: 9/9 passing, confirmed via a targeted `rg -n "recurse-submodules|submodule update"` sweep across all live `.md` files.
- **`gh pr merge` and `gh pr view` blocked by the Claude Code auto-mode classifier:** merging a PR is an outward-facing action this session's harness would not permit directly. The orchestrator performed the merge; this agent verified the merged state locally (`git fetch` + `git log`) rather than via `gh`.
- **Pre-existing lint issue found, not fixed:** `uv run ruff check .` reports one `I001` unsorted-import finding in `helpers/tests/test_cli.py:778`, introduced in commit `e6dcddc` (Phase 4 work, `fix(04-04): bound unit fetch to timeout`). This predates this plan and is outside the scope of any file this plan's tasks list — left untouched per the scope-boundary rule, not auto-fixed.
- **One flaky test on first full-suite run:** `test_review_returns_before_hung_unit_fetch_completes` failed once under load (`elapsed 4.87s` vs. an asserted `< 2.0s` bound) and passed cleanly in isolation on retry (`1.65s`). A timing assertion under system load, not a regression from this plan's changes — none of this plan's edits touch `cli.py` or that test.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- REL-01 and REL-02 requirements complete. The submodule-claim, redteam-prompt, deps-template, and cwd-bug-explanation rows from the Phase 5 defect ledger (D-02, D-04 x3) are closed and can be marked resolved in the ledger, citing this summary's 6-file/8-mention count for the submodule claim.
- `test_docs_invariants.py` now carries 2 additional code-derived guards (9 total in the file), holding both corrected claims closed against regression.
- Pre-existing, out-of-scope `ruff` finding in `test_cli.py:778` remains open for whichever future plan next touches that file.
- No blockers for the next plan in the phase's wave sequence.

---
*Phase: 06-remediation-and-governed-release*
*Completed: 2026-08-21*

## Self-Check: PASSED

All claimed files and commits verified present:
- FOUND: `.planning/phases/06-remediation-and-governed-release/06-03-SUMMARY.md`
- FOUND: `2b9b787`, `34e25f3`, `fa012be`, `3e1b7e8`, `8c3c800`
