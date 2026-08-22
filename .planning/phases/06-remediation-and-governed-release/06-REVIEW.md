---
phase: 06-remediation-and-governed-release
reviewed: 2026-08-21T00:00:00Z
depth: standard
files_reviewed: 25
files_reviewed_list:
  - CHANGELOG.md
  - README.md
  - plugins/sec-overlay/.claude-plugin/plugin.json
  - plugins/sec-overlay/CHANGELOG.md
  - plugins/sec-overlay/CLAUDE.md
  - plugins/sec-overlay/README.md
  - plugins/sec-overlay/skills/sec-overlay/CLAUDE.md
  - plugins/sec-overlay/skills/sec-overlay/README.md
  - plugins/sec-overlay/skills/sec-overlay/SKILL.md
  - plugins/sec-overlay/skills/sec-overlay/agents/README.md
  - plugins/sec-overlay/skills/sec-overlay/agents/redteam.md
  - plugins/sec-overlay/skills/sec-overlay/helpers/README.md
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/driver.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phases.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_docs_invariants.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_driver.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_frozen_contract.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_phases.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_live.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_profiles.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_rule_glob.py
findings:
  critical: 0
  warning: 1
  info: 0
  total: 1
status: issues_found
---

# Phase 06: Code Review Report

**Reviewed:** 2026-08-21
**Depth:** standard
**Files Reviewed:** 25 (diff base: `dbac91975162871ad6453289f31a878ac58a9618^`)
**Status:** issues_found

## Summary

Reviewed the Phase 06 remediation diff: the WR-01 `--root` guard and new `--workspace` flag on
`review` in `cli.py`, the redteam/postflight `PHASE_TABLE` wiring in `phases.py`/`driver.py`, the
deps Fix-line rendering fix in `report.py`, and the new/changed test files (`test_review_live.py`,
`test_review_profiles.py`, `test_rule_glob.py`, `test_frozen_contract.py`, `test_docs_invariants.py`).

Findings:

- **`--root` guard (`cli.py:340`)**: all three failure modes (missing, empty, file-as-root) are
  guarded and covered by dedicated tests in `test_review_live.py`. No defect.
- **`--workspace` flag on `review` (`cli.py:353-358`, `671-676`)**: correctly wired, resolved via
  `workspace.load_paths`, and does not weaken the SCALE-03 resume-identity guard (verified by
  `test_review_workspace_override_permits_a_second_profile_without_weakening_the_resume_guard`).
  I initially suspected a crash when `--workspace` points at a fresh, nonexistent directory with
  zero reviewable files (`load_paths` never calls `Workspace.ensure()`), but traced and reproduced
  the actual code path: `report.write_report()` unconditionally calls
  `coverage_ledger.build_coverage_ledger(ws)` before any raw `.write_text()` call, and that
  function calls `ws.kb.mkdir(parents=True, exist_ok=True)`, which creates the whole tree
  (including `ws.root`) as a side effect. Confirmed via a live reproduction script against
  `run_review(...)` with a nonexistent `--workspace` and an empty diff: `rc == 0`, full workspace
  tree created, no crash. **Not a defect** — but see WR-01 below: this behavior is only reachable
  by accident of `build_coverage_ledger`'s `mkdir(parents=True)`, and no test exercises this exact
  combination (fresh `--workspace` + zero reviewable files), so it is not a *guaranteed* contract,
  just a lucky one.
- **`redteam`/`postflight` `PHASE_TABLE` wiring** (`phases.py:119,128`; `driver.py:286,306`):
  correctly ordered and dispatched; matches `test_phases.py`/`test_driver.py` assertions. No defect.
- **Deps Fix-line fix** (`report.py:91`, `pkg.rsplit('@', 1)[0] or pkg`): correctly handles scoped
  npm identifiers (`@scope/name@1.2.3`) that the old `pkg.split('@')[0]` broke on. Verified against
  `test_report.py`'s five cases, all passing. No defect.
- **New test files**: `test_review_profiles.py`'s four new D-08/E-12 tests close a real
  vacuous-subset gap (the security-kept ⊆ general-kept relation was previously only exercised at
  `∅ ⊆ ∅`); `test_rule_glob.py`'s one-line diff correctly adds the new `workspace=None` kwarg to a
  signature-capturing mock. No defects in test logic.
