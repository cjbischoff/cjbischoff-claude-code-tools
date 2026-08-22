---
phase: 03-rule-matching-review-modes
plan: 02
subsystem: security-tooling
tags: [python, stdlib-only, sec-overlay, rule-resolution, cli]

requires:
  - phase: 03-rule-matching-review-modes
    provides: built-in-only rule resolution tracer (`resolve_rule_doc`, `glob_match`, `builtin_rule_docs_dir`)
provides:
  - Four-layer per-path rule resolution (custom, project, global, built-in) with first-match-wins fallthrough
  - Whole-layer first-non-empty include/exclude filter selection, structurally separate from per-path resolution
  - `--rule` / `--exclude` CLI flags on the `review` subcommand
  - `merge_system_rule` header-concatenation merge for built-in + user rule text
  - RULE-03 hard-reject rule-file safety gate (`read_rule_file_safe`, `RuleSafetyError`)
affects: [phase-04-concurrency-and-flag-surface]

actuals:
  tokens: 42000
  tasks: 3
  commits: 7

tech-stack:
  added: []
  patterns:
    - "Per-path layer fallthrough and whole-layer filter selection kept as two structurally separate functions (`match_project_rule_entry`, `build_file_filter`) that never call each other, per RULE-02's highest-risk-mis-implementation warning"
    - "Rule-file reads all funnel through one safety-gate entry point (`read_rule_file_safe`); no other code path opens a rule file"
    - "Safety-cap enforcement happens on the capped read itself (TOCTOU-safe), never via a separate `stat` call"

key-files:
  created: []
  modified:
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/rule_glob.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_rule_glob.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md
    - plugins/sec-overlay/CHANGELOG.md
    - plugins/sec-overlay/.claude-plugin/plugin.json

key-decisions:
  - "read_rule_file_safe's repo_root parameter is exactly the base already threaded to that layer's loader (true repo_root for the project layer, the layer's own config file's parent directory for custom/global) — not a separately threaded true project root. A global config under ~/.sec-overlay/ is essentially never nested under an arbitrary project's repo_root, so enforcing the true root uniformly would fail the global layer on every real invocation."
  - "Boundary check runs against the symlink-resolved path (stronger than OCR's pre-resolution check), closing a symlink-escape gap OCR itself has"
  - "A safety violation always hard-raises RuleSafetyError; OCR's warn-and-fallthrough behavior is deliberately not ported (D-08)"
  - "Size cap enforced on the read itself via a capped open('rb') + read(cap+1), not a separate stat call, so a file that grows between stat and read cannot bypass the limit"
  - "Test names for the safety gate use the literal substring 'safety' (not just 'safe') so the plan's `-k safety` acceptance filter collects all six tests"

requirements-completed: [RULE-02, RULE-03, RULE-04]

coverage:
  - id: D1
    description: "Four-layer per-path rule resolution (custom > project > global > built-in) with first-match-wins fallthrough"
    requirement: RULE-02
    verification:
      - kind: unit
        ref: "tests/test_rule_glob.py -k rule_resolution or -k layer or -k fallthrough"
        status: pass
    human_judgment: false
  - id: D2
    description: "Whole-layer first-non-empty include/exclude filter selection, plus --rule/--exclude CLI wiring"
    requirement: RULE-02
    verification:
      - kind: unit
        ref: "tests/test_rule_glob.py::test_build_file_filter and related build_resolution tests"
        status: pass
    human_judgment: false
  - id: D3
    description: "merge_system_rule header-concatenation merge"
    requirement: RULE-04
    verification:
      - kind: unit
        ref: "tests/test_rule_glob.py -k merge"
        status: pass
    human_judgment: false
  - id: D4
    description: "RULE-03 hard-reject rule-file safety gate: symlink resolution, extension allowlist, repo-root containment, 512 KB cap enforced on the read"
    requirement: RULE-03
    verification:
      - kind: unit
        ref: "tests/test_rule_glob.py -k safety (6 tests)"
        status: pass
    human_judgment: false

duration: 1h10m
completed: 2026-08-18
status: complete
---

# Phase 3 Plan 2: Four-Layer Rule Resolution + Safety Gate Summary

**Four-layer per-path rule resolution with a hard-reject rule-file safety gate (symlink resolution, extension allowlist, repo-root containment, 512 KB cap), `--rule`/`--exclude` CLI flags, and `merge_system_rule` header concatenation.**

## Performance

