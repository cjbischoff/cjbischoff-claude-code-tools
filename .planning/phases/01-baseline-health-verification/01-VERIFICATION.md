---
phase: 01-baseline-health-verification
verified: 2026-08-17T00:00:00Z
status: passed
score: 7/7 must-haves verified (1 via recorded override)
overrides_applied: 1
report: 01-VERIFICATION-REPORT.md
---

# Phase 1: Baseline Health Verification

## Tool Versions

| Tool | Version |
| ---- | ------- |
| ruff | 0.16.0 |
| ty | 0.0.64 (5e64a131b 2026-07-27) |
| pytest | 9.1.1 |
| python | 3.13.14 |
| claude | 2.1.220 (Claude Code) |

Captured 2026-08-17 via `uv run --locked --directory plugins/sec-overlay/skills/sec-overlay/helpers <tool> --version` (repo-root `claude --version` for the CLI). No version pins were added to any file (D-09); no `requires-python` floor was declared (D-11).

## VAL-01 — Plugin Validation

- Command: `claude plugin validate .`
- Directory: `.` (repo root)
- Exit code: 0
- Output (tail):

```
Validating marketplace manifest: ~/.claude-plugin/marketplace.json

✔ Validation passed
```

- Command: `claude plugin validate .`
- Directory: `plugins/sec-overlay`
- Exit code: 0
- Output (tail):

```
Validating plugin manifest: ~/plugins/sec-overlay/.claude-plugin/plugin.json

Validating plugin: ~/plugins/sec-overlay/CLAUDE.md

⚠ Found 1 warning:

  ❯ root: CLAUDE.md at the plugin root is not loaded as project context. To ship context with your plugin, use a skill (skills/<name>/SKILL.md) instead.

Validating command: ~/plugins/sec-overlay/commands/README.md

⚠ Found 1 warning:

  ❯ frontmatter: No frontmatter block found. Add YAML frontmatter between --- delimiters at the top of the file to set description and other metadata.

Validating command: ~/plugins/sec-overlay/commands/audit.md

⚠ Found 1 warning:

  ❯ frontmatter: No frontmatter block found. Add YAML frontmatter between --- delimiters at the top of the file to set description and other metadata.

✔ Validation passed with warnings
```

Both invocations exit 0. The second passes with three warnings (an informational CLAUDE.md-at-plugin-root notice, and two frontmatter notices on `commands/README.md` and `commands/audit.md`) — not failures, and not merged into or inferred from the repo-root receipt above.

## VAL-02 — sec-overlay Quality Gates

All three receipts run against `plugins/sec-overlay/skills/sec-overlay/helpers` only (D-13), through `uv run --locked` so a drifted lockfile fails loudly instead of silently re-resolving (D-10).

- Command: `uv run --locked --directory plugins/sec-overlay/skills/sec-overlay/helpers pytest -q`
- Directory: `.` (repo root; `--directory` resolves the target, no `cd`)
- Exit code: 1
- Output (tail):

```
=========================== short test summary info ============================
FAILED tests/test_bench.py::test_seed_corpus_is_valid - assert (0 >= 5)
FAILED tests/test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd
2 failed, 816 passed in 28.79s
```

- Command: `uv run --locked --directory plugins/sec-overlay/skills/sec-overlay/helpers ruff check sec_overlay/ bench/ tests/`
- Directory: `.` (repo root; `--directory` resolves the target, no `cd`)
- Exit code: 1
- Output (tail):

```
Found 4 errors.
No fixes available (4 hidden fixes can be enabled with the `--unsafe-fixes` option).
```

- Command: `uv run --locked --directory plugins/sec-overlay/skills/sec-overlay/helpers ty check`
- Directory: `.` (repo root; `--directory` resolves the target, no `cd`)
- Exit code: 1
- Output (tail):

```
Found 161 diagnostics
```

`--locked` held for all three commands — no lockfile drift.

## VAL-03 — prek Hooks

- Command: `prek run --all-files`
- Directory: `.` (repo root)
- Exit code: 0
- Output (tail):

```
Require README.md and CHANGELOG.md updates...............................Passed
```

