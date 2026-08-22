# `tests/` — the deterministic test suite

108 pytest files, 1285 tests. Run from `helpers/`: `uv run pytest -q`. Two failures on a clean
checkout are environmental (gitignored bench corpus, excluded vendored semgrep clone) — see the
skill [`CLAUDE.md`](../../CLAUDE.md) §1.

The fake-response `R` classes in `test_review_tracer.py` and `test_diffscope.py` declare
`stdout = ""` as a class attribute so `ty check` resolves the attribute; behavior is unchanged.

`test_stage_validate.py` covers the `_adapt_dict` / `_adapt_optional_dict` rejection paths:
a non-dict output for a dict-adapted stage returns `["stage output must be an object"]`, a
non-dict non-None output for `reachability` returns `["stage output must be an object or null"]`,
and `None` for `reachability` passes through to the wrapped validator without rejection.

`test_cli.py` covers `run_review` mapping the coverage-manifest seal to an exit code: a
`complete` seal returns 0 (including a diff with zero reviewable files), a `partial` seal
returns 3 and prints one "unfinished file" line per non-`done` manifest entry naming its path,
state, and note, and the same mapping holds through the `main()` entry point. A fake
`parse_hunks` raises for chosen paths to force the `failed` transition that a `partial` seal
requires — the production `file_diff_text`/`parse_hunks` pair never raises on its own.
`test_review_excludes_oversized_diff_via_wired_diff_line_counts` spies on `cli.partition` to
capture the `Selection` it returns and asserts a >5000-line fake diff lands in
`selection.excluded` with reason `too-large`, not `selection.reviewable` (CR-03 regression:
`run_review` used to call `partition(records)` with no `diff_line_counts`/`binary_paths`, so
the size cap and binary exclusion never fired from the CLI).
`test_review_writes_ledger_and_report_with_zero_drops_and_declines` and
`test_review_ledger_drop_count_matches_markdown_drop_rows` cover `run_review` wiring
`review_position_gate`'s `(kept, dropped, declines)` into `report.write_report`: the
zero-drop/zero-decline case still writes both `report.md`'s none-dropped/none-required
sentences and an empty-list `review_ledger.json` (T-02-15), and a monkeypatched gate
returning canned drops asserts the markdown drop-row count equals the ledger's drop count
(T-02-18).

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

`test_review_tracer.py` (16 tests) covers the `sec-overlay review` tracer path end to
end: `main(["review", ...])` with a fake `subprocess.run` injected at the module level (`cli.py`
looks up `subprocess.run` inline at call time, so a `monkeypatch.setattr(subprocess, "run", ...)`
reaches it through every `runner=` default) exits 0 and seals `artifacts/coverage_manifest.json`
`complete`; plus focused tests for `validate_ref`'s leading-dash rejection, `parse_hunks`/
`added_line_numbers`, `resolve_position`'s exact match, `review_position_gate` keeping an
in-hunk finding, and `changed_file_records`' `--name-status` parsing. Nine more tests (Phase 3
Plan 1) cover the `rule_glob`/`reflection` wiring: a `.py` file resolving `rule_docs/python.md`
and an allowlisted-but-unmatched `.rb` file falling back to `default.md` (an `.rst` path would
never reach `rule_glob` at all — `file_select`'s `ALLOWED_EXTENSIONS` excludes it upstream,
D-09) through `run_review(..., profile="security")`'s `review_ledger.json["rule_docs"]`;
`expand_braces` (first-group-only) and `glob_match` (`**` and case-insensitive) unit cases;
`resolve_rule_doc` first-match-wins against a monkeypatched map; `reflection.apply_verdict`
retracting a submitted id, ignoring an unsubmitted one, and refusing to retract a protected
subject class; and `test_review_zero_findings_still_renders_reflection_sections`, pinning that
a zero-finding run still writes `reflection_retractions`/`reflection_skipped` as empty lists
(never omitted) in the ledger and renders the "## Reflection retractions" heading in
`report.md` (D-14/D-15 never-silent discipline). Its one protected-subject test now also asserts
the refused retraction is recorded (`REFUSED_REASON`), never a silent `[]` (Phase 3 Plan 05).

