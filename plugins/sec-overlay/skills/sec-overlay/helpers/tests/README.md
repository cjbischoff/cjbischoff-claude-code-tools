# `tests/` — the deterministic test suite

98 pytest files, 1021 tests. Run from `helpers/`: `uv run pytest -q`. Two failures on a clean
checkout are environmental (gitignored bench corpus, excluded semgrep submodule) — see the skill
[`CLAUDE.md`](../../CLAUDE.md) §1.

`test_cli.py` covers `run_review` mapping the coverage-manifest seal to an exit code: a
`complete` seal returns 0 (including a diff with zero reviewable files), a `partial` seal
returns 3 and prints one "unfinished file" line per non-`done` manifest entry naming its path,
state, and note, and the same mapping holds through the `main()` entry point. A fake
`parse_hunks` raises for chosen paths to force the `failed` transition that a `partial` seal
requires — the production `file_diff_text`/`parse_hunks` pair never raises on its own.

`test_report.py` covers `render_dropped_findings_section` (three drops, the empty-list
none-dropped statement, input-order preservation), `to_markdown` wiring both the
dropped-findings and position-review sections after the findings body even when both are empty,
and `write_report` writing `review_ledger.json` once from the same `dropped`/`position_reviews`
arguments it renders into the markdown report, with the markdown row count and the ledger's
`dropped` count asserted equal.

`test_phase_gate.py` covers `review_position_gate`: a three-way kept/dropped/declines split of
findings against diff hunks, using `diffhunks.hunk_for_line` on the resolved position — including
both hunk-boundary adjacency edges and drop-list sort/idempotency checks.
`test_needs_position_review_is_a_decline_not_a_drop_or_keep` asserts `declines` holds the
`PositionResult` `resolve_position` returned, not the raw `Finding` (CR-01 regression); the
`test_report.py` companion,
`test_review_position_gate_declines_compose_directly_into_write_report`, pipes a real
`review_position_gate` decline straight into `write_report(position_reviews=...)` with no
adapter, proving the two modules' contracts actually compose.

New `test_review_coverage.py` (23 tests) and `test_diffhunks.py` (18 tests) bring
`CoverageManifest` and `parse_hunks` to full behavior (DIFF-03, DIFF-04): every legal and
illegal state transition, the empty-manifest seal refusal, atomic-write round-tripping through
`load`, absent/zero hunk counts, CRLF and no-newline-marker handling, a frozen `Hunk` with tuple
collections, and a three-path lifecycle plus a contiguous `line_in_hunk` sweep proving the parser
and the membership check agree over a full hunk range. `test_review_tracer.py` is unchanged and
still green.

New file `test_review_tracer.py` (6 tests) covers the `sec-overlay review` tracer path end to
end: `main(["review", ...])` with a fake `subprocess.run` injected at the module level (`cli.py`
looks up `subprocess.run` inline at call time, so a `monkeypatch.setattr(subprocess, "run", ...)`
reaches it through every `runner=` default) exits 0 and seals `artifacts/coverage_manifest.json`
`complete`; plus focused tests for `validate_ref`'s leading-dash rejection, `parse_hunks`/
`added_line_numbers`, `resolve_position`'s exact match, `review_position_gate` keeping an
in-hunk finding, and `changed_file_records`' `--name-status` parsing.

`test_workspace.py` gained 4 tests for `Workspace.artifacts` (default path resolves under root,
a `reports_dir` override does not redirect it, `ensure()` creates it, `ensure()` is idempotent).

`test_patch_status.py`'s fake-runner helper is now a small `_Runner` class with `calls` as a
real instance attribute, instead of monkey-patching an attribute onto a plain function object
(`ty` cannot type a dynamically-added function attribute) — no behavior change.

`test_rule_matcher.py`, `test_bucket_b.py`, and `test_calibrate.py` add an explicit
`is not None` assertion before dereferencing an `X | None` call result the test already
knows is non-`None` at that point — `ty` needs the narrowing spelled out; no behavior change.

`test_bench.py`'s `CorpusEntry` builder and `test_profile.py`'s `ScanProfile` roundtrip test
apply the same `dataclasses.replace` fix as the `Finding` builders below, for the same
`ty` reason — no behavior change.