Only the `doc-update-guard` hook id from `.pre-commit-config.yaml` appears in this output. `conventional-commit-msg` is registered under `stages: [commit-msg]`; `prek run --all-files` runs pre-commit-stage hooks only and never invokes a commit-msg-stage hook, which needs a real commit-message file to lint. This is the exact unresolved VAL-03 assumption flagged in 01-01-PLAN.md's `<flagged_assumptions>` — the plan assumed one `--all-files` run would exercise both hook ids; it exercises one. Carried into the Triage Ledger below as a `config` finding for the Task 3 checkpoint to confirm or correct.

## Triage Ledger

| Gate | Failure | Disposition | Rationale |
| ---- | ------- | ------------ | --------- |
| VAL-02 pytest | `tests/test_bench.py::test_seed_corpus_is_valid` | environmental | `bench/corpus_seed/` holds only `README.md` — the labelled corpus JSON is gitignored and absent in this checkout, matching the maintainer's documented environment-only failure (plugin `CLAUDE.md` §1, sec-overlay skill `CLAUDE.md` §1). Not resolved by committing corpus data. |
| VAL-02 pytest | `tests/test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd` | environmental | `rules/semgrep/` is absent and no `.gitmodules` is registered in this repo, so the vendored semgrep ruleset the plugin `CLAUDE.md` documents as a submodule prerequisite is not present in this checkout — same class of clean-checkout gap as the bench corpus above, not a code defect. |
| VAL-02 ruff | 4 lint errors: `C408` x2 (`tests/test_citations.py:16`, `tests/test_factcheck_baseline_envelope.py:9`), `RUF015` (`tests/test_postflight.py:26`), `FLY002` (`tests/test_structural_index.py:115`) | code defect | Real style violations in test-helper code, not stale assertions — each rewrites a `dict()`/slice/join to the form ruff prefers. No test's asserted behavior is wrong (D-03 does not apply); production/test code changes, not the check. |
| VAL-02 ty | 161 diagnostics (154 `invalid-argument-type`, 3 `unresolved-reference`, 2 `unresolved-attribute`, 1 `unsupported-operator`, 1 `not-subscriptable`) across 14 files: `tests/test_report.py` (55), `tests/test_factcheck_baseline_envelope.py` (34), `tests/test_citations.py` (34), `tests/test_prefilter.py` (14), `tests/test_bench.py` (5), `sec_overlay/stage_validate.py` (4), `tests/test_workspace.py` (3), `tests/test_profile.py` (3), `tests/test_wiring.py` (2), `tests/fixtures/graph_target/app/db.py` (2), `tests/test_rule_matcher.py` (1), `tests/test_patch_status.py` (1), `tests/test_calibrate.py` (1), `tests/test_bucket_b.py` (1), `tests/fixtures/graph_target/app/api.py` (1) | code defect | Real type errors, mostly test call-sites passing loosely-typed literals/dicts against stricter model signatures (for example `tests/test_workspace.py:32` passing `str` where `Workspace` expects `Path`), plus one production file (`sec_overlay/stage_validate.py`, 4 diagnostics). Full 161-diagnostic output greped for `models.py`/`evidence.py`: zero matches — neither frozen contract module (D-02) appears in any diagnostic; a fix is in scope for normal governance. |
| VAL-03 prek | `conventional-commit-msg` hook id never appears in `prek run --all-files` output | config | The hook is `stages: [commit-msg]` in `.pre-commit-config.yaml`; `--all-files` only fires pre-commit-stage hooks. Not a broken hook — `--all-files` structurally cannot exercise a commit-msg-stage hook. Flagged as the VAL-03 assumption in 01-01-PLAN.md for the Task 3 checkpoint. |

Every VAL-01 receipt exited 0; no VAL-01 row is needed.

## Remediation Route

**Selected: `proceed-as-triaged`**

No row in the Triage Ledger touches `sec_overlay/models.py` or `sec_overlay/evidence.py` (confirmed against the full 161-line ty diagnostic output, not a tail sample). Plan 02 executes the ledger's two code-defect rows (VAL-02 ruff: 4 files; VAL-02 ty: 15 files) under normal governance, including the shipping-file version bump and changelog entry the sec-overlay plugin requires. The two environmental pytest rows and the one config row (VAL-03) carry no proposed fix and stay as documented, checkable gaps. Phase 1 completes with this plan; Plan 02 is scoped by this ledger, not by re-running the gates from scratch.