`test_reflection.py` (16 tests, Phase 3 Plan 05 Task 1) covers `reflection.py`'s prompt-rendering
and verdict-validation half of the retract-only filter: `render_reflection_prompt` substituting
`{{PATH}}`/`{{DIFF}}`/`{{COMMENTS}}`, all five `PROTECTED_SUBJECT_CLASSES` phrases and the
ordered method-step headings (veto before Ground A before Ground B before "when in doubt")
appearing in the rendered text; `validate_verdict` accepting `approve_all_comments` (retracts
nothing), accepting `report_incorrect_comments` for a submitted id, ignoring extra fields
(severity/message/add_finding), and raising `ReflectionResponseError` on an unsubmitted id,
invalid JSON, or an unnamed tool; and one parametrized test per protected subject class proving
`apply_verdict` refuses the retraction (finding stays in `kept`) while still recording it
(`REFUSED_REASON`, distinct from `RETRACTED_REASON`) — plus a mutation test proving `apply_verdict`
never mutates its input list. Six more tests (Task 2) cover the ledger's markdown-rendering half:
`render_reflection_skipped_section` renders "No file was skipped." when empty and a
path/reason/error row per `ReflectionSkip`; `to_markdown` renders `REFLECTION_SKIPPED_HEADING` even
with zero findings; `write_review_ledger` writes a `reflection_skipped` key matching the dataclass
fields, keeps applied and refused retractions in the same `reflection_retractions` list, and never
writes a second `*reflection*.json` artifact file.

`test_review_agent.py` (12 tests, Phase 3 Plan 06 Task 1) covers `review_agent.py`'s prompt
render and response parse, monkeypatching `_review_file_template_path` to a `tmp_path` fixture
template so it needs nothing from `agents/review-file.md` (Task 2's file): `render_review_prompt`
substituting all four content tokens and raising on a genuinely unfilled one (distinct from
simply omitting a placeholder, which raises nothing); a `code_comment` for the reviewed path
converting to one `Finding`, one for a different path being discarded and counted rather than
converted; a `task_done`-only response yielding an empty list with no raise; a model-supplied
`evidence_sources` or `status` being overwritten with `REVIEW_AGENT_CLAIM`/`FindingStatus.RAW`
rather than trusted; `evidence.confirms_alone` false for every produced finding; malformed JSON,
an unknown tool, and a missing `line`/`message` all raising `ReviewResponseError`; and two parses
of the same response producing identical finding ids (idempotent re-parse).

`test_rule_glob.py` (new, Phase 3 Plan 2) grows across three TDD tasks. Task 1 (10 tests, green)
covers the four-layer rule resolver: per-path fallthrough (`ProjectRuleEntry`/`ProjectRule`/
`RuleResolution`, custom > project > global > built-in, first-match-wins per path),
`merge_with_system_rule`'s header concatenation and its three empty-input cases, and
`load_project_rule` preserving JSON array match order and idempotent repeated resolution. Task 2
(9 tests, green) covers the structurally separate whole-layer first-non-empty `build_file_filter`
(skips an empty layer, never merges two non-empty layers, lower-cases patterns at build time),
`build_resolution` assembling the three layers and appending CLI `--exclude` values, a case
proving the custom/global layers resolve a relative `rule` field against their own config
directory (not `repo_root`, unlike the project layer), the `--rule`/`--exclude` CLI wiring
reaching `run_review`, and an excluded file never entering the coverage manifest. Every test that
dereferences an `X | None` call result now carries the explicit `is not None` assertion `ty`
needs to narrow the type (same idiom as `test_rule_matcher.py`/`test_bucket_b.py` below) — no
behavior change, but it took `ty check`'s diagnostics on this file from 12 to 0. Task 3 (6 tests,
green) covers the rule-file safety gate (`read_rule_file_safe`, `RuleSafetyError`): the 512 KB
boundary at 524288/524289 bytes, a symlink escaping the repo root, a disallowed extension on the
resolved path (a plain `.yaml` file and a `.md` symlink pointing at one), trailing-newline
stripping with inner blank lines preserved, byte- not character-based sizing on multi-byte UTF-8
text, and `run_review` exiting 2 with the message on stderr and no fallback to another layer.

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

`test_phases.py` gained six tests wiring `redteam`/`postflight` into `PHASE_TABLE` (D-01):
`test_phase_table_contains_redteam_and_postflight` (both names present),
`test_redteam_precedes_the_artifact_gate` (`redteam` sits between `selfscore` and `artifact-gate`
— `artifact_gate.run_artifact_gate` hard-requires `redteam-plan.md`, kind `agent`, prompt
`redteam.md`), `test_postflight_is_the_final_phase` (last table row, kind `deterministic`, no
prompt), `test_original_phase_order_is_preserved` (the 22 pre-existing rows keep their relative
order), and `test_missing_inputs_reports_absent_artifacts_for_the_new_phases` /
`test_outputs_present_tracks_the_postflight_artifact` covering the two new rows' input/output
path helpers against an unensured and an ensured `Workspace`.