`test_citations.py`, `test_factcheck_baseline_envelope.py`, and `test_report.py`'s `Finding`
test-builders (`_f`/`_tf`/`_full`) now build a base `Finding(...)` call and layer per-test
overrides with `dataclasses.replace(base, **kw)`, instead of a `dict()` + `.update(kw)` +
`Finding(**d)` construction — `**d`'s inferred concrete dict type tripped `ty`'s
per-field argument checking that `replace`'s `**changes: Any` typing bypasses. Clears the bulk
of the VAL-02 ty ledger (`invalid-argument-type` diagnostics across all three files); no
behavior change — `Finding` is not frozen, so post-construction mutation still works.

`test_postflight.py` and `test_structural_index.py` clear the last two VAL-02 ruff findings:
a single-element list-slice becomes `next(...)` (`RUF015`), and a `"\n".join([...])` becomes
adjacent string-literal concatenation (`FLY002`) — both no-op on behavior.

`test_prefilter.py` and `test_wiring.py`'s `Exclusions([], [], [])` fixture calls now pass
`Exclusions(set(), [], set())` — `Exclusions.rule_ids`/`classes` are `set[str]` fields, so the
prior `list` literals type-checked incorrectly under `ty` even though the runtime behavior
(both accept iteration) was unaffected.

New `test_command_audit.py` covers the load-bearing content of `/sec-overlay:audit`: the command file documents routing (`/sec-overlay:audit`), single-repo driver (`run.drive`), multi-repo confirmation step, and the `correlate` CLI with required `--out` flag.

`test_kb.py` gained `test_new_tree_paths` for `kb.py`'s new arc42/threat-model tree path helpers;
`test_workspace.py` gained `test_ensure_creates_trees`, pinning that `Workspace.ensure()` creates
`architecture/runtime-view/` and `threat-model/attack-sequences/`.

New `test_ste_lint.py` covers `sec_overlay.ste_lint.lint_prose`: clean prose passes; a >25-word
sentence, a semicolon in prose, and a >6-sentence paragraph each produce an error; a semicolon
inside a code span or fenced code block is exempt; a heading and a table separator row are
exempt but a semicolon inside a table cell is still flagged; a 4-word capitalized run and a
sentence repeating " then " each produce a warning, not an error.

`test_ste_lint.py` gained three fix-round regression tests: an unterminated code fence with a
real semicolon violation after it reports an `"unbalanced"` error instead of silently linting
nothing; a paragraph using "e.g." twice across three real sentences produces no false
"over 6 sentences" error; and a 30-word sentence containing "e.g." mid-sentence is still
flagged as over 25 words rather than being fractured into two short sentences.

New `test_cvss4_data.py` covers the vendored CVSS v4.0 data: `MACROVECTOR_LOOKUP` has >250
six-digit-key entries with scores in `[0, 10]`, and `MAX_COMPOSED`/`MAX_SEVERITY` are nonempty.

New `test_references_caps.py` checks `references/mermaid-caps.md`'s cap table against
`sec_overlay.diagram_gate.CAPS`/`SEQ_CAPS`, so the doc and the gate never drift apart.

`test_cvss.py` fully rewritten for the v4.0 engine: 25 reference vectors pinned to NVD's published
`cvssMetricV40` base scores (`E:X` only, so no threat-metric ambiguity), plus band/bounds/rejection
and `offensive_priority` tests.

`test_calibrate.py`'s CVSS fixtures migrated to CVSS v4.0 vectors (expectations recomputed from the
real `cvss40_base` engine, not guessed); it now collects and passes against the re-pointed
`calibrate.py`.

New `test_artifact_gate.py` (§4.8) covers `run_artifact_gate`: a clean run passes; a stale constant
section, a missing detail file, a missing red-team directive, and a triage ID with no matching
finding each produce an error string; the gate always writes `kb/gates/artifact-gate.json`. Also
covers `check_duplication`: a duplicated heading and a threat-model-owned structure heading each
fail, distinct headings pass, and the gate skips the check silently when the arc42/threat-model
trees are absent.

New `test_redteam_gate_paths.py` verifies the red-team gate path split (O-65): `redteam-adversary.md`
declares `kb/gates/redteam-adversary.json` and does not contain the old `kb/gates/redteam.json`,
avoiding collision with `redteam.py:357`'s gate path.