- **Duration:** 1h10m (prior sessions completed Tasks 1-2; this session finished Task 3's GREEN implementation and documentation)
- **Tasks:** 3/3 completed
- **Files modified:** 7 (2 source, 1 test, 4 docs/config)

## Accomplishments

- `resolve_rule_doc` now walks `[custom, project, global]` per path before falling back to the built-in map, deciding independently per path (`match_project_rule_entry`).
- `build_file_filter(layers)` selects the first whole layer whose `include`/`exclude` lists are non-empty — structurally separate from per-path resolution, sharing no loop or helper with it.
- `build_resolution(rule_path, excludes, repo_root)` assembles the custom (`--rule`), project, and global layers plus their file filter; the CLI's `--rule` and `--exclude` (repeatable) flags on `review` reach `run_review`, narrowing `selection.reviewable` before the coverage manifest loop.
- `merge_with_system_rule(builtin_text, user_text)` concatenates built-in and user rule text under `## System-Specific Rules (Mandatory)` / `## User-Specific Rules (Mandatory)` headers, covering all three empty-input cases.
- `read_rule_file_safe(path, repo_root)` is the sole entry point for opening a rule file: resolves symlinks (`Path.resolve(strict=True)`), checks the resolved suffix against `ALLOWED_RULE_EXTENSIONS`, checks `Path.is_relative_to` containment against the resolved `repo_root`, then reads at most `MAX_RULE_FILE_BYTES + 1` (524289) bytes and rejects anything over the 512 KB cap before any UTF-8 decode. Raises `RuleSafetyError` naming the path and reason; no layer fallthrough on violation.
- `cli.py`'s `run_review` catches `RuleSafetyError` around both `build_resolution` and the per-file `resolve_rule_doc` call, prints the message to stderr, and returns exit code 2.

## Task Commits

1. **Task 1: Per-path layer fallthrough + `merge_system_rule`** - `4d7a4cd` (test, RED) / `1409dc1` (feat, GREEN)
2. **Task 2: Whole-layer filter selection + `--rule`/`--exclude` CLI wiring** - `0b142b9` (test, RED) / `c714b1b` (feat, GREEN)
3. **Task 3: Rule-file safety gate** - `21df638` (test, RED) / `061a2c4` (feat, GREEN)

**Plan metadata:** (final metadata commit follows this SUMMARY)

## Files Created/Modified

- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/rule_glob.py` - four-layer resolution, whole-layer filter selection, `merge_with_system_rule`, `read_rule_file_safe`, `RuleSafetyError`, `_entry_rule_path`
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py` - `--rule`/`--exclude` flags, `RuleSafetyError` handling with exit code 2
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_rule_glob.py` - 25 tests total across the three tasks (6 for the safety gate)
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md` - documents all three tasks' behavior and the safety gate's OCR divergences
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md` - test-suite narrative for the three tasks
- `plugins/sec-overlay/CHANGELOG.md` - `1.52.0` through `1.53.0` entries
- `plugins/sec-overlay/.claude-plugin/plugin.json` - version `1.53.0`

## Decisions Made

- **`read_rule_file_safe`'s `repo_root` boundary is the per-layer resolution base, not a separately threaded true project root.** No user input was available this session to confirm; decided autonomously because enforcing the true project repo root uniformly would make the global layer (`~/.sec-overlay/`, essentially never nested under an arbitrary project) fail its boundary check on every real invocation. This reads T-03-09's "cannot pull text from outside the repo under review" as describing the boundary each layer already trusts for its relative paths, matching the plan's literal instruction to "replace Task 1's placeholder read... with `read_rule_file_safe`" without introducing a new parameter.
- Three deliberate divergences from OCR's `system_rules.go`, documented in `read_rule_file_safe`'s docstring: boundary check on the resolved path (stronger, closes a symlink-escape gap OCR has), hard-raise instead of warn-and-fallthrough (D-08), and TOCTOU-safe size enforcement on the capped read itself rather than a separate `stat`.
- `custom`/`global` layers resolve a relative `rule` field against their OWN config file's directory; only the `project` layer resolves against the true `repo_root` — carried forward unchanged from Task 2, mirrors OCR's `loadRuleFile`/`loadGlobalRule` vs `loadProjectRule`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Safety-gate test names didn't match the plan's `-k safety` filter**
- **Found during:** Task 3 (writing the RED tests)
- **Issue:** Five of the six new tests were named `test_read_rule_file_safe_*`, which contains "safe" but not the literal substring "safety" the plan's acceptance criterion filters on. `pytest -k safety` collected only 1 of 6.
- **Fix:** Renamed the five tests to `test_rule_safety_gate_*` so all six contain "safety".
- **Files modified:** `tests/test_rule_glob.py`
- **Verification:** `pytest tests/test_rule_glob.py -k safety -q` → 6 passed.
- **Committed in:** `21df638` (part of the RED task commit)

---

**Total deviations:** 1 auto-fixed (Rule 3).
**Impact on plan:** Naming-only fix required to satisfy the plan's own acceptance criterion; no scope creep.

## Issues Encountered

None beyond the deviation above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

RULE-02/03/04 are fully implemented and tested. Phase 4 owns the flag surface for the 5000-line size cap and any `--concurrency` support; this plan's resolver functions hold no module-level mutable state, so parallel resolution in Phase 4 will not interleave (probe RULE-02/concurrency, backstop-verified).

---
*Phase: 03-rule-matching-review-modes*
*Completed: 2026-08-18*

## Self-Check: PASSED

All 6 files verified present on disk; all 6 task commits (`4d7a4cd`, `1409dc1`, `0b142b9`, `c714b1b`, `21df638`, `061a2c4`) verified present in git history.