`test_driver.py` gained `test_postflight_is_a_registered_deterministic_action` (calls
`DETERMINISTIC_ACTIONS["postflight"]` and asserts `kb/prior_context.json` is written),
`test_redteam_is_not_a_deterministic_action` (redteam stays an agent phase, dispatched via
`agents/redteam.md`, never through `DETERMINISTIC_ACTIONS`), and
`test_every_deterministic_phase_has_a_registered_action` — a table-derived regression guard
iterating `PHASE_TABLE` so a future deterministic phase with no matching action fails loudly
instead of silently no-oping at dispatch time.

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
| `test_docs_invariants.py` | Documentation contracts: prompt-constants block presence, `finding-template.md` sections, agent-prompt rules, the `EVIDENCE_VOCABULARY` block listing every `sec_overlay.evidence` tier/status/disposition value verbatim, the `CLAUDE.md` phase-order block tracking `PHASE_TABLE`'s relative order, and (06-06, WR-01) that no live doc wrongly denies review's --workspace support — premise pinned against `run_review`'s real signature; the matcher covers three denial wordings, with pattern tests pinning both denial and corrected phrasing. |
| `test_frozen_contract.py` | Byte-identity: `models.py`/`evidence.py` are frozen mirrors of a separate Go port (D-15) — a sha256 pin fails loudly on any edit. `fingerprint()` golden-value pins (fully-populated, minimally-populated, field-order-permuted) prove its behavior independent of that byte check. REL-03: `pyproject.toml`'s `[project] dependencies` stays `[]`. |

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