## VAL-01 / VAL-03 Remediation

No fix required; both gates green at baseline. Re-verified during Plan 02 execution:

- `claude plugin validate .` at the repo root: exit 0 (`✔ Validation passed`).
- `claude plugin validate .` inside `plugins/sec-overlay/`: exit 0 (`✔ Validation passed with warnings` — 3 pre-existing warnings on `CLAUDE.md` project-context loading and missing command frontmatter, none of them a VAL-01 failure and none touched by this plan).
- `prek run --all-files` from the repo root: exit 0.

The VAL-03 `config` row (`conventional-commit-msg` never appearing in `--all-files` output) is
unchanged from Plan 01's finding: the hook is `stages: [commit-msg]` and structurally cannot run
under `--all-files`, which only fires pre-commit-stage hooks. This is not a broken hook and the
Remediation Route already dispositioned it as a documented, checkable gap rather than an
actionable defect — Task 2 makes no commit against it.

## Final Verification

Captured 2026-08-17 after the last fix commit (`111f28e`, Plan 02's completion commit). Tool
versions re-checked and unchanged from the block above: ruff 0.16.0, ty 0.0.64
(5e64a131b 2026-07-27), pytest 9.1.1, python 3.13.14, claude 2.1.220 — no drift, no note needed
(D-09).

`git status --porcelain` before capture showed two untracked GSD orchestration files
(`.gsd/dispatch-isolation-sentinel.json`, `.planning/config.json`) — execution-harness
bookkeeping created by the phase orchestrator, not tracked project content, not touched by any
gate, and outside this plan's `files_modified` scope. No tracked file was modified or staged.
The tree was otherwise clean; these two files are noted here for full disclosure rather than
omitted.

- Command: `claude plugin validate .`
- Directory: `.` (repo root)
- Exit code: 0
- Output (tail):

```
Validating marketplace manifest: ~/.claude-plugin/marketplace.json

✔ Validation passed
```

- Command: `claude plugin validate .`
- Directory: `plugins/sec-overlay`
- Exit code: 0
- Output (tail):

```
Validating plugin manifest: ~/plugins/sec-overlay/.claude-plugin/plugin.json

Validating plugin: ~/plugins/sec-overlay/CLAUDE.md

⚠ Found 1 warning:

  ❯ root: CLAUDE.md at the plugin root is not loaded as project context. To ship context with your plugin, use a skill (skills/<name>/SKILL.md) instead.

Validating command: ~/plugins/sec-overlay/commands/README.md

⚠ Found 1 warning:

  ❯ frontmatter: No frontmatter block found. Add YAML frontmatter between --- delimiters at the top of the file to set description and other metadata.

Validating command: ~/plugins/sec-overlay/commands/audit.md

⚠ Found 1 warning:

  ❯ frontmatter: No frontmatter block found. Add YAML frontmatter between --- delimiters at the top of the file to set description and other metadata.

✔ Validation passed with warnings
```

Same three informational warnings as the baseline receipt — unchanged, not regressions.

- Command: `uv run --locked --directory plugins/sec-overlay/skills/sec-overlay/helpers pytest -q`
- Directory: `.` (repo root; `--directory` resolves the target, no `cd`)
- Exit code: 1
- Output (tail):

```
FAILED tests/test_bench.py::test_seed_corpus_is_valid - assert (0 >= 5)
FAILED tests/test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd
2 failed, 816 passed in 27.00s
```

Both failures carry the `environmental` disposition from the Triage Ledger above, restated here:
`test_seed_corpus_is_valid` fails because `bench/corpus_seed/` holds only `README.md` (the
labelled corpus JSON is gitignored and absent in this checkout);
`test_report_finds_vendored_rules_regardless_of_cwd` fails because `rules/semgrep/` is absent
and no `.gitmodules` is registered. Both are unchanged since the phase's baseline run — not a
regression introduced by Plan 02's fixes, and out of this plan's fix scope per the Remediation
Route's `proceed-as-triaged` decision. `--locked` held; no lockfile drift.

- Command: `uv run --locked --directory plugins/sec-overlay/skills/sec-overlay/helpers ruff check sec_overlay/ bench/ tests/`
- Directory: `.` (repo root; `--directory` resolves the target, no `cd`)
- Exit code: 0
- Output (tail):

```
All checks passed!
```

- Command: `uv run --locked --directory plugins/sec-overlay/skills/sec-overlay/helpers ty check`
- Directory: `.` (repo root; `--directory` resolves the target, no `cd`)
- Exit code: 0
- Output (tail):

```
All checks passed!
```

- Command: `prek run --all-files`
- Directory: `.` (repo root)
- Exit code: 0
- Output (tail):

```
Require README.md and CHANGELOG.md updates...............................Passed
```

Only the `doc-update-guard` hook id appears, matching Plan 01's structural finding — unchanged.

**Note on this section's exit-code count:** five of the six receipts above show `Exit code: 0`.
The sixth (pytest) legitimately shows `Exit code: 1` — the two environmental failures the
Triage Ledger dispositioned and the maintainer's Remediation Route explicitly left unfixed. The
plan's own action text names this as the one exception under which the phase still seals
("an environmental failure recorded in the triage ledger is the one exception"); recording a
fabricated `Exit code: 0` for pytest to satisfy a literal six-way count would itself violate the
phase's own prohibition against manufacturing a green gate. See the Summary's Deviations section
for the full account of this plan-text/verify-script tension.

## Fix Ledger

One row per fix that landed under Plan 02's `proceed-as-triaged` Remediation Route. The two
VAL-02 pytest rows and the VAL-03 config row in the Triage Ledger above carry no fix — the
maintainer's route left them as documented, unfixed gaps.

| Gate | Failure | Fix summary | Commit SHA |
| ---- | ------- | ------------ | ---------- |
| VAL-02 ruff | `RUF015` `tests/test_postflight.py:26`; `FLY002` `tests/test_structural_index.py:115` | Replaced slice-then-index with `next()`; replaced `.join()` with adjacent-literal concatenation | b776e26 |
| VAL-02 ruff | `C408` x2 `tests/test_citations.py:16`, `tests/test_factcheck_baseline_envelope.py:9` | Replaced `dict()` + `.update(kw)` + `Finding(**d)` builders with `dataclasses.replace(base, **kw)`, removing the flagged `dict()` literal call | 4fa044c |
| VAL-02 ty | 3 `invalid-argument-type`, `tests/test_workspace.py` | `Workspace.__init__` now coerces a `str` path to `Path` directly | db095dd |
| VAL-02 ty | 16 `invalid-argument-type`, `tests/test_prefilter.py` + `tests/test_wiring.py` | `Exclusions` test fixtures now pass sets instead of list/mixed literals | 381708c |
| VAL-02 ty | 123 `invalid-argument-type` (34 `test_citations.py` + 34 `test_factcheck_baseline_envelope.py` + 55 `test_report.py`) | `dataclasses.replace` restores per-field `ty` checking on `Finding` test builders — `**d`'s inferred dict type had bypassed it | 4fa044c |
| VAL-02 ty | 8 `invalid-argument-type` (5 `test_bench.py` + 3 `test_profile.py`) | Same `dataclasses.replace` builder fix applied to bench/profile test builders | 563079c |
| VAL-02 ty | 3 (1 `unresolved-attribute` `test_rule_matcher.py`, 1 `not-subscriptable` `test_bucket_b.py`, 1 `unsupported-operator` `test_calibrate.py`) | Added `is not None` narrowing before dereferencing optional results | 7a38879 |
| VAL-02 ty | 1 `unresolved-attribute`, `tests/test_patch_status.py` | Replaced ad hoc namespace test double with a real class for the fake runner | de805e3 |
| VAL-02 ty | 4 `invalid-argument-type`, `sec_overlay/stage_validate.py` (production file) | Added `_adapt_dict`/`_adapt_optional_dict` adapters unifying the validator call signature (also closes a real crash-on-malformed-input gap, deviation Rule 2) | 609c421 |
| VAL-02 ty | 3 `unresolved-reference` (2 `tests/fixtures/graph_target/app/db.py` + 1 `app/api.py`) | Stubbed the `cursor`/`app` bindings the fixture referenced but never defined | 74564a4 |

Row diagnostic counts sum to 161 (3+16+123+8+3+1+4+3), matching the Triage Ledger's VAL-02 ty
total exactly. No row in this table touches `sec_overlay/models.py` or `sec_overlay/evidence.py`.

## Constraint Proof

**1. Frozen-contract integrity.** Diffed the two D-02 modules from the phase-start commit
(`a4731cb`, "docs(01): complete 01-01 plan") to `HEAD`:

- Command: `git diff --name-only a4731cb..HEAD -- plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/models.py plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/evidence.py`
- Exit code: 0
- Output: (empty — no changes to either file across all of Plan 02 and Plan 03)

**2. Governance compliance.** For each of the 9 shipping-file fix commits in the Fix Ledger,
`git show --name-only <sha> | grep -E 'plugin\.json|CHANGELOG\.md'` confirms both files staged
in the same commit:

```
db095dd: plugins/sec-overlay/.claude-plugin/plugin.json, plugins/sec-overlay/CHANGELOG.md
381708c: plugins/sec-overlay/.claude-plugin/plugin.json, plugins/sec-overlay/CHANGELOG.md
b776e26: plugins/sec-overlay/.claude-plugin/plugin.json, plugins/sec-overlay/CHANGELOG.md
4fa044c: plugins/sec-overlay/.claude-plugin/plugin.json, plugins/sec-overlay/CHANGELOG.md
563079c: plugins/sec-overlay/.claude-plugin/plugin.json, plugins/sec-overlay/CHANGELOG.md
7a38879: plugins/sec-overlay/.claude-plugin/plugin.json, plugins/sec-overlay/CHANGELOG.md
de805e3: plugins/sec-overlay/.claude-plugin/plugin.json, plugins/sec-overlay/CHANGELOG.md
609c421: plugins/sec-overlay/.claude-plugin/plugin.json, plugins/sec-overlay/CHANGELOG.md
74564a4: plugins/sec-overlay/.claude-plugin/plugin.json, plugins/sec-overlay/CHANGELOG.md
```

Nine fix commits, nine consecutive patch bumps (`1.37.3` through `1.37.11`), each with its own
changelog entry — no fix landed without its version bump.

**3. Ledger integrity.** `git cat-file -t <sha>` for every SHA in the Fix Ledger:

```
db095dd: commit
381708c: commit
b776e26: commit
4fa044c: commit
563079c: commit
7a38879: commit
de805e3: commit
609c421: commit
74564a4: commit
```

All nine resolve as real commits — no fabricated or dangling SHA in the ledger.

## Phase Outcome

Phase 1's baseline is trustworthy: both `claude plugin validate .` invocations, ruff, ty, and
prek all exit 0 on the current tree, and ruff/ty's prior 165 combined findings (4 lint errors +
161 type diagnostics) are gone, fixed across 9 commits without touching the frozen
`models.py`/`evidence.py` contract or skipping a version bump. Two gaps remain by deliberate,
documented choice rather than oversight. First, two pytest failures stay red —
`test_seed_corpus_is_valid` and `test_report_finds_vendored_rules_regardless_of_cwd` — both
because this checkout lacks environment-only data the plugin's own `CLAUDE.md` documents as a
prerequisite (a gitignored labelled corpus under `bench/corpus_seed/`, and a `rules/semgrep/`
vendored ruleset with no `.gitmodules` registered to fetch it), not because of a code defect;
the maintainer's `proceed-as-triaged` Remediation Route left both unfixed on that basis. Second,
prek's `--all-files` run structurally cannot exercise the `conventional-commit-msg` hook, since
that hook is scoped to the `commit-msg` git stage and only fires on an actual commit — a config
fact about how prek stages work, not a broken or missing hook. Anyone relying on this baseline
should install the corpus/submodule data before trusting the pytest gate specifically, and should
trust `conventional-commit-msg` from its per-commit enforcement history (visible in this repo's
commit log) rather than from any `--all-files` receipt.
