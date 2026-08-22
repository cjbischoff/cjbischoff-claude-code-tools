---
phase: 06-remediation-and-governed-release
reviewed: 2026-08-21T00:00:00Z
updated: 2026-08-22T00:00:00Z
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
  info: 1
  total: 2
status: issues_found
---

# Phase 06: Code Review Report

**Reviewed:** 2026-08-21 (plan 06-01..06-05 pass); delta-reviewed 2026-08-22 (plan 06-06)
**Depth:** standard
**Files Reviewed:** 25 (base pass); 1 (06-06 delta: `test_docs_invariants.py`)
**Status:** issues_found (0 critical, 1 warning, 1 info — all new-and-open findings are in the
06-06 delta section below; the base pass's sole finding, WR-01, is closed — see disposition note)

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

**Status: CLOSED.** Fixed in plan 06-06, commit `83da4e0` (`docs(06-06): correct review
--workspace doc claims`); disposition recorded in `06-DEFECTS.md` row 13. Verified during this
delta pass: `rg -n -i "workspace override" SKILL.md README.md helpers/README.md` now returns zero
matches, and the code-derived regression guard this fix added
(`test_no_live_doc_denies_the_review_workspace_override`) passes against the current tree. Kept
below, unmodified, for the historical record of what the original finding was.

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

## Plan 06-06 delta review

**Reviewed:** 2026-08-22
**Depth:** standard
**Scope:** the single source file changed across commits `83da4e0`, `bf6e65a`, `07ed797`,
`b7c7a01` — `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_docs_invariants.py`. All
other changed files in this plan are Markdown docs, a `plugin.json` version bump, and planning
artifacts; checked only for factual consistency against the code (see below), not deep-reviewed.

### What 06-06 shipped in this file

Two commits touched the test file. `83da4e0` added `_STALE_WORKSPACE_CLAIM_PATTERN` (a `"has
no\s*` `--workspace` `\s*override"` regex), the `inspect`/`re` imports, the `run_review` import,
and `test_no_live_doc_denies_the_review_workspace_override` (the WR-01 regression guard, pinning
its premise against `run_review`'s real keyword-argument signature). `07ed797` (a CodeRabbit
follow-up on PR #29) broadened the regex to also catch "does not support" and "lacks (a/an)"
phrasings, and added two new pattern-only tests:
`test_stale_workspace_claim_pattern_matches_known_denial_phrasings` and
`test_stale_workspace_claim_pattern_does_not_match_corrected_wording`.

### Verification performed

- `uv run pytest tests/test_docs_invariants.py -q` → **13 passed** (0 failed).
- `uv run pytest -q` (full suite, from `helpers/`) → **1 failed, 1287 passed**; the one failure is
  the same pre-existing environmental gap noted in the base pass (`test_bench.py`, gitignored
  corpus) — not a regression from this file.
- `uv run ruff check tests/test_docs_invariants.py` → clean (`[]`, exit 0).
- No line in the file exceeds the project's 100-character limit.
- No debug artifacts (`print`, `TODO`, `FIXME`, `XXX`, `HACK`, `debugger`) in the file.
- Confirmed `run_review` (`cli.py:233-249`) genuinely has a `workspace: str | None = None` keyword
  parameter — `inspect.signature(run_review).parameters` includes `"workspace"` today, so the
  premise assertion at line 133 does not vacuously pass; it would fail loudly (with the stated
  message) if that parameter were ever renamed or removed, which is the guard's stated purpose.
- Confirmed `_PLUGIN_ROOT` (`parents[4]` from the test file's path) resolves to
  `plugins/sec-overlay` — the plugin root, not a wider or narrower scope — and `.rglob("*.md")`
  from there stays inside the plugin directory tree; no path escapes upward or sideways.
- Live-ran the regex against the current doc tree with the same filtering logic the test uses
  (`CHANGELOG.md` name-skip, `_HISTORICAL_DIR_MARKERS`/`_VENDORED_DIR_MARKERS` skip) — zero
  matches, confirming the WR-01 fix (`SKILL.md`, `README.md`, `helpers/README.md`) actually landed
  and the guard's premise holds against the real doc tree.
- Confirmed `plugins/sec-overlay/CHANGELOG.md:33` quotes the exact stale phrase (`` "review lacks
  a `--workspace` override" ``) as historical prose describing the fix — this is exactly the case
  the `if md_file.name == "CHANGELOG.md": continue` exclusion exists to protect against; without
  it, the guard would false-positive on its own changelog.
- Regex correctness spot-checks against the four denial phrasings the test pins and the two
  corrected phrasings it pins as non-matches: all six behave as the test file asserts (traced by
  hand; matches the passing test run above).

No bugs found in the regex, the premise check, the `rglob` scope, or test isolation (each test
only reads files; no test mutates shared state or leaves artifacts).

### WR-02: `test_stale_workspace_claim_pattern_matches_known_denial_phrasings`'s docstring
overclaims exhaustive regex coverage

**Severity:** Warning
**File:** `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_docs_invariants.py:150-159`

**Issue:** The docstring reads: "The pattern must catch every denial wording review's doc surfaces
could regress to." The implementation is three hardcoded literal alternatives — `has no`, `does
not support`, `lacks(?: an?)?` — immediately (whitespace-only gap) followed by `` `?--workspace`?
``. This catches the four specific phrasings the test enumerates, and the three phrasings the
original WR-01 finding actually used, but it is not exhaustive of "every" wording a future doc
regression could use. Plausible denial phrasings that would **not** match and would silently pass
the guard:

- `"review has no support for --workspace"` (inserts "support for" between "has no" and the flag —
  the regex requires only whitespace in that gap)
- `"review doesn't support --workspace"` (the contraction, vs. the literal `"does not support"`)
- `"review cannot use a --workspace override"` / `"you can't pass --workspace to review"`
- `"there is no --workspace flag for review"`

This is the same design already used by this file's older
`_SUBMODULE_INSTRUCTION_PHRASES = ("recurse-submodules", "submodule update", "is a git submodule")`
guard (a fixed phrase tuple, not a semantic check) — so the narrow-coverage *pattern* is an
established, accepted tradeoff in this codebase, not a new design mistake. What is new and
specific to this test is the docstring's absolute claim ("every denial wording... could regress
to") layered on top of that narrow, literal-phrase implementation. A maintainer reading only the
docstring — which is exactly what this guard exists to let a maintainer do instead of re-deriving
the regex's actual coverage — would reasonably believe re-wording a future stale doc claim in any
form is caught, when in fact only these three literal shapes are.

Given this guard is the direct regression-prevention mechanism for a defect that a human reviewer
had to catch by hand once already (WR-01 was not caught by any automated check when first
introduced), an overclaiming docstring here creates a specific risk: a future contributor sees
this test passing and the docstring's "every wording" claim, and concludes the doc-drift class of
bug is now fully guarded against, when a differently-phrased regression would slip through
silently exactly as WR-01 originally did.

**Fix:** Narrow the docstring to what the pattern actually verifies. For example:

```python
def test_stale_workspace_claim_pattern_matches_known_denial_phrasings():
    """The pattern catches the three literal denial phrasings WR-01 found in the wild.

    Not exhaustive of every possible future wording — see
    _STALE_WORKSPACE_CLAIM_PATTERN's docstring for the literal-phrase tradeoff this
    guard accepts, same as _SUBMODULE_INSTRUCTION_PHRASES above.
    """
```

Optionally, widen the regex to also catch the contraction and a couple of the other plausible
phrasings above (e.g. add `doesn't support`, `cannot use`, `can't (?:use|pass)` to the
alternation) if the added coverage is worth the added regex complexity — this is a judgment call,
not a blocking requirement, since the pattern-tuple approach is already established in this file.

### IN-01: Duplicate doc-walking loop between two guard tests

**Severity:** Info
**File:** `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_docs_invariants.py:105-124,
127-147`

**Issue:** `test_no_live_doc_claims_a_git_submodule_that_does_not_exist` (pre-existing, unchanged
by 06-06) and `test_no_live_doc_denies_the_review_workspace_override` (new in 06-06) both contain
an identical loop shape:

```python
for md_file in _PLUGIN_ROOT.rglob("*.md"):
    rel = "/" + md_file.relative_to(_PLUGIN_ROOT).as_posix()
    if md_file.name == "CHANGELOG.md":
        continue
    if any(marker in rel for marker in _HISTORICAL_DIR_MARKERS + _VENDORED_DIR_MARKERS):
        continue
    txt = md_file.read_text()  # or .lower()
    ...
```

06-06 introduced the second copy of this loop rather than factoring a shared iterator. This is a
straightforward duplication (not a correctness bug — both copies are correct and independently
verified above), and it means a future third guard of the same shape (a third phrasing regression
class) would add a third copy rather than reuse one.

**Fix:** Extract a shared helper, e.g.:

```python
def _iter_live_docs():
    """Yield every live (non-historical, non-vendored, non-CHANGELOG) doc under the plugin root."""
    for md_file in _PLUGIN_ROOT.rglob("*.md"):
        rel = "/" + md_file.relative_to(_PLUGIN_ROOT).as_posix()
        if md_file.name == "CHANGELOG.md":
            continue
        if any(marker in rel for marker in _HISTORICAL_DIR_MARKERS + _VENDORED_DIR_MARKERS):
            continue
        yield md_file, rel
```

Then both tests iterate `_iter_live_docs()` instead of repeating the filter. Not blocking —
optional cleanup the next time either test is touched.

---

_Reviewed: 2026-08-21 (base pass); 2026-08-22 (06-06 delta)_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