`test_findings_gate.py` (Phase 3 Plan 05 Task 3, 7 new `-k general_defect` cases) covers the
D-12 receipt-gate disposition ladder: `disposition_without_receipt` returns `unconfirmed` for
null dereference, error swallowing, resource leak, and injection (each asserted individually,
injection's explicitly rather than by falling through a default), and
`needs-deployment-testing` for thread safety; an unknown class raises `ValueError`; and a
general-defect finding WITH a Tier-1 receipt still reaches `confirmed` through the unchanged
`confirms_alone` path, proving no reflection outcome or profile value can grant that status.

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

`test_rule_docs.py` (phase 3 plan 03, RULE-05) is a conformance suite over the nine built-in
rule docs, driven entirely from `BUILTIN_PATH_RULE_MAP`, `BUILTIN_DEFAULT_RULE`, and
`REQUIRED_RULE_SECTIONS`/`RULE_SECTION_SYNONYMS` — no filename is hardcoded, so a language added
later needs a map entry and a doc file, never a test edit. It checks every map value (plus
`default.md`) exists and is non-empty, that no doc on disk is an orphan the map never points at,
that every doc's five `####` sections match the five required families in order and each carries
a "Do not report" exclusion block, that the four TS/JS extensions all resolve to
`ts_js_tsx_jsx.md`, that a representative path per language resolves to its own doc, that an
extensionless or unmatched-extension path resolves to `default.md`, that a two-entry map
collision resolves to the first entry (`monkeypatch` on `BUILTIN_PATH_RULE_MAP` and
`builtin_rule_docs_dir`, not real files), and that `resolve_rule_doc` is idempotent.

`test_review_profiles.py` (phase 3 plan 04, REV-01) covers `sec_overlay.review_findings`:
`classify` returns `None` for a non-allowlisted `Finding.cls` and the class itself for each of
the five `GENERAL_DEFECT_CLASSES`; `apply_profile` raises `ValueError` on an unknown profile
name or an unknown gate marking; an unmarked finding is always kept, under both profiles, with
`disposition == UNCONFIRMED_DISPOSITION`; the `security` profile drops every gate-marked
finding regardless of class; the `general` profile bypasses gates A/B for an allowlisted class
but still drops a non-allowlisted gate-A finding and drops gates C/D/E unconditionally even for
an allowlisted class; `apply_profile` never assigns a `confirmed` disposition; dropped findings
sort by `(path, line, rule_id)` independent of input order; and
`EXCLUSION_BLOCK_BY_PROFILE` names the two `prompt-constants.md` blocks a profile selects. The
last two tests are the D-10 dual-run no-regression proof: a synthetic seven-finding fixture
(`_dual_run_fixture`, one finding per gate letter A–E plus one unmarked) run through the
`security` profile must match the committed
`fixtures/review_profiles_security_baseline.json` byte-for-byte — any future change to
`apply_profile` that moves the security profile's kept/dropped split fails this test, which is
the point — and the `general` profile's kept set must be a strict superset of the `security`
profile's kept set on the same fixture, with every added finding carrying a
`defect_class` in `GENERAL_DEFECT_CLASSES`. The baseline-provenance docstring on the first of
these two tests cites `245d9e7`, the commit that added
`fixtures/review_profiles_security_baseline.json`. Both tests carry `dual_run` in their name
(`test_dual_run_security_profile_matches_committed_baseline_no_regression` and
`test_dual_run_general_profile_is_a_strict_superset_of_the_security_baseline`) so `pytest -k
dual_run` selects exactly the D-10 pair.

`test_review_live.py` (new, phase 3 plan 06, REV-02) covers `cli.run_review` wired to a real
finding source end to end: `--prepare` writes a plan entry and rendered prompt per reviewable
file; a recorded `review-file` return produces a nonzero finding count; the same fixture diff
run under `security` then `general` proves the profile split on a live source (a null-dereference
finding excluded under `security`, included under `general`); a finding claimed on a line far
outside every diff hunk is relocated by the position gate's whole-file rung and then dropped with
reason `outside-diff` (not the earlier `no-snippet` decline); a `reflection.apply_verdict`
retraction removes a live finding and the retraction records in the ledger; a file with no
recorded return, a stale base/head return, and an unparseable return each land in
`review_source_skipped` without stopping the run for other files; and the CLI's existing exit
codes (2 on an invalid ref, 3 on a partial seal, 0 on a complete one) are unaffected by the new
finding-source wiring. The fake runner's `git show <ref>:<path>` branch returns a whole-file text
reconstructed from the fixture diff by default, or an explicit override
(`head_texts` parameter) for the one test that needs a claimed line outside the diff-derived
content. `test_rule_glob.py`'s `fake_run_review` local fixture gained a `prepare: bool = False`
keyword to match `run_review`'s signature; `test_cli.py`'s `test_review_ledger_drop_count_matches_markdown_drop_rows`
monkeypatch of `review_position_gate` gained a matching `file_text_by_path=None` third parameter.

Phase 3 plan 07 (Task 1, REV-02 gap closure) tightens and extends `test_review_live.py`'s
reflection coverage. `test_reflection_retraction_removes_a_live_finding` now asserts
`ledger["review_findings"] == []` after the faked retraction (the finding's actual absence,
not just the retraction entry's presence — the assertion this test previously stopped short
of). `test_reflection_failure_for_one_file_leaves_other_files_unaffected` covers two changed
files: a fake `apply_verdict` that raises for one path and passes the other through
unretracted proves a per-file reflection failure lands only in `reflection_skipped` for the
raising path, while both files' findings still ship in `review_findings`.
`test_finding_on_an_unreflected_path_survives` monkeypatches `review_position_gate` to inject
an extra finding on a file absent from `selection.reviewable`, proving the reflection loop's
rebind-by-filter never touches a finding on a path it never iterates (D-14, no silent drop).

Phase 3 plan 07 (Task 2, REV-03 gap closure) extends `test_review_profiles.py` with the D-12
disposition ladder proof `apply_profile` skipped until now.
`test_apply_profile_assigns_needs_deployment_testing_for_thread_safety` keeps a single
thread-safety finding under a relaxable gate and asserts its disposition is
`NEEDS_DEPLOYMENT_TESTING_DISPOSITION`, not `UNCONFIRMED_DISPOSITION` — this fixture is local to
the test, never a mutation of `_dual_run_fixture` (whose one thread-safety entry is gate-C, an
unconditional drop, so it never reaches this branch).
`test_apply_profile_assigns_unconfirmed_for_each_static_checkable_class` parametrizes the same
shape over `null-dereference`, `error-swallowing`, `resource-leak`, and `injection`, asserting
`UNCONFIRMED_DISPOSITION` for each. `test_apply_profile_never_assigns_a_confirmed_disposition` now
runs over `_dual_run_fixture` plus one added kept thread-safety finding, asserting every kept
disposition is one of the two allowed values rather than only `UNCONFIRMED_DISPOSITION` — the
committed-baseline comparison test is untouched, since the baseline never serialized a
`disposition` field.

Phase 6 plan 04 (Task 2, D-08/E-12) extends `test_review_profiles.py` with four probes closing the
E-12 defect: the security-kept ⊆ general-kept relation had only ever been exercised on an empty
comparison (`05-DEFECTS.md` row 5), so ∅ ⊆ ∅ passed vacuously and proved nothing.
`test_apply_profile_vacuous_subset_is_distinguishable_from_a_real_pass` asserts the subset
relation over two empty runs AND, as a separate assertion, that both sides were in fact empty —
a subset check alone cannot tell "held" from "had nothing to hold".
`test_apply_profile_subset_holds_at_a_single_kept_finding` exercises the same relation at size
one. `test_apply_profile_narrowest_margin_boundary_finding_is_kept_by_both` keeps a `gate=None`
finding whose `cls` is drawn from the real `GENERAL_DEFECT_CLASSES` table (`"injection"`, not
invented) — `gate is None` is the only route by which the security profile ever keeps a finding,
so this is the narrowest margin available, and it proves the subset holds even for a finding that
looks classification-eligible but never reaches `classify()` because the `or` short-circuits first.
`test_apply_profile_kept_set_is_stable_under_input_permutation` reruns `_dual_run_fixture()` and
its reverse through both profiles, comparing kept sets by `finding.id` rather than list position.
All four reuse `_dual_run_fixture()` (unmodified) or a slice/direct call of it — no second fixture
was added.

Phase 3 plan 07 (Task 3) adds `test_thread_safety_finding_ships_needs_deployment_testing_end_to_end`
to `test_review_live.py` — the composed proof that Task 1's ledger wiring and Task 2's disposition
ladder hold together through the real CLI path, not only at unit level. A single recorded
thread-safety finding runs through `run_review` under the `general` profile with no faked
`apply_verdict` (the real `reflection.apply_verdict` called with an empty verdict keeps
everything, so reflection's default behavior IS the "reflection keeps it" case); the ledger's one
surviving finding carries `"disposition": "needs-deployment-testing"` and
`"defect_class": "thread-safety"`.

Phase 4.1 plan 01 (DIFF-04) fixes `run_review` writing to the bare `--root` instead of the
per-repo sidecar `scan` and `audit` already use. `test_review_live.py`, `test_review_tracer.py`,
and `test_rule_glob.py` each gained (or reuse) a `_sidecar_ws(root)` helper that resolves
`RepoMemory.for_target(root, runner=...).workspace` with the same runner the test handed
`run_review` — `subprocess.run` read at call time for a `monkeypatch.setattr(subprocess, "run",
...)` fixture, or the test's own explicit `runner=` object for `test_rule_glob.py`'s
`_review_runner` fixture. Every assertion that used to join `tmp_path` directly against
`coverage_manifest.json`, `review_ledger.json`, `runs/review_plan.json`,
`runs/review_prompts/`, or `report.md` now reads through that sidecar workspace instead — a
passing test now proves the sidecar convention holds, not the bare-root bug. `test_diffscope.py`
needed no change: it never reads back a review artifact path.

Phase 4 plan 01 (Task 1, tracer) adds one test to `test_review_tracer.py`:
`test_review_one_finding_ships_diff_anchored_comment_and_sarif_fingerprint` injects a
`review_source` returning one real `Finding` into a direct `run_review()` call, asserts exit 0,
then asserts `artifacts/review_comments.json` holds exactly one comment with the five-key shape
(`path`/`line`/`side`/`existing_code`/`content`) mapped from that finding plus the embedded
`coverage_manifest`. It also calls `sarif.to_sarif([finding])` directly rather than reading
`report.sarif` — `report.py`'s `write_report` reads findings from `ws.findings_dir`, populated
only by `run_scan`, so `report.sarif` written by `run_review` always has empty `results`
regardless of this plan's changes — and asserts the result carries a 16-hex-char
`partialFingerprints` entry.

`test_bundle.py` (new, Phase 4 plan 01 Task 2, 14 tests) covers `group_bundles`'s totality
(every input path appears in exactly one returned unit), input-order preservation, deterministic
`unit_id` across repeat calls on the same member set, a different member set producing a
different `unit_id`, the empty-input and single-file cases, `ReviewUnit.__post_init__` rejecting
an empty `files` tuple, and the real pairing rules: Python/Go/TS impl-test pairs, locale siblings
and config-family siblings in the same directory (plus a locale-siblings-across-directories case
that must NOT pair), and unrelated files each landing in their own unit.

`test_review_agent.py` gained three tests (Phase 4 plan 01 Task 2) covering the widened
`bundle_paths` parameter: a `code_comment` naming any member of a supplied `bundle_paths` set is
kept and its `Finding.file` is that entry's own path (not the outer `path` argument); a comment
naming a path outside `bundle_paths` is discarded and counted, exactly like the single-file rule;
and `bundle_paths=None` reproduces the pre-widening single-path behavior unchanged.

Phase 4 plan 01 Task 3 found `sarif.py` and `review_comments.py` already correct — no
implementation gap — and closed the missing test coverage instead. `test_sarif.py` gained eight
tests locking the `partialFingerprints` contract (OUT-02): two findings differing only in
`message` share a fingerprint; findings differing in `file`, `cls`, or `evidence` each produce
different fingerprints; `to_sarif([])` yields `results == []` with no `partialFingerprints` key
anywhere in the serialized document; a single finding gets exactly one 16-character fingerprint;
whitespace-only evidence still gets a fingerprint; and a decomposed-vs-precomposed pair of the
same Unicode grapheme (`"café"` vs `"café"`) produces different fingerprints — recording
that the fingerprint is a byte-equality contract with no `unicodedata` normalization pass, on
purpose. `test_review_comments.py` (new, 5 tests) locks the OUT-01 contract:
`comment_from_finding`'s field mapping, an empty comment list still carrying the
`coverage_manifest`, the write path resolving to `ws.artifacts / COMMENTS_FILENAME`, and a
comment payload having exactly the 5 documented keys and no more.

`test_cli.py` gained a new section (Phase 4 plan 02 Task 1, SCALE-02) covering the bounded
`--concurrency`/`--timeout`/`--max-git-procs` flags: each flag is accepted at 1 and at its own
ceiling; each is rejected at 0, -1, and one past its ceiling with a non-zero exit and a stderr
message naming the flag and its `1 and <ceiling>` range; a non-integer value raises `SystemExit`
via argparse before `run_review` ever runs; and the three defaults (8, 600, 16) are asserted by
spying on `run_review`'s kwargs when no flag is passed.

`test_cli.py` gained four more tests (Phase 4 plan 02 Task 2, SCALE-02) for the bounded
`ThreadPoolExecutor` git-fetch loops: a wall-clock test asserting `N` files' fetch elapses in
roughly one sleep interval, not `N` sleep intervals, when `--max-git-procs` fits every file;
a manifest-order test with an uneven per-file delay asserting `coverage_manifest.json`'s file
order stays input order regardless of which file's fetch finishes first; a monkeypatch on
`cli.ThreadPoolExecutor` asserting zero reviewable files never constructs a pool.

`test_review_coverage.py` gained ten tests (Phase 4 plan 03 Task 2, SCALE-03) covering a
resume-identity gate: `MANIFEST_VERSION` is 2; `to_dict`/`load` round-trip
`model`/`profile`, including a `None` case and a version-1 manifest with neither key; a
`ResumeIdentityError` extends `RuntimeError`; `check_resume_identity` passes on a match, permits
any value when the prior manifest recorded neither field, and raises naming both values on a
model or profile mismatch; and `cli.run_review` run twice with different `model` values against
the same target returns 2 on the second call, leaving the manifest byte-identical with no new
artifact file written.

`test_cli.py` gained two more tests (Phase 4 plan 02 Task 3, SCALE-02) for the per-`ReviewUnit`
`--timeout`: a fake runner sleeps past `timeout=1` on a three-file locale-sibling group
(`en.json`/`fr.json`/`de.json`, grouped into one unit by `bundle.py`'s same-directory locale
rule) and asserts `run_review` returns `3`, that `coverage_manifest.json` marks **all three**
member paths `failed` with the exact note `cli.TIMEOUT_NOTE`, and that its `seal` is `"partial"`
— three, not two, so a fix that only fails the first member (or the unit as a whole) and leaves
the rest unfinished cannot pass; a second test asserts a unit that finishes inside `timeout=5`
still seals `"complete"` (rc 0), so the new dispatch path is a no-op when nothing is slow.

`test_cli.py` gained two more tests (Phase 4 plan 03 Task 3, SCALE-03) for SHA-pinning on
resume: a fake runner whose `rev-parse` for `develop` returns a different SHA than the prior
run sealed asserts the resumed `git diff --name-status` call still uses the persisted head
SHA; a second fake runner makes the persisted head SHA itself unresolvable (`rev-parse
--verify` exits 128, simulating a rewritten/collected SHA) and asserts the resumed run exits 2
naming that SHA rather than reading an empty diff (T-04-12). `test_review_live.py`'s
profile-split test (security excludes a null-dereference finding, general includes it) was
split to run against two independent target directories instead of resuming one target with a
second `profile` — the new resume-identity gate (Task 2) now rejects that second call.

`test_cli.py` gained two more tests (Phase 4 plan 04 Task 1, OUT-01 gap closure) asserting
`review_comments.json`'s embedded `coverage_manifest` matches the on-disk
`coverage_manifest.json` byte-for-byte on its `seal` field: a complete single-file run expects
`"complete"` on both, and a partial run (one of two files fails `parse_hunks`) expects
`"partial"` on both. Both fail against the pre-fix ordering — `write_review_comments` ran before
`manifest.seal()`, so the embedded seal always read `null` regardless of the on-disk value.

`test_cli.py` gained two more tests (Phase 4 plan 04 Task 2, SCALE-03 gap closure) for the
`review` subcommand's `--model` argparse surface: a spy on `run_review` asserts `cli.main([...,
"--model", "opus"])` forwards `model="opus"`; a resume test drives two `cli.main` calls against
the same target with different `--model` values and asserts the second exits 2 with both model
names named in stderr. Both fail against the pre-fix parser — `--model` was unrecognized, so
`main()` never called `run_review` with a `model` value, leaving the already-wired
`check_resume_identity` gate dead code in production.

`test_cli.py` gained three more tests (Phase 4 plan 04 Task 3, SCALE-02 gap closure) bounding a
hung unit fetch's wall-clock time: `test_review_returns_before_hung_unit_fetch_completes` reuses
the three-locale-sibling unit and 1.2s-sleeping runner from the 4.20s reproduction
(`test_review_unit_timeout_fails_every_member_with_timeout_note`) and asserts elapsed time under
2s instead of the full ~3.6s sequential fetch — the pre-fix `with ThreadPoolExecutor(...) as ex:`
blocks on exit until the abandoned worker finishes, even after `future.result(timeout=...)`
already raised.  `test_review_abandoned_unit_fetch_stops_at_the_unit_deadline` counts a
0.6s-sleeping runner's invocations and asserts the count stays below the unit's full member
count — the abandoned worker must stop fetching once its own deadline passes rather than working
through every remaining member.  `test_review_production_git_calls_carry_subprocess_timeout`
monkeypatches the real `subprocess.run` with a fake accepting `**kwargs` and asserts every call
the review path makes (with no injected `runner`) carries `timeout` equal to the declared
`--timeout`, so a hung git child is killed instead of orphaned. Fixing this shifted the shared
fake-runner convention: **every fake handed to `monkeypatch.setattr(subprocess, "run", ...)` (or
injected as `runner=`) must accept a `timeout` keyword it can ignore**, because the production
default is now `partial(subprocess.run, timeout=timeout)` — `_make_review_runner` (`test_cli.py`),
`_fake_run_for`/`failing_diff` (`test_review_live.py`), and `_fake_run`/`_make_fake_run`
(`test_review_tracer.py`) all gained `**kwargs` for this reason; none of their return values
changed.

Fixing SCALE-02 also surfaced a latent regression from the SCALE-03 `--model` wiring (Phase 4 plan
04 Task 2, commit `7b72c75`): `test_rule_glob.py`'s `fake_run_review` spy had no `model` parameter,
so the full suite raised `TypeError: fake_run_review() got an unexpected keyword argument 'model'`
once Task 3's fix forced a full-suite run. Added `model=None` to the spy's signature to match
`run_review`'s real keyword-only parameters.

`test_review_live.py` gained `test_run_review_scopes_git_calls_to_root_not_process_cwd` (Phase 5
plan 01, D-05-01-01), the suite's first `run_review` test with no injected `runner` at all: it
builds a real temporary git repo (real `subprocess.run`, `git init`/`commit`) deliberately
separate from pytest's own cwd, calls `run_review(base_sha, head_sha, str(repo), prepare=True)`,
and asserts `review_plan.json` lists the repo's real changed file. Pre-fix, the production
runner's git calls ran unscoped against pytest's cwd (this plugin's `helpers/` checkout) instead
of the temp repo, so the plan came back empty — every other `run_review` test in this file
instead monkeypatches the stdlib `subprocess.run` with a fake that reads only `cmd` and ignores
every keyword argument (including `cwd`), so a wrong `cwd` binding would not have made any of
them fail either before or after this fix.

`test_review_live.py` gained three tests pinning WR-01 (Phase 6 plan 01):
`test_run_review_rejects_a_nonexistent_root_with_exit_2`,
`test_run_review_rejects_an_empty_root_with_exit_2`, and
`test_run_review_rejects_a_file_as_root_with_exit_2`. Each asserts `run_review` returns 2 with a
single `error: --root ...` line on stderr (`capsys`) instead of raising. Pre-fix, the three cases
failed three different ways depending on where `Workspace.ensure()`'s `mkdir(parents=True)`
happened to land: a missing root was silently auto-vivified by the mkdir side effect (no crash,
but the run proceeded against a non-git directory and failed later with an unrelated "unresolvable
ref" message); an empty-string root reached a real `subprocess.run(cwd="")` and raised
`FileNotFoundError`; and a file-as-root raised `NotADirectoryError` from `Workspace.ensure()`'s own
`mkdir` before any git call. The guard normalizes all three to the same exit-2 message before any
workspace or subprocess work starts. Adding the guard also meant
`test_exit_codes_unchanged_invalid_ref_partial_seal_complete`'s `partial`/`complete` roots — which
previously relied on that same auto-vivification to spring into existence — now `mkdir()` those
directories explicitly before calling `run_review`.

`test_review_live.py` gained three tests covering `run_review`'s new `workspace=` override
(D-03, Phase 6 plan 01): `test_run_review_uses_the_workspace_override_when_supplied` asserts an
explicit `workspace=` writes `artifacts/coverage_manifest.json` under that path and leaves the
`--root` sidecar untouched; `test_run_review_falls_back_to_the_repo_sidecar_when_workspace_is_absent`
pins the pre-existing no-override behavior as a regression guard (it already passed before the
`workspace` parameter existed — TypeError only fires when the kwarg is actually passed); and
`test_review_workspace_override_permits_a_second_profile_without_weakening_the_resume_guard` runs
`run_review` twice against the same `workspace=` override with two different `model` values and
asserts the second call still exits 2 — the SCALE-03 resume-identity check reads the resolved
workspace's manifest, so it applies the same whether that workspace came from `load_paths` or the
`RepoMemory` sidecar. `test_rule_glob.py`'s `fake_run_review` spy also gained `workspace=None`
(same class of gap `model=None` closed there previously) once the new keyword-only parameter made
the full suite raise `TypeError: fake_run_review() got an unexpected keyword argument 'workspace'`.
The spy fix lands in the same commit as the implementation (1.69.0), not the RED commit above,
since the `TypeError` only fires once `main()`'s `review` dispatch starts passing
`workspace=args.workspace`.

`test_report.py` gained five tests pinning the deps Fix-line package-name bug (Phase 6 plan 03,
D-04): `test_fix_line_names_scoped_package_with_version`,
`test_fix_line_names_unscoped_package_with_version`,
`test_fix_line_falls_back_to_full_identifier_when_versionless_scoped`,
`test_fix_line_uses_placeholder_when_identifier_absent`, and
`test_fix_line_resolves_at_rightmost_separator_for_multi_at_identifier`, each also asserting the
rendered Fix line never contains a hollow backtick pair (`` `` ``). Pre-fix, `render_finding`'s
deps branch split the evidence string on the first `@`
(`pkg.split('@')[0]`) to isolate the package name from its `@version` suffix — but a scoped
npm-style identifier (`@scope/name@version`, produced by `sca.parse_osv_json` straight from
osv-scanner's `package.name` field) begins with that same `@` character, so the first split
lands on the scope delimiter and returns an empty string. The two unscoped-identifier tests
already passed before the fix (no leading `@` to mis-split on); only the three scoped-identifier
tests captured RED.

`test_docs_invariants.py` gained
`test_redteam_agent_describes_the_real_two_way_wants_runtime_predicate` (Phase 6 plan 03, D-02),
a code-derived doc guard pinning `agents/redteam.md`'s Discriminate section against
`redteam.py`'s `wants_runtime()`. It reads both trigger values from real code with no hardcoded
copy — `"needs-runtime"` via set difference against the already-imported `RUNTIME_DISPOSITIONS`,
and `FindingStatus.NEEDS_DEPLOYMENT_TESTING.value` from `sec_overlay.models` — and asserts the
prompt no longer claims a third "neither static-settled nor a live-exploit test" disposition
that opts a finding out of the runtime plan. `wants_runtime()` is a plain two-trigger OR: either
condition alone forces inclusion; `open_questions` plays no role in that predicate at all — it
is an independent mechanism `redteam.md` uses to flag human-answerable unknowns, never a bucket
a finding can be routed into or out of.

`test_docs_invariants.py` also gained `test_claude_md_phase_order_tracks_phase_table`
(Phase 6 security audit, T-06-02-06): it walks the live `PHASE_TABLE` and asserts every phase
the skill `CLAUDE.md` "Phase order" block names appears in the same relative order, using a
name-to-doc-label map. The block is a condensed operator view, so table rows it deliberately
omits (`factcheck`, `demote-noise`, `selfscore`) are exempt from presence but a reorder of any
named row fails the suite. This replaces the one-time manual side-by-side read Plan 06-02
recorded as its doc-drift check with a standing regression guard.

`test_frozen_contract.py` (new, Phase 6 plan 04, D-15/REL-03) is the frozen-contract
tripwire suite. Two sha256 byte-identity guards pin `models.py`/`evidence.py` against
their committed digests — either file is a byte-identical mirror of a separate Go
port, and a mismatch fails with an actionable message naming the required sign-off
and Go-port update. Three `fingerprint()` golden-value tests reach the same pinned
12-hex value from a fully-populated `Finding`, a minimally-populated one (every
optional field at its dataclass default), and one built with the same required
fields passed in reverse keyword order — proving the digest depends only on
`rule_id`/`cls`/`anchor` and is inert to every other field and to construction
order, independent of the byte-identity guards above. `test_helpers_declare_zero_runtime_dependencies`
reads the real `pyproject.toml` via stdlib `tomllib` and asserts `[project]
dependencies == []` (REL-03), closing the requirement with a running check instead
of a one-time manual read.
