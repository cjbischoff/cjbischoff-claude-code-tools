# `tests/` — the deterministic test suite

82 pytest files, 599 tests. Run from `helpers/`: `uv run pytest -q`. Two failures on a clean
checkout are environmental (gitignored bench corpus, excluded semgrep submodule) — see the skill
[`CLAUDE.md`](../../CLAUDE.md) §1.

`test_sarif.py` gained `test_suppressed_findings_carry_insource_suppression`, covering
`to_sarif`'s `suppressed` parameter. `test_report.py` gained
`test_write_report_defaults_to_suppressed_full_sarif` and
`test_write_report_confirmed_only_flag_restores_prior_output`, covering `write_report`'s new
suppressed-full default and the `confirmed_only` restore path.

`test_phases.py` (new) covers `sec_overlay/phases.py`'s `PHASE_TABLE` order (findings-gate right
after investigate, dedupe/demote-noise before report, trace present, and now `factcheck` sitting
between `trace` and `calibrate` — ISSUE-047) and the pure sequencer helpers (`missing_inputs`,
`outputs_present`, `next_actionable_phase`).

`test_driver.py` covers `sec_overlay/driver.py`'s `run_deterministic_phase`: raises
`PhaseHalt` on a missing input, raises `PhaseHalt` when the action ran but a declared output is
still absent, and records the stage `"done"` on success. Also covers `render_dispatch`: the
returned block names the `agents/<prompt>` file and the substituted target/workspace/SHA, and now
`test_dispatch_is_secret_redacted` asserts the block is passed through `redactor.safe_for_prompt`
before returning (ISSUE-051). Three `run_audit` tests (new) cover the resumable table-walker:
halts at `recon` with no scan-profile yet, auto-advances past `recon` once its output exists and
halts at `architecture`, and — the regression guard — does NOT auto-skip `critic` just because
`findings_dir` (its shared input/output path) already exists from earlier phases. Also covers
`unrouted_triage_dispatch` (names an unrouted class and its count; `None` when
`unrouted_candidate_classes` is empty), the `investigate`-phase wiring in `run_audit` (the dispatch
carries `render_dispatch`'s reconciled `{{ATTACK_CLASS}}` list, including a class `reconcile_plan`
added that recon omitted, and the triage block is appended after it when a class stays unrouted),
`test_run_audit_passes_full_class_set_to_patch_dispatch` — drives `run_audit` up through
`calibrate` so `patch` is the actionable phase and asserts its dispatch carries every class from
`agents_to_spawn`, not one token (ISSUE-050), and `test_factcheck_action_applies_verdicts` —
writes a `kb/verdicts.json` VERIFIED verdict for one finding, runs
`DETERMINISTIC_ACTIONS["factcheck"]`, and asserts the finding is stamped
`verification="fact-checked"` (ISSUE-047).

## Structural guards (know these)

| Test | Guards |
|------|--------|
| `test_contracts.py` | Prompt↔schema drift: a `Finding` JSON example in an agent prompt must parse against the real `models.py`. |
| `test_finding_schema.py` | The `Finding` record stays consistent with `references/finding.schema.json`. |
| `test_wiring.py` | Silent-backend / clsmap / dead-link regressions and attack-class routing. |
| `test_docs_invariants.py` | Documentation contracts: prompt-constants block presence, `finding-template.md` sections, agent-prompt rules. |

## The rest

The remaining files are per-module unit tests named `test_<module>.py` mirroring
`sec_overlay/<module>.py` (e.g. `test_calibrate.py`, `test_verify.py`, `test_dedupe.py`), plus
bench/citation tests (`test_bench.py`, `test_citations.py`) that need local seed data.

`test_verify.py`'s `test_verify_findings_static_only_routes_to_needs_deployment_testing` covers
ISSUE-053: a `static-only` re-verify routes the finding to `needs-deployment-testing`, not
`confirmed` — only `verified-static` promotes to `fixed`.

When you add or change a test file, update this README's counts and guard list in the same commit
(enforced by the pre-commit hook).

The review-improvements test files (`test_cluster.py`, `test_scope.py`, `test_selfscore.py`,
`test_sarif.py`, `test_calibrate.py`, `test_report.py`) are `ruff format`-clean; run `ruff format`
before committing edits.
