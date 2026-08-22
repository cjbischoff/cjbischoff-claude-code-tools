# Phase 7: Test & Lint Debt Cleanup - Context

**Gathered:** 2026-08-22
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase closes three acknowledged debt items from PR #23 and nothing else:

1. TEST-01 — `test_rule_glob.py` asserts that the CLI forwards `--workspace` to `run_review`.
2. TEST-02 — the WR-01 tests in `test_review_live.py` prove the guard runs before any git call.
3. LINT-01 — the ruff `I001` finding in `test_cli.py` is fixed and a full-repo ruff run is clean.

No new features, no edits to production code paths, no doc work (Phase 8 owns docs).

</domain>

<decisions>
## Implementation Decisions

### TEST-01 test shape
- **D-01:** Extend the existing test `test_review_cli_parses_rule_and_exclude_and_reaches_run_review` (`plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_rule_glob.py:224`). Pass `--workspace` in the CLI invocation and capture and assert `workspace` in the fake `run_review`. Do not add a new test function.
- **D-02:** Assert only `workspace`. Do not add assertions for `model`, `prepare`, `concurrency`, or other kwargs.

### TEST-02 proof method
- **D-03:** Prove ordering with a zero-git-calls spy. Monkeypatch `subprocess.run` with a recording spy. On a bad `--root`, assert exit code 2 AND an empty spy call list. This proves no git process ran before the guard fired.
- **D-04:** Apply the spy to all three WR-01 tests: missing root, empty root, and file-as-root (`plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_live.py:403-432`). Reuse one helper.

### LINT-01 fix depth
- **D-05:** Apply the ruff autofix (`ruff check --fix`) to `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_cli.py`, then run `ruff check .` at the repo root as the success gate.
- **D-06:** If the full-repo run surfaces other pre-existing findings, report them in verification notes. Do not fix them in this phase.

### Delivery & versioning
- **D-07:** One branch, one pull request. A single commit `test(sec-overlay): close PR #23 test and lint debt` covers all three items.
- **D-08:** Test files under `helpers/tests/` are shipping files, so the commit bumps the sec-overlay `plugin.json` patch version once and adds one `CHANGELOG.md` entry.

### Claude's Discretion
- Spy helper naming and placement inside `test_review_live.py`.
- Exact `--workspace` argument value used in the TEST-01 invocation.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements and roadmap
- `.planning/REQUIREMENTS.md` — TEST-01, TEST-02, LINT-01 definitions with exact file:line targets.
- `.planning/ROADMAP.md` — Phase 7 goal and the three success criteria.

### Target files
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_rule_glob.py` — TEST-01 target (test at line 224, fake `run_review` signature at line 231).
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_live.py` — TEST-02 target (WR-01 block, lines 403-432).
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_cli.py` — LINT-01 target (`I001` at line 778: `from sec_overlay import cli` sorted after `import subprocess`).

### Governance
- `CLAUDE.md` (repo root) — commit format, version-bump rule, changelog routing.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Monkeypatch-based fake `run_review` pattern already exists in `test_rule_glob.py:229-235` — extend it for the `workspace` capture.
- `test_review_live.py` already monkeypatches and uses `capsys`; the spy helper fits the file's existing style.

### Established Patterns
- Tests use plain pytest with `tmp_path`, `monkeypatch`, `capsys`. No fixtures files, no mocks library.
- The ruff `I001` fix is autofixable (`[*]` marker) — a two-line import swap.

### Integration Points
- None. All edits are test-file-local; production code is untouched.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches within the decisions above.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. If the full-repo ruff run surfaces extra findings, they become deferred items per D-06.

</deferred>

---

*Phase: 7-Test & Lint Debt Cleanup*
*Context gathered: 2026-08-22*
