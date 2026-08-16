# `tests/` — the deterministic test suite

85 pytest files, 677 tests. Run from `helpers/`: `uv run pytest -q`. Two failures on a clean
checkout are environmental (gitignored bench corpus, excluded semgrep submodule) — see the skill
[`CLAUDE.md`](../../CLAUDE.md) §1.

`test_wiring.py` gained four regression pins (ISSUE-017, ISSUE-020, ISSUE-031, ISSUE-033) for
already-wired items: `reconcile_plan(` and `unrouted_candidate_classes(`/`unrouted_triage_dispatch(`
appear in `driver.py`, `render_fp_feedback` keys on `fingerprint`, and `run_deterministic_phase`
halts with `"did not produce"` when a declared output artifact is absent. `test_fp_feedback.py`
gained `test_feedback_survives_workspace_rename` (ISSUE-033), pinning that the fingerprint-keyed
feedback body is identical across a workspace rename (nonce excluded from the comparison, since
`wrap_untrusted` mints a fresh one per call).

`test_codeql.py` gained `test_every_codeql_finding_carries_receipt` (ISSUE-004): regression pin for codeql receipt attachment — every parsed finding must carry at least one `codeql:<rule_id>` evidence source.

`test_dedupe.py` gained `test_dedupe_same_line_same_class_dedupes_without_dataflow` (ISSUE-042):
two `RAW` findings sharing `(file, line, cls)` with empty `dataflow` and differing message
collapse to one duplicate. `test_correlate_edges.py` gained
`test_recurrence_uses_shared_shipping_set` (ISSUE-005), asserting `edges._RECURRENCE_STATUSES ==
evidence.SHIPPING_STATUSES`.

`test_contracts.py` gained three prompt-text assertions (ISSUE-027, ISSUE-029, ISSUE-036):
`test_recon_prompt_requires_route_summary`, `test_architecture_prompt_requires_all_controls`,
and `test_threat_model_retains_every_entrypoint` check that `recon.md`, `architecture.md`, and
`threat-model.md` each emit what `sec_overlay.route_control`'s checks look for.

`test_context.py` gained three tests for `doc_coverage()`: `test_doc_coverage_warns_when_few_docs_read`, `test_doc_coverage_warns_below_ratio`, and `test_doc_coverage_no_docs_no_warning` (ISSUE-016) — validate doc coverage ratio computation and warning thresholds.

`test_profile.py` gained `test_schema_declares_evidence_and_subsystems` and
`test_profile_required_includes_attack_surface_evidence` (ISSUE-025): the schema and
`profile._REQUIRED` now agree that `attack_surface_evidence` is required, `subsystems` optional.

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
`test_run_audit_halts_when_scan_profile_missing_at_investigate` (new, M1, 0.10.1) stages state up
to `investigate` with no `scan-profile.json` and asserts `run_audit` raises `PhaseHalt` (not
`FileNotFoundError`) naming the missing file.