- **Full test suite**: `uv run pytest -q` from `helpers/` → `1 failed, 1283 passed`. The one
  failure, `tests/test_bench.py::test_seed_corpus_is_valid`, is a documented pre-existing
  environmental gap (`bench/corpus_seed/*.json` is gitignored; see
  `skills/sec-overlay/CLAUDE.md:34-37` and `plugins/sec-overlay/CLAUDE.md`'s dev-commands block:
  "full suite (2 env-only failures — see skill CLAUDE.md §1)") — not a Phase 06 regression.
- **Documentation drift**: three docs still claim `review` has no `--workspace` override, directly
  contradicted by the flag this same phase added. See WR-01.

## Warnings

### WR-01: Three doc files still claim `review` has no `--workspace` override

**File:** `plugins/sec-overlay/skills/sec-overlay/SKILL.md:95`
**File:** `plugins/sec-overlay/skills/sec-overlay/README.md:34-36`
**File:** `plugins/sec-overlay/skills/sec-overlay/helpers/README.md:267`

**Issue:** All three files state, verbatim, that `review` has no `--workspace` override and that
the same `--root` string must be passed to every invocation of one review run:

- `SKILL.md:95`: "`--root` has no `--workspace` override for review (unlike `scan`/`audit`): pass
  the identical `--root` string, preferably absolute, to every prepare, dispatch, and consume
  invocation of one review..."
- `README.md:35-36`: "...review shares this convention too — it has no `--workspace` override, so
  pass the same `--root` string to every invocation of one run."
- `helpers/README.md:267`: "...`review` has no `--workspace` override, so the same `--root` string
  must be passed to every invocation of one run."

This is false as of this same phase: `cli.py:671-676` adds a `review.add_argument("--workspace",
...)` flag, `cli.py:353-358` implements it (`if workspace: ws = load_paths(workspace=workspace)`),
and `cli.py:313-318`'s `run_review` docstring accurately documents it ("workspace: Explicit
workspace override (`--workspace`, mirrors `audit`'s flag)..."). The plugin's own `CHANGELOG.md`
entries 1.68.10/1.69.0 document adding this flag (D-03) but do not mention correcting these three
stale passages.

This is not caught by any existing automated check: `test_docs_invariants.py` (read in full, 143
lines) has no assertion about `--workspace` documentation, so the doc-invariant test suite gives a
false sense of safety here. It also violates the plugin's own hard governance rule in
`plugins/sec-overlay/CLAUDE.md`: "**Hard rule — docs track code in the same commit.** When you
change anything under `agents/`, `helpers/`, or `references/` (or any folder that has a
`README.md`), update that folder's `README.md` in the same commit" — enforced by the repo's prek
pre-commit hook, but the hook only checks that a README was *touched* in the same commit as a
sibling file change, not that its content is accurate, so a stale claim can survive it if the
README was edited for an unrelated reason in the same commit (as happened here — these READMEs
were edited in this phase for the redteam/postflight ordering fix, D-01, but the pre-existing
`--workspace` claim was left untouched).

A user or agent following `SKILL.md`'s or `README.md`'s guidance would incorrectly conclude that
per-run workspace overrides are impossible for `review`, when `--workspace` has in fact shipped
and is tested (`test_run_review_uses_the_workspace_override_when_supplied`,
`test_run_review_falls_back_to_the_repo_sidecar_when_workspace_is_absent`).

**Fix:** Update all three passages to reflect the new flag. For example, in `SKILL.md:95`:

```markdown
# before
`--root` has no `--workspace` override for review (unlike `scan`/`audit`): pass the identical
`--root` string, preferably absolute, to every prepare, dispatch, and consume invocation of one
review...

# after
`review` now takes a `--workspace` override, mirroring `scan`/`audit` (default: the per-repo
sidecar beneath `--root`). Whichever you use — the default sidecar or an explicit `--workspace` —
pass the identical value to every prepare, dispatch, and consume invocation of one review...
```

Apply the analogous correction to `README.md:34-36` and `helpers/README.md:267`. Consider adding
an assertion to `test_docs_invariants.py` that greps these three files for the stale phrase
`"has no.*--workspace override"` (or an allowlist of the correct phrasing) so a future flag
addition cannot silently leave documentation behind again.

---

_Reviewed: 2026-08-21_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