`test_stage_validate.py` gained `test_unknown_stage_raises` (ISSUE-034): `validate_stage` now
raises `ValueError` for an unregistered stage instead of silently passing. `test_bucket_c.py`'s
`test_stage_validate_dispatch` updated to expect the same raise for `"unknown-stage"`.
`test_prefilter.py` gained `test_strict_raises_when_planned_backend_skipped`,
`test_strict_ok_when_all_ran`, and `test_run_prefilter_raises_strict_by_default_on_skipped_backend`
for the new `_raise_on_incomplete_backends` helper and `run_prefilter(..., strict=True)` default;
every existing test that deliberately exercises a skipped/failed backend now passes `strict=False`.
It also gained `test_strict_ignores_disabled_backend` and `test_strict_raises_on_absent_backend`
(R14): a `"disabled"` skip reason is excluded from the strict raise, but `"absent"` and other
reasons still raise.

`test_cost.py` gained `test_record_and_aggregate_timings` (ISSUE-014), covering the new
`cost.record_timing`/`cost.aggregate_timings_by_phase` per-phase wall-clock accounting.

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

`test_stage_validate.py` gained `test_context_validator_flags_cited_doc_missing_from_docs_read` and `test_context_validator_ok_when_cited_doc_present` (ISSUE-021) — the `context` stage-validator rejects a `source_doc` citation absent from `provenance.docs_read`.

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
`outputs_present`, `next_actionable_phase`). `test_artifact_phases_follow_selfscore` (new, §4.8)
asserts `artifact-gate` sits after `selfscore` and `artifact-review` sits after `artifact-gate`,
and that `artifact-review` is an agent phase naming `agents/artifact-review.md`.
`test_arch_tm_gate_rows` (new) asserts the deterministic `arch-gate`/`tm-gate` rows sit immediately
after `architecture`/`threat_model`.

`test_driver.py` covers `sec_overlay/driver.py`'s `run_deterministic_phase`: raises
`PhaseHalt` on a missing input, raises `PhaseHalt` when the action ran but a declared output is
still absent, records the stage `"done"` on success, and (`test_deterministic_phase_records_timing`,
ISSUE-014) records the phase's wall-clock seconds into `state.budget["timings"]` via
`cost.record_timing`. Also covers `render_dispatch`: the
returned block names the `agents/<prompt>` file and the substituted target/workspace/SHA, and now
`test_dispatch_is_secret_redacted` asserts the block is passed through `redactor.safe_for_prompt`
before returning (ISSUE-051). `test_act_arch_gate_halts_on_cap_breach`,
`test_act_arch_gate_ignores_absent_threat_model_tree`, and
`test_act_tm_gate_halts_when_dfd_missing` (new) cover `_act_arch_gate`/`_act_tm_gate`: a diagram
cap breach halts and still writes the gate JSON, an absent threat-model tree does not halt
`arch-gate`, and a missing `dfd.mmd` halts `tm-gate` (`require_threat_model=True`). Three
`run_audit` tests (new) cover the resumable table-walker:
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

`test_act_artifact_gate_halts_on_error` (new, §4.8) writes a `report.md` containing a banned
constant fragment and asserts `driver._act_artifact_gate` raises `PhaseHalt`, covering the new
`artifact-gate` phase's registered action (wraps `artifact_gate.run_artifact_gate`).

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

`test_selfscore.py` gained `test_self_score_counts_critic_reject_rate` and
`test_self_score_reject_rate_zero_without_critic_events` (ISSUE-043), covering the new
`critic_viable`/`critic_rejected`/`critic_reject_rate` keys counted from history events.

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

`test_coverage_ledger.py` gained cases for `build_coverage_ledger`'s own `needs_follow_up`
surfaces now carrying `reason`/`next_step`: `validate_coverage_ledger` rejects one missing
either field, accepts one carrying both, and `render_markdown` renders both columns.

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

`test_report.py` gained `test_economics_renders_timing` (ISSUE-014): `to_markdown` renders a
"Wall-clock by phase" list under "Run economics" when `economics["by_phase_seconds"]` is given.