`test_cli_e2e.py` gained `test_audit_cli_resumable_across_invocations` (new, C1, 0.10.1): drives
`cli.main(["audit", ...])` twice with `driver.run_audit` stubbed and `record_stage(ws,
"investigate")` called between the two invocations (simulating the orchestrator's manual record),
and asserts the second `audit` invocation leaves that stage recorded and `pass_number` unchanged —
the regression guard for the CLI no longer calling `state.begin_pass` on every invocation.

## Structural guards (know these)

| Test | Guards |
|------|--------|
| `test_contracts.py` | Prompt↔schema drift: a `Finding` JSON example in an agent prompt must parse against the real `models.py`. |
| `test_finding_schema.py` | The `Finding` record stays consistent with `references/finding.schema.json`. |
| `test_wiring.py` | Silent-backend / clsmap / dead-link regressions and attack-class routing. |
| `test_docs_invariants.py` | Documentation contracts: prompt-constants block presence, `finding-template.md` sections, agent-prompt rules, and (new) the `EVIDENCE_VOCABULARY` block listing every `sec_overlay.evidence` tier/status/disposition value verbatim. |

## The rest

The remaining files are per-module unit tests named `test_<module>.py` mirroring
`sec_overlay/<module>.py` (e.g. `test_calibrate.py`, `test_verify.py`, `test_dedupe.py`), plus
bench/citation tests (`test_bench.py`, `test_citations.py`) that need local seed data.

`test_verify.py`'s `test_verify_findings_static_only_routes_to_needs_deployment_testing` covers
ISSUE-053: a `static-only` re-verify routes the finding to `needs-deployment-testing`, not
`confirmed` — only `verified-static` promotes to `fixed`.

`test_evidence.py` gained coverage for the shared tier/status vocab: `TIER1_RECEIPTS |
TIER2_RECEIPTS` partitions `_MECHANICAL` exactly, `receipt_tier()` grades colon-form sources,
`confirms_alone()` requires a Tier-1 receipt, and `SHIPPING_STATUSES`/`RUNTIME_DISPOSITIONS` match
their fixed literal sets.

`test_models.py` gained coverage for `Finding.receipt_tier` — defaults to `None`, round-trips a
set value through `to_dict`/`from_dict`, and an absent key loads as `None`.

`test_findings_gate.py` gained coverage for the tier-model gate (breaking): a `confirmed` finding
with only Tier-2 receipts (`ripgrep`, `ast-grep`, `structural-index`, `tree-sitter`) is now
rejected, a Tier-1 receipt (e.g. `codeql:dataflow`) still passes, an out-of-vocabulary
`runtime_disposition` is rejected, and `receipt_tier` is stamped onto the finding file as a side
effect of `validate_findings`. `test_driver.py` gained
`test_findings_gate_action_halts_on_error`, confirming `_act_findings_gate` now raises
`PhaseHalt` (previously validated silently) when the gate reports any error.

`test_findings_gate.py` also gained coverage for `validate_citations`: an unresolved `file:line`
citation is rejected, a genuine `line: 1` anchor on real code survives, a placeholder `line: 1`
anchor on a missing file is rejected, a `candidate`-status finding is not gated, and a control
finding (`context.control_findings`) forced to `confirmed` status is rejected the same way once
its doc-cited file doesn't exist under the target root.

`test_models.py` gained coverage for `Finding.impact` — defaults to `""` and round-trips a set
value through `to_dict`/`from_dict`; an old finding dict with no `impact` key loads blank.
`test_findings_gate.py` gained coverage for the new gate rule: a `SHIPPING_STATUSES` finding with
blank `impact` is rejected, a non-shipping finding with blank `impact` is not.
`test_report.py` gained coverage that `render_finding`'s §4 Impact renders the finding's real
`impact` text and that the constant §6 Confirmed Attack Scenario / §8 Testing strings are gone
(ISSUE-052); the existing full-tier section-presence test was updated to match.

When you add or change a test file, update this README's counts and guard list in the same commit
(enforced by the pre-commit hook).

The review-improvements test files (`test_cluster.py`, `test_scope.py`, `test_selfscore.py`,
`test_sarif.py`, `test_calibrate.py`, `test_report.py`) are `ruff format`-clean; run `ruff format`
before committing edits.

`test_selfscore.py` gained `test_shipping_counts_full_set`, covering `build_self_score`'s new
`shipping` count over `evidence.SHIPPING_STATUSES`.

`test_redteam.py`'s red-team bar tests now cover the coverage-first `_above_bar`: severity above
the floor earns a directive with no receipt required; the dead `prime-manual-test` history test
is removed, and `test_lead_carrier_without_receipt_is_not_a_directive` is replaced with
`test_lead_carrier_without_receipt_is_still_a_directive` reflecting the new bar.

`test_redteam.py` gained four payload-reachability tests (ISSUE-056):
`test_untraceable_payload_is_unrunnable`, `test_traced_payload_is_runnable`,
`test_reachable_dict_alone_is_runnable`, and `test_discriminate_buckets_unrunnable_separately`,
covering the new `payload_runnable` gate and the `discriminate` `"unrunnable"` bucket. Pre-existing
`_rt`/`_f`-built fixtures that reach `needs_runtime` now set a `dataflow` trace so they exercise
severity/bar/sort logic, not payload traceability.

`test_redteam.py` gained `test_render_plan_surfaces_unrunnable_findings_not_dropped` (ISSUE-056
fix round 1): asserts an unrunnable finding's id appears in `render_plan`'s new "Unrunnable
preconditions" section — a recall regression guard proving these findings are surfaced, not
silently dropped from the plan.

`test_phase_gate.py` gained five tests for `_parse_ref`'s trailing-hint stripping (plain
path:line, range-anchor, trailing hint after line/range, bare path, unparseable line).

`test_phase_gate.py` gained three tests for the new `attack_surface_gate`: a surface backed by a
non-comment code line passes, a surface backed only by a comment line is rejected, and a surface
with no evidence at all is rejected.

`test_prompts.py` (new) covers `prompts.render_prompt`: all tokens filled, an unfilled token
raising `ValueError` that names it, and extra unused `subs` keys being ignored.

`test_route_control.py` (new, ISSUE-027/029/036) covers `route_control.py`: a table control the
architecture markdown omits is a `needs_follow_up` gap, a table entrypoint the threat model drops
is a gap, no gap when everything is present, and `record_route_gaps` round-trips a gap's
`reason`/`next_step` through `kb/coverage-ledger.json` while `validate_coverage_ledger` still
returns no errors. Word-boundary gap tests pin the fix for substring false-negatives: a control
that is a substring of a longer word (`auth` inside `authorization`) is still a gap, the same
control as a standalone token is covered, and an entrypoint carrying path punctuation (`/login`)
still matches as a standalone mention.

`test_class_ext.py` (new) covers `class_ext.py`: an alias map (sqli/cmdi/xss → injection.md)
counts coarse extension files, direct files count by name, and uncovered classes log gaps so
coverage is never silent.

`test_sast.py` gained `test_semgrep_excludes_sidecar` to verify `run_semgrep` includes
`--exclude` flags for `.sec-overlay`, `.git`, `.venv`, and `node_modules` directories via
the `_SKIP_DIRS` tuple.

`test_report.py` gained `test_bottom_line_counts_in_words` (ISSUE-010): the bottom-line
`Confirmed:` line renders counts in words (`"1 critical, 1 high, 2 medium, 1 low"`), never as a
digit ratio (`"1/1/2/1"`); the pre-existing NDT-separation test was updated to the words format.

`test_report.py` gained `test_short_title_cuts_on_word_boundary` and
`test_short_title_no_cut_when_short` (ISSUE-011): `_short_title` trims a triage title to a word
boundary with a trailing `…`, never cutting mid-word, and leaves short titles untouched.

`test_prefilter.py` gained `test_candidate_ids_are_class_prefixed_and_per_class_numbered`
(ISSUE-013): `_assign_candidate_ids` now numbers candidates per attack class
(`C-SQLI-0001`, `C-XSS-0001`, ...) instead of one global `C-0001..` sequence, so ids carry the
class and never collide across rulesets; `test_serial_and_concurrent_identical` was updated to
the new scheme.
