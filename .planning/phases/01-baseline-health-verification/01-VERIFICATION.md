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