`test_prefilter.py` gained `test_candidate_ids_are_class_prefixed_and_per_class_numbered`
(ISSUE-013): `_assign_candidate_ids` now numbers candidates per attack class
(`C-SQLI-0001`, `C-XSS-0001`, ...) instead of one global `C-0001..` sequence, so ids carry the
class and never collide across rulesets; `test_serial_and_concurrent_identical` was updated to
the new scheme.

`test_report_split.py` (new, ISSUE-009) covers the per-finding-file report split:
`write_report` writes `findings/<ID>.md` for every reportable/NDT finding, `report.md` links each
one under "## Detail" instead of inlining its body, and the Detail list is risk-ordered. Six
pre-existing `test_report.py` assertions that expected the old inline "Confirmed
(source-provable)"/"Needs runtime proof" bodies (verification text, receipts, `Caution` notes,
section headings) were updated to check the new `findings/<ID>.md` files or the "## Detail" link
list instead.

The `_full` helper in `test_report.py` builds its `Finding` kwargs as a dict literal (not a
`dict()` call) to satisfy ruff `C408`.

`test_cvss.py`'s `sec_overlay.cvss` import is wrapped across multiple lines to satisfy ruff
`I001` (the single-line form exceeded the 100-char limit).

`test_report.py`, `test_models.py`, `test_citations.py`, and `test_factcheck_baseline_envelope.py`
had their fixture `cvss_vector` strings swapped from `CVSS:3.1` to `CVSS:4.0` vectors of
equivalent meaning, matching the v4.0-only parser (`sec_overlay/cvss.py`). `test_cvss.py`'s own
`CVSS:3.1` fixture is untouched — it exercises the parser's rejection path.

`test_mermaid_index.py` (new) covers `sec_overlay.mermaid_index.index_mermaid` against flowchart,
sequence, and C4 fixtures: node/edge/subgraph/store-id extraction, sequence participant order and
message count, `has_style` detection, and a `ValueError` on an unrecognized diagram header.

`test_flowchart_mid_label_edge` added to `test_mermaid_index.py`: covers the `a -- label --> b`
mid-arrow-label form, asserting the edge triple and that the label text never appears as a node.

`test_c4_index` widened to expect `store_ids == {"user", "db"}`: `Person(...)` and `*_Ext(...)`
element ids are orphan-exempt required shapes, same as `ContainerDb`/`SystemDb`/`*Queue`.
`test_flowchart_edge_with_inline_source_label` (new) pins a fix to `mermaid_index.py`'s edge
regexes: an edge whose source node carries its own inline bracket label on the same line
(`web[Web] --> api[API]`) now parses — it previously produced zero edges, silently dropping
every such edge.

New `test_diagram_gate.py` covers `sec_overlay.diagram_gate`: node/participant/message caps
(`CAPS`, `SEQ_CAPS`), the ≤4-word edge-label rule, DFD trust-boundary-subgraph requirement,
derivation provenance (`%% derived-from: <file> sha256:<hash>` — missing header, stale hash, and
an element/participant absent from the named source all fail), legend-required styling, and the
orphan-detail check (a node that only ever receives — never a source — and isn't a store/actor
is flagged; a chain's entry node, which is naturally out-degree-only, is not). Per design spec §6
(R4), the orphan check runs only for `container`/`component`/`dfd` — never `context` or
`sequence`, since context actors are by definition often degree-1.

Crash-path hardening round (fix review findings F1–F4): `test_provenance_missing_source_reports_error_not_crash`
and `test_attack_sequence_missing_parent_does_not_crash` pin `_provenance`'s guard against a
missing derived-from source (both the direct-missing-file case and `_attack_parent`'s
`MISSING-PARENT` placeholder) — an error string, not a `FileNotFoundError`.
`test_source_diagram_unparseable_does_not_crash` pins the same treatment for a garbage source
diagram (`ValueError` from `index_mermaid` now becomes an `"unparseable"` error string, not an
uncaught traceback). `test_double_brace_source_not_orphan` (plus
`test_flowchart_edge_with_double_brace_source_label` in `test_mermaid_index.py`) pins the fix to
`_INLINE_LABEL_SKIP`: it only spanned single-char bracket pairs and missed multi-char forms like
`q{{Queue}}`, silently dropping the edge and false-flagging the source node as an orphan. Three
previously-untested branches are now pinned directly: `test_sequence_message_cap` (the message
half of `SEQ_CAPS`), `test_target_diagram_unparseable_returns_error` (the top-level `check_diagram`
parse-failure branch), and `test_style_with_legend_passes` (a styled diagram with a legend present
passes clean).

Diagram-gate parsing-gap round: `test_mermaid_index.py::test_chained_flowchart_edges` pins a
chained edge line (`a --> b --> c`) recording both hops, not just the first.
`test_hyphenated_sequence_participant_and_message` and
`test_unhyphenated_sequence_messages_still_parse` pin hyphenated participant/message ids
(`auth-api`) parsing correctly (message count, participant list, edge tuple) alongside the
existing unhyphenated forms (`a->>b`, `a--)b`, `a-xb`). `test_diagram_gate.py` gained
`test_empty_threat_model_passes_by_default` / `test_empty_threat_model_fails_when_required` for
the new `require_threat_model` gate flag, and `test_node_label_over_four_words_fails` /
`test_bare_id_node_label_not_flagged` for the new node-label word-count check.

New `test_run.py` covers `sec_overlay.run.fence`: passes when the current `git status --porcelain`
output matches the captured baseline, raises `WorkingTreeFenceError` naming the delta lines
otherwise.

`test_run.py`'s unused `pathlib.Path` import (leftover from the initial draft) was removed to
satisfy ruff F401; `tmp_path` already provides a `Path` instance via the pytest fixture.

`test_run.py` gained `test_receipt_writes_counts_even_when_stdout_empty`, covering
`sec_overlay.run.receipt`: writes `<ws.kb>/receipts/<phase>.json` with the `phase`, `stdout`,
`artifacts`, and `counts` keys, and returns that path.

`test_run.py` gained `test_write_env_writes_all_tokens`, covering `sec_overlay.run.write_env`:
writes `<ws.root>/run.env` with `TARGET`, `WORKSPACE`, `SHA`, `SCAN_SCOPE`, and `REPO_ROOT` lines
and returns that path.

`test_run.py` gained three `infer_role` tests, covering `sec_overlay.run.infer_role`: a dict-form
`subsystems` entry named `rbac-policy`/`identity` returns `rbac-source`, a network `attack_surface`
returns `service-enforcer`, and an ambiguous profile defaults to `infra`.

`test_run.py` gained two `synthesize_manifest` tests, covering `sec_overlay.run.synthesize_manifest`:
a valid two-member call passes `validate_manifest` with distinct `slug#scan_scope` keys, and a
member with a role outside `ROLES` raises `ValueError`.

`test_run.py` gained `test_drive_writes_receipt_and_env_and_fences`, covering `sec_overlay.run.drive`:
with a fake git runner reporting a clean tree at every call, one deterministic `noop` phase runs,
`run.env` and `kb/receipts/noop.json` both exist afterward, and the result is `"AUDIT COMPLETE"`.

`test_driver.py` gained `test_run_audit_calls_on_complete_before_recording`, covering the new
`on_complete` parameter on `driver.run_audit`: for a single deterministic phase whose output already
exists, `on_complete` is called with the phase name before `run_audit` returns `"AUDIT COMPLETE"`.

`test_run.py` keeps its import block sorted (ruff I001) — the local `sec_overlay` import in
`test_synthesize_manifest_rejects_bad_role` is separated by a blank line.

`test_run.py` gained `test_load_baseline_persists_and_fences_a_later_cross_invocation_write`,
covering `sec_overlay.run._load_baseline`: the first call captures and persists the baseline to
`<ws.kb>/fence-baseline`; a later call with a dirty runner still returns the persisted clean value,
and fencing against it raises `WorkingTreeFenceError`. It also gained
`test_advance_writes_receipt_records_stage_and_fences_persisted_baseline`, covering
`sec_overlay.run.advance`: a clean-tree call writes a receipt and records the stage; a later dirty
call raises `WorkingTreeFenceError` against the still-persisted baseline. The dead
`monkeypatch.setattr(run_mod, "_PHASE_TABLE", ...)` line in `test_drive_writes_receipt_and_env_and_fences`
(a `raising=False` no-op — `drive` takes `table=`, not `_PHASE_TABLE`) was removed.

`test_command_audit.py`'s `--out` assertion comment now reads "correlation output lands under the
CWD (artifacts/)", matching the corrected `audit.md`.

`test_diffscope.py` grew from 2 to 22 tests, covering the full ref-validation and
`changed_file_records` behavior: allowlisted refs including `HEAD~1`, an empty-ref rejection, a
leading-dash rejection with allowlisted rest, four shell-metacharacter rejections, an empty diff,
emitted-order preservation, rename and copy records each carrying `old_path`, `file_diff_line_count`,
`binary_paths`, and a call-order test proving `rev-parse` always precedes `diff` and no raw ref
ever reaches a `diff` argv, plus `resolve_ref_sha`'s own success and raise-on-nonzero-returncode
cases (CR-02 regression: a syntactically valid but nonexistent ref used to resolve to `""` instead
of raising). `test_cli.py` gained three `review` exit-2 tests: a leading-dash `--base`, an empty
`--base`, and an unresolvable-but-valid `--base` fed through a fake runner returning
`returncode=128` — each asserting `rc == 2` and a stderr line naming the ref.

`test_file_select.py` is new (63 tests): parametrised checks over ten representative
`ALLOWED_EXTENSIONS` entries plus one absent extension, case-insensitive extension matching, a
no-extension path, one parametrised test per `DEFAULT_EXCLUDE_GLOBS` entry matching its own
documented example path directly with `fnmatch.fnmatch` (not the `_is_generated` aggregate,
which would hide a broken pattern behind an overlapping one), generated-beats-allowlisted
precedence, non-ASCII path-quoting normalization, an empty-input case, deleted/binary exclusion,
both sides of the `DEFAULT_MAX_DIFF_LINES` boundary, `ExcludedFile` rejecting a reason outside
`EXCLUSION_REASONS`, and a fixture-set walk asserting every produced reason is in the enum.

`test_positioning.py` is new (30 tests), covering the never-guess positioning ladder in
`positioning.py`: `_match_consecutive`'s exact whitespace-stripped consecutive-line matching
(single/multiple/no occurrence, empty needle, needle longer than haystack, no case folding);
`PositionResult.__post_init__` rejecting an `exact`/`relocated` result with no line, a
`needs-position-review` result carrying a line, and an unknown decision or reason outside the
closed vocabularies; and all four `resolve_position` rungs in order — hunk match (`exact`,
declining to `ambiguous-multiple-matches` on two hits), whole-file match in the claimed file
(`relocated`/`whole-file-match`), match in exactly one other changed file
(`relocated`/`cross-file-match`, declining to `cross-file-ambiguous` on two hits), and the
final no-match decline (`no-hunk-match`). Also covers an absent/whitespace-only snippet
declining before any rung runs (`no-snippet`), an absent claimed path declining rather than
raising, rung-order precedence (rung 1 beats rung 2 even when rung 2 would also match),
determinism across repeated calls, and every result — including declines — carrying the
original `claimed_path`/`claimed_line`/`snippet`.

`test_review_tracer.py`'s `_FakeFinding` gained an `evidence` attribute (default
`"os.system(cmd)"`, matching its fake diff's one added line) so
`test_review_position_gate_keeps_finding_on_added_line` exercises a genuine rung-1 hunk match
through `resolve_position`'s five-argument signature, instead of the position gate short-circuiting
on a missing snippet.

`test_report.py` gained coverage for the new additive `report.py` symbols (D-13, POS-02):
`render_position_review_section` on three declined `PositionResult`s renders one
`## Position review required` table row per result with claimed path, claimed line, snippet, and
reason; on an empty list it still renders the heading plus an explicit
"No finding required position review" line; a pipe character in the snippet is escaped so it
cannot be read as a table delimiter, and a multi-line snippet collapses onto one row.
`write_review_ledger` writes `artifacts/review_ledger.json` with a `position_reviews` entry per
decline (`state: "needs-position-review"` plus claimed path/line, snippet, reason) and always
carries the `position_reviews`/`dropped` keys, even when both are empty; the JSON round-trips
every field, and calling it twice leaves one valid file holding the second call's data. Both
symbols ship in plan 02-04, task 3.
