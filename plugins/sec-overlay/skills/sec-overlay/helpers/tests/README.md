# `tests/` — the deterministic test suite

142 pytest files, 1830 tests. Run from `helpers/`: `uv run pytest -q`. Two failures on a clean
checkout are environmental (gitignored bench corpus, excluded vendored semgrep clone) — see the
skill [`CLAUDE.md`](../../CLAUDE.md) §1.

New `test_phase_docs.py` pins REQ-61: every document that states the pipeline's phase order must
carry a `<!-- BEGIN GENERATED: phase-table -->` block rendered from `PHASE_TABLE`, not a
hand-maintained list that can drift from the code. `test_every_document_carries_a_generated_block`
and `test_every_generated_block_is_current` check the four generated documents (`SKILL.md`, the
skill root `README.md`, `agents/README.md`, `helpers/README.md`) against `phase_docs.regenerate`.
`test_the_table_states_every_phase_in_order` and `test_a_kind_filter_keeps_the_full_table_index`
pin `render_phase_table`'s column and kind-filter contract directly against `PHASE_TABLE`.
`test_renaming_a_phase_makes_a_block_stale` proves the staleness check actually detects a rename,
not just an absent block. `test_claude_md_carries_no_generated_block` and
`test_note_documents_is_skill_md_only` pin that the skill `CLAUDE.md` points at `SKILL.md` for the
phase table and its operator notes instead of duplicating them.
`test_every_table_phase_has_a_note_in_skill_md` is gone: ruling P5-10 removed it because it and
`test_contract_lint.py`'s `test_operator_notes_name_every_phase_and_nothing_else` stated two
contradictory contracts for the same `<!-- BEGIN PHASE NOTES -->` region. The contract-lint test is
the surviving one. `test_claude_md_is_in_documents_but_not_note_documents` pins that `CLAUDE.md` is a `DOCUMENTS`
member (so Task 5's contract lint, which iterates `DOCUMENTS`, covers it) while staying out of
`NOTE_DOCUMENTS` — a fix-round finding: `CLAUDE.md` had been left out of `DOCUMENTS` entirely.

`test_contract_lint.py` gains three more REQ-61 tests.
`test_operator_notes_name_every_phase_and_nothing_else` asserts exact set equality: the note keys in
`SKILL.md` and the `PHASE_TABLE` phase names are one set, and the failure message names both the
missing and the extra keys. There is no `NON_TABLE_STEPS` exception — ruling P5-10 deleted that
constant. `test_operator_notes_follow_the_table_order` checks the notes appear in the same order
as `PHASE_TABLE`. `test_pipeline_documents_name_only_substitutable_tokens` checks every `{{TOKEN}}`
in a `DOCUMENTS`/`NOTE_DOCUMENTS` file is in `driver.DISPATCH_TOKENS` or
`phase_docs.ORCHESTRATOR_TOKENS` — the operator notes live in `SKILL.md`, not `CLAUDE.md`. Only the
token test failed on the first run: `agents/README.md` named a literal `{{PLACEHOLDER}}` token that
no producer substitutes; the sentence now shows real tokens (`{{TARGET}}`/`{{WORKSPACE}}`) instead
of an invented one. A `PhaseSpec` rename in `phases.py` now fails this file's
`test_operator_notes_name_every_phase_and_nothing_else` alongside `test_phase_docs.py`'s
`test_every_generated_block_is_current` (plus two more phase_docs tests the rename also breaks), so
a rename can no longer pass the suite with a stale document.

Two more `test_phase_docs.py` tests pin `regenerate`'s failure modes, both on synthetic text so no
real document carries a broken marker.
`test_a_nested_begin_marker_raises_instead_of_deleting_the_text` builds a document whose second
`BEGIN` opens before the first block's `END` and asserts the `ValueError` names line 4; before the
guard, the outer rewrite swallowed the inner marker and every line between the two. `test_a_crlf_document_regenerates` joins the same document with `\r\n` and
asserts the block is rewritten; before the `\r?$` anchor, the marker never matched and `--check`
reported a stale document as current.

`phase_docs.py` ships. `regenerate` rewrote the four generated documents from `PHASE_TABLE`, and
`SKILL.md`'s old hand-numbered walkthrough became a five-item preface list (the steps
`PHASE_TABLE` does not own) plus the generated table and a 28-entry Phase Notes region, one bullet
per `PHASE_TABLE` name, in order. `test_docs_invariants.py`'s old
`test_claude_md_phase_order_tracks_phase_table` guarded a hand-maintained phase-order block in the
skill `CLAUDE.md` that no longer exists — that file now points at `SKILL.md` instead of duplicating
`PHASE_TABLE` (REQ-61), so the test is replaced with
`test_claude_md_points_at_skill_md_for_the_phase_order`, which checks the pointer instead of a
label list. `test_no_dead_helpers.py`'s `DEAD_ALLOWLIST` gains `phase_docs.py:note_keys`
(test-only importer, no production caller).

New `test_redteam.py::test_directive_falls_back_to_the_finding_preconditions` pins REQ-55: a
finding with no `runtime_test` still shows its own `preconditions` in the directive body, in the
same "Code-settled" block the heading already names.

New `test_selfscore.py` tests pin REQ-54: `test_self_score_buckets_partition_the_finding_population`
checks every finding on disk lands in exactly one `by_status` bucket and that `duplicate` matches
the bucket count, and `test_self_score_reports_collapsed_counts` checks `reported_collapsed` counts
one representative per cluster, the same way the report collapses clusters. New
`test_artifact_consistency.py` tests pin the same requirement:
`test_gate_flags_a_self_score_that_loses_findings` checks clause (h) rejects a score whose
`by_status` buckets sum to less than `total`, and
`test_gate_flags_any_self_score_mismatch_against_the_report` replaces the old bounded-tolerance
test — clause (d) now flags a mismatch in either direction, since both the report and the score
collapse clusters under REQ-54.

`test_self_score_counts_by_status_and_persists` now asserts the five new REQ-54 keys alongside
the original ten: `total`, `duplicate`, `by_status`, `reported_collapsed`, and
`needs_runtime_collapsed`, computed from the same fixture findings the original ten keys use.

New `test_constraint_enforcer.py` tests pin REQ-51: `evidence._MECHANICAL` must equal
`TIER1_RECEIPTS | TIER2_RECEIPTS` (the derivation, not an independent literal), and a new
`evidence.unknown_receipts` must report a source whose prefix names neither tier and is not
`llm`-namespaced, pass a declared prefix, pass an `llm-claimed:`/`llm-corroborated` source, and
pass the `prove` lane's `reproduction` receipt (a real receipt outside both tiers). A gate test
confirms `validate_findings` reports the offending source with a "closed set" message instead of
silently ignoring it; a second gate test confirms a finding confirmed solely by `reproduction`
still passes. `test_findings_gate.py::test_confirmed_requires_tool_receipt`'s fixture drops
`read:sanity` (an undeclared prefix under REQ-51) for `llm-claimed:read-sanity` — same intent, no
mechanical receipt, now legal under the closed set. `test_frozen_contract.py`'s pinned
`_EVIDENCE_SHA256` (D-15) is updated to match `evidence.py`'s new bytes — `unknown_receipts` and
the `_MECHANICAL` derivation moved `REPRODUCTION_RECEIPT`/`is_reproduction_receipt` into that file.

New `test_constraint_enforcer.py` tests pin REQ-52: `reachability.BLOCKERS` must admit
`external-boundary`, and `blocker_of` must report it verbatim instead of coercing it to `"other"`.
A prompt test asserts `agents/trace.md`'s reachability-decision bullet names `external-boundary` in
the closed taxonomy list, not only in the paragraph below it. Three `findings_gate` tests cover the
new clause: an `external-boundary` finding with no `open_questions` entry is rejected, one whose
entry is missing `who_to_ask_or_check` is rejected the same way, and one with all three
`OPEN_QUESTION_KEYS` populated passes. Three further tests pin the shape `agents/trace.md`
documents: an `external-boundary` verdict with no `reachable` key passes both
`validate_reachability` and `stage_validate.validate_stage("reachability", ...)`, the same verdict
with a non-bool `reachable` still errors, and a non-`external-boundary` verdict with `reachable`
absent still errors.

`test_contract_lint.py::test_every_closed_vocabulary_matches_its_schema_enum` (REQ-50) now also
derives `completeness_tier`, `judge_verdict`, `receipt_tier`, and `reachability.blocker` from
`fix_disposition.TIERS`, `calibrate.JUDGE_VERDICTS`, the literal `{1, 2}`, and
`reachability.BLOCKERS`. A new `test_nested_item_schemas_declare_their_published_keys` pins the
`open_questions`, `affected_sites`, and `history` item schemas against
`models.OPEN_QUESTION_KEYS`, `models.AFFECTED_SITE_KEYS`, and the `history` event key.

New `test_no_dead_helpers.py` (REQ-48) is the standing guard against the class of dead lever
`test_dead_lever.py` pins one instance at a time: an AST scan walks every public function in
`sec_overlay/` and requires each one to carry a reference from a non-test Python file, a
`DEAD_ALLOWLIST` entry with a one-line reason, or a `PROMPT_ONLY` entry naming the agent prompt or
`SKILL.md` that runs it by name (never a Python import). The scan proves a reference, not a call:
an unused import still counts, so the guard is a floor against new dead code, not a reachability
proof. A second test fails the moment a listed entry gains a reference,
and a third fails the moment a listed entry names a function deleted from the tree, so a new dead
helper fails the suite instead of joining the pile silently. Reconciling the two lists against the
current tree dropped `scoring.py:score_fix` from `PROMPT_ONLY` (`verify.py` now imports and calls
it directly) and added `reflection.py:validate_verdict` (named only by `agents/README.md`).
`report.py`'s `to_markdown` carried an unreached `token_spend`/"Token spend by phase" branch behind
`economics`; REQ-46 deleted the token measurements, so this task deleted the parameter and the
branch with it.

`test_no_dead_helpers.py` gains two tests. The first requires `context.py:load` and
`fix_disposition.py:validate` to carry a list entry. Both are dead, and the flat name scan hides
them behind an unrelated identifier of the same name. The second requires `_public_functions` to
report an `async def` helper. Both tests fail against the flat name scan.

The scan now resolves a reference to the module that defines the function, so a bare name in an
unrelated module no longer counts as a caller. A key is `<module>.py:<function>`. It counts as
referenced when a non-test file imports the function by name from that module, imports the module
and reads the attribute, or uses the bare name inside the defining module itself.
`_public_functions` also matches `ast.AsyncFunctionDef`. `helpers/tests/` stays outside the scan,
so a test-only importer never makes a helper live: `fix_disposition.py:validate` is imported by
`test_fix_and_gates.py` and still belongs in `DEAD_ALLOWLIST`. Module keys are file basenames, so
`cli.py` and `workspace.py`, which each exist twice in this tree, share one key per name.

`test_no_dead_helpers.py` gains three more tests pinning fix round 1, finding I2. The prompt corpus
must hold `commands/audit.md`. The four helpers that the slash command runs must cite that file.
Every `PROMPT_ONLY` entry must invoke its helper inside a code span of the cited file. All three
fail: the corpus stops at `agents/` and `SKILL.md`, and a bare name in prose satisfies the current
citation check.

A `PROMPT_ONLY` citation now must prove an invocation. The guard keeps only the code of the cited
file: fenced blocks, indented blocks, and inline backtick spans. Inside that code the helper must
appear as a call, `name(`, or as `module.name`. The corpus adds `plugins/sec-overlay/commands/`,
which is where the slash command runs `drive`, `advance`, `infer_role`, and `synthesize_manifest`.
Re-citing every entry moved `run.py:infer_role` and `run.py:synthesize_manifest` out of
`DEAD_ALLOWLIST` into `PROMPT_ONLY` at `commands/audit.md`, moved `campaign.py:pass_report` and
`detection_coverage.py:generate` the other way, and re-pointed `context.py:leads`,
`githist.py:security_fix_commits`, `run.py:advance`, and `run.py:drive` at the file that runs them.

`test_diffscope.py` gains `test_changed_files_raises_when_git_diff_fails`, which pins fix round 1,
finding I4. A non-zero `git diff --name-only` exit must raise, and the message must name the
operation and both revisions. It fails today: `changed_files` discards the return code, so a
failed diff reads as an empty change set and `postflight` keeps every stale prior conclusion.

`test_dead_lever.py`'s three REQ-47 tests now pass: `sec_overlay.scope` and `test_scope.py` are
deleted (the module had no caller), `scanscope.py`'s `rel_to_root` is deleted along with its test
in `test_scanscope.py` (also no caller), and `SKILL.md`'s scope-token paragraph now points at
`run.env` instead of restating the old `kb/scan-scope.json` sentence.

`test_dead_lever.py` gains three tests pinning REQ-46: `sec_overlay.cost` must expose only
`record_timing` and `aggregate_timings_by_phase`, a bare workspace's rendered report must hold no
"Tokens by" or "Estimated cost" line, and `SKILL.md` must never name `record_agent(`. `cost.py`
now holds only the two timing helpers. `test_cost.py` drops its four token/USD tests, keeping
only `test_record_and_aggregate_timings`. `test_report.py` drops
`test_write_report_renders_run_economics` and
`test_run_economics_section_renders_phase_model_and_usd_estimate` — both asserted a token or USD
total that no longer exists. `test_bench.py` drops `test_scorecard_cost_none_per_tp_when_no_tp`
and trims the token/USD assertions out of `test_scorecard_carries_cost_columns` and
`test_scorecard_markdown_renders_cost_and_per_class_fp`, keeping their wall-clock assertions.

New `test_findings_overflow.py` (REQ-27, 5 tests) covers the load-and-save round trip through
`read_findings`/`write_findings`: an unknown finding key survives the round trip, known fields
stay unchanged, two insertion orders of the same unknown keys produce byte-identical output, a
finding with no unknown key is unchanged, and `read_findings` warns on stderr naming each
preserved key.

New `test_patch_status_real_git.py` (REQ-01) drives real `git apply --check` against a repo
fixture, locking both outcomes: an additive patch whose added line is absent is `NOT_APPLIED`,
and the same patch is `APPLIED` once the added line is present. `test_patch_status.py`'s two
order-pinning tests were rewritten to pin the new forward-then-reverse call order.

`test_calibrate_evidence.py` pins REQ-20: receipt tier, verification strength, and assessed
reachability each move `calibrate_score` upward, and an unassessed finding scores unchanged.

New `test_trace_prompt.py` (REQ-06, REQ-19) pins that `trace.md` covers `needs-deployment-testing`
findings and names the in-band channel first.

New `test_prefilter_receipt.py` (REQ-16) pins that `run_prefilter` writes its receipt to disk
before recording the `prefilter` stage, so a fence abort never leaves a done stage with no receipt.

New `test_prefilter_paths.py` (REQ-15) covers the path-relativization boundary in `run_prefilter`:
an absolute backend path under `target` becomes repo-root-relative, an already-relative path is
left alone, and a path outside `target` stays verbatim rather than being rewritten into something
that does not resolve.

New `test_receipt_counts.py` (REQ-13, folds in REQ-23) covers `workspace.finding_counts`: it
partitions a workspace's findings into `findings_in` (every finding file) and `findings_out`
(the `evidence.SHIPPING_STATUSES` subset), with `findings` kept equal to `findings_in` for the
pre-REQ-13 consumer. `run.advance`'s receipt now carries these three counts instead of a
`F-*.json` glob that matched no real finding id. `driver._write_gate` gains the same two keys,
so a gate receipt (e.g. `findings-gate.json`) records finding counts, not only `passed`.

New `test_contract_lint.py` (REQ-32, Task 1) checks that `finding.schema.json`'s `verification`
and `runtime_disposition` enums equal `sec_overlay.evidence`'s `VERIFICATION_VALUES` and
`RUNTIME_DISPOSITIONS`, plus `None`. `test_models.py` gained four tests for the same closed
enums: `Finding.from_dict` rejects a prose `verification` value and an unknown
`runtime_disposition`, and accepts a documented value or `null` for either field.

`test_contract_lint.py` (REQ-18, Task 2 RED) adds two failing tests: the `FINDING_SHAPES` block
in `prompt-constants.md` must name every key in `models.RUNTIME_TEST_KEYS`,
`OPEN_QUESTION_KEYS`, and `AFFECTED_SITE_KEYS`, and `agents/investigate.md` must reference
`FINDING_SHAPES`. Both fail to import until the three key tuples exist on `models.py`.

`test_contract_lint.py` (REQ-18, Task 2 GREEN) passes once `models.py` exports the three key
tuples and `prompt-constants.md`/`investigate.md` publish and import the `FINDING_SHAPES` block.
`test_frozen_contract.py`'s `_MODELS_SHA256` moved to the new digest in the same commit, since
`models.py` gained the three constants.

`test_detection_coverage.py` guards the coverage document: `generate()`'s output must name the
dependency-internal sink limit and cite `dependency-sinks.json`, so the doc cannot silently
drop the routing-versus-proof distinction. A second test asserts `generate()`'s output equals
the tracked `references/DETECTION_COVERAGE.md`, byte for byte. This closes the drift the first
test cannot see: an edit to `detection_coverage.py` with no matching regeneration of the file.

The fake-response `R` classes in `test_review_tracer.py` and `test_diffscope.py` declare
`stdout = ""` as a class attribute so `ty check` resolves the attribute; behavior is unchanged.

`test_rules_check.py` covers the `rules check` CLI and `resolve_with_layer`: the project layer
resolves to the mapped rule doc, an unmapped path falls through to the built-in doc, and a
misspelled top-level subcommand names the nearest valid one via `difflib` (REQ-S4).

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

`test_review_result.py` (5 tests, REQ-P7) locks the consolidated `review_result.json`
contract: `write_review_result` lands the file in `ws.artifacts` with the full documented
`RESULT_KEYS` set on both a zero-finding run and a populated run, each finding record carries
the seven documented fields, and dataclass declines/skips serialize to plain dicts.

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
writes a second `*reflection*.json` artifact file. Four more tests (Task 9, REQ-P6) pin the
recorded-verdict source that drives production reflection: `recorded_verdict_source(ws, *, base,
head)` returns the recorded `{id: analysis}` mapping for a path, and raises `ValueError` when no
return is recorded, the return is not JSON, or the envelope's `base`/`head` is stale — mirroring
`review_agent.recorded_return_source`. The envelope is written under `reflection_label(path)` via
`record_agent_return`.

`test_review_live.py` (Task 9, REQ-P6) adds four end-to-end tests through `run_review` with no
`apply_verdict` monkeypatch: a recorded verdict retracts a non-protected finding
(`RETRACTED_REASON`), a verdict naming a protected-class finding is refused and the finding stays
kept (`REFUSED_REASON`), a reviewable file with findings but no recorded verdict fails open (finding
survives AND a `reflection_skipped` entry is ledgered — never a silent keep-all), and
`--prepare-reflection` renders one review-filter prompt per file with post-profile kept findings
into `runs/reflection_prompts/`. `test_reflection_failure_for_one_file_leaves_other_files_unaffected`
records an unreadable verdict for one file (skip) and a valid empty verdict for another (kept),
proving a per-file verdict failure is isolated — it too drives the real `recorded_verdict_source`
rather than monkeypatching `apply_verdict`.

`test_review_budget.py` (new, REQ-P4, Task 12) covers the hard token budget: the OCR-shaped
cost constants (`PLAN_PROMPT`, `PLAN_OUT`, `ROUNDS`, `ROUND_OUT`, `FILE_BUDGET_FRACTION`),
`estimate_tokens` staying the raw `len//4` primitive, `estimate_review_cost` following OCR's
plan-loop formula (empty diff == 21300, scaling with diff length), and `BudgetGate` admitting
until a projected breach then latching closed (budget 0 unlimited; an estimate hitting the
budget exactly still admits). `test_review_live.py` gains four end-to-end `run_review` tests
(tiny budget seals `partial`, notes `skipped(budget)`, exits 0; zero budget reviews every file;
`--prepare` records a per-file `token_estimate`; a file over the 0.8 cap is excluded before
review). `test_docs_invariants.py` gains `test_review_budget_constants_match_ocr_shape`, pinning
the constant tuple against `(2000, 400, 7, 700)` and `0.8`.

`test_diffscope.py` (REQ-P5, Task 13) gains
`test_dirty_file_records_lists_staged_unstaged_untracked`, a real-repo check that
`dirty_file_records` returns one record per working-tree change git reports (a staged
modification, an unstaged modification, an untracked file). `test_review_live.py` gains three
CLI tests: `--commit <sha>` scoping the review to `sha^..sha` (the plan entry pins the parent
and commit SHAs), `--commit` with `--base` exiting 2 (mutual exclusion), and
`--workspace-dirty` listing staged, unstaged, and untracked changes.
`test_validate_ref_accepts_allowlisted_refs` gains a `HEAD^` case, pinning the GREEN allowlist
change that lets `--commit`'s `sha^` parent ref validate.

`test_review_agent.py` and `test_review_live.py` (REQ-P3, Task 14) cover the per-file plan phase.
The agent-seam tests check `render_review_prompt` injecting a `{{PLAN_GUIDANCE}}` body (empty by
default), `render_plan_prompt` substituting the plan template's tokens, and
`plan_guidance_from_return` ordering issues by severity and raising on invalid JSON, an unknown
severity, a missing `issues` key, or an issue without guidance. The CLI tests check `--prepare
--plan` writing a plan prompt only for a unit at or over `PLAN_LINE_THRESHOLD`, a recorded plan
return injecting its guidance into the review prompt, and an invalid plan return failing open —
the review prompt renders without guidance and a `plan_skips.json` entry records the skip.

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

`test_citations.py`, `test_baseline_envelope.py`, and `test_report.py`'s `Finding`
test-builders (`_f`/`_tf`/`_full`) now build a base `Finding(...)` call and layer per-test
overrides with `dataclasses.replace(base, **kw)`, instead of a `dict()` + `.update(kw)` +
`Finding(**d)` construction — `**d`'s inferred concrete dict type tripped `ty`'s
per-field argument checking that `replace`'s `**changes: Any` typing bypasses. Clears the bulk
of the VAL-02 ty ledger (`invalid-argument-type` diagnostics across all three files); no
behavior change — `Finding` is not frozen, so post-construction mutation still works.

`test_calibrate_evidence.py`'s `_f` builder took the same `dataclasses.replace` fix (REQ-20
fix round 1), clearing the one ruff `C408` finding and 34 `ty` `invalid-argument-type`
diagnostics its prior `dict()`-splat construction carried; all six REQ-20 assertions are
unchanged.

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

`test_contracts.py` also gained two guards for the catalog and absence receipts.
`test_ssrf_proof_tuple_admits_the_dependency_internal_sink` slices `ssrf.md` down to its
"## Proof tuple" section. It checks that `dependency-catalog` and `sec-overlay.absence` both
appear inside that slice, not just somewhere in the file.
`test_investigate_tool_grounding_names_the_two_new_receipts` checks `investigate.md` names
`dependency-catalog` and states it never confirms a gate alone.

`test_contract_lint.py` (REQ-07) gains two tests checking `agents/validate.md` matches the
`findings_gate.py` confirmation rule. `test_validate_prompt_states_the_tier1_confirmation_rule`
checks the prompt names every `evidence.TIER1_RECEIPTS` value, the word `Tier-1`, and
`needs-deployment-testing`. `test_validate_prompt_does_not_imply_tier2_confirms` checks the
`**Confirmed**` verdict section names `Tier-1`, so a Tier-2-only receipt never reads as
sufficient for `confirmed`.

`test_contract_lint.py` (REQ-10) gains `test_threat_model_prompt_imports_qualifier_proof` and
its `_imports_line` helper. The test checks `agents/threat-model.md`'s `## Imports` section
names `QUALIFIER_PROOF`, since the prompt grades severity and needs the blanket-qualifier rule.

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
after investigate, dedupe/demote-noise before report, trace present) and the pure sequencer helpers (`missing_inputs`,
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
`agents_to_spawn`, not one token (ISSUE-050).
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
| `test_contracts.py` | Prompt↔schema drift: a `Finding` JSON example in an agent prompt must parse against the real `models.py`. Two guards pin the always-run absence pack: `recon.md` must mention `rules/absence` right after the word "always", and `golden_scan_profile.json` must carry `rules/absence` in `sast_plan.semgrep.rulesets`. |
| `test_finding_schema.py` | The `Finding` record stays consistent with `references/finding.schema.json`. |
| `test_contract_lint.py` | REQ-32: a closed vocabulary's code constant matches its schema `enum`, verbatim. |
| `test_wiring.py` | Silent-backend / clsmap / dead-link regressions and attack-class routing. |
| `test_docs_invariants.py` | Documentation contracts: prompt-constants block presence, `finding-template.md` sections, agent-prompt rules, the `EVIDENCE_VOCABULARY` block listing every `sec_overlay.evidence` tier/status/disposition value verbatim, the `CLAUDE.md` phase-order section pointing at `SKILL.md` instead of duplicating `PHASE_TABLE`
(REQ-61), (06-06, WR-01) that no live doc wrongly denies review's --workspace support — premise pinned against `run_review`'s real signature; the matcher covers three denial wordings, with pattern tests pinning both denial and corrected phrasing — and that every `dependency-sinks.json` catalog entry's `sink`/`indicators` tokens appear inside the specific table row named by its `cls` value in `attack-classes.md` — not merely anywhere in the file — so recon's class table never drifts from the catalog, in the row `reconcile_plan` actually routes by. Two more guards pin the class-file side of that routing: every catalogued `cls` value (`ssrf`, `expr-eval-rce`, `ssti`) has a matching `agents/classes/<cls>.md` file, and `expr-eval-rce.md` carries all five required section headings — so `reconcile_plan` can never select a class with no class prompt behind it. |
| `test_frozen_contract.py` | Byte-identity: `models.py`/`evidence.py` are frozen mirrors of a separate Go port (D-15) — a sha256 pin fails loudly on any edit. `fingerprint()` golden-value pins (fully-populated, minimally-populated, field-order-permuted) prove its behavior independent of that byte check. REL-03: `pyproject.toml`'s `[project] dependencies` stays `[]`. |
| `test_absence_rules.py` | The `rules/absence` semgrep pack against `fixtures/absence_repo`: it flags the missing-safe-option site, stays silent on the fixed site, and every rule's own block carries a `cls:` line after its `metadata:` line — not just a raw count of `cls:` occurrences in the file. One test per rule now covers all five. Each asserts the vulnerable site by `(file, rule, line)` and the hardened site's silence. The three added pairs are `engines_unsafe.go`/`engines_safe.go` for `cel.NewEnv` and `lua.NewState`, plus `fetch.py`'s two `requests.get` lines. Skips when `semgrep` is absent from `PATH`. |
| `test_astgrep.py` (4 new) | `build_rule()` emits a `not:`-wrapped relational rule; `run_astgrep_rule()` passes the rule inline via `--inline-rules` and returns parsed matches; the live case runs `fixtures/absence_repo/rego-absence.yaml` and asserts the Go absence rule flags `vulnerable.go` and stays silent on `safe.go`. Skips when `ast-grep` is absent from `PATH`. |

## The rest

The remaining files are per-module unit tests named `test_<module>.py` mirroring
`sec_overlay/<module>.py` (e.g. `test_calibrate.py`, `test_verify.py`, `test_dedupe.py`), plus
bench/citation tests (`test_bench.py`, `test_citations.py`) that need local seed data.

`test_verify.py`'s `test_verify_findings_static_only_routes_to_needs_deployment_testing` covers
ISSUE-053: a `static-only` re-verify routes the finding to `needs-deployment-testing`, not
`confirmed` — only `verified-static` promotes to `fixed`.

New `test_verify_causes.py` (REQ-21) covers `verify.VERIFY_CAUSES`: `verify_patch` now returns one
of five named causes (`verified-static`, `not-fixed`, `patch-not-applied`, `rule-no-match`,
`unconfirmed`) instead of overloading `static-only`, `_CAUSE_TO_VERIFICATION` maps every cause to
a legal `Finding.verification` value, `verify_findings` records `verify:cause:<cause>` in history,
and an unmapped cause degrades to `static-only` rather than laundering an unknown verdict clean.
`test_verify.py`'s `test_verify_patch_static_only_when_class_not_detectable` was renamed to
`test_verify_patch_rule_no_match_when_class_not_detectable` and now expects `"rule-no-match"`.

New `test_verify_configs.py` (REQ-22) covers a `resolve_configs(ws, fallback)` helper: it reads
the semgrep rulesets `recon` already planned in `kb/scan-profile.json` and falls back to the
caller's scalar only when the profile is missing, unreadable, or plans no rulesets — so a finding
is re-verified against the ruleset that actually flagged it, not an unrelated caller-supplied one.

`test_evidence.py` gained coverage for the shared tier/status vocab: `TIER1_RECEIPTS |
TIER2_RECEIPTS` partitions `_MECHANICAL` exactly, `receipt_tier()` grades colon-form sources,
`confirms_alone()` requires a Tier-1 receipt, and `SHIPPING_STATUSES`/`RUNTIME_DISPOSITIONS` match
their fixed literal sets. Two more guards cover the `dependency-catalog` receipt:
`test_dependency_catalog_is_a_tier_two_receipt` checks it sits in `TIER2_RECEIPTS`, not
`TIER1_RECEIPTS`, and grades to tier 2; `test_dependency_catalog_alone_cannot_confirm` checks
`confirms_alone()` returns `False` for it alone and `True` once a Tier-1 receipt joins it.

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

`test_phase_artifact_contract.py` gained four tests pinning REQ-40: `report` must declare
`reports/redteam-plan.md` as an input, `redteam` must run before `report`, `render_ndt` must
accept a `has_redteam_plan` keyword and omit the pointer when false, and `report.py` must hold
no `redteam-plan.md` filesystem probe. All four are green. `phases.py` moves `redteam` ahead of
`report` in `PHASE_TABLE`; `report.py` threads a `has_redteam_plan` keyword through `render_ndt`,
`_ndt_next_actions`, `to_markdown`, and `write_finding_details`, and `write_report` takes the
same keyword instead of probing the filesystem for `redteam-plan.md`. `driver.py`'s `_act_report`
passes `has_redteam_plan=True`, since the driver only calls `write_report` after the `redteam`
phase has run.

`test_phases.py`'s `test_redteam_precedes_the_artifact_gate` is renamed
`test_redteam_precedes_the_report` and now asserts `demote-noise` < `redteam` < `report` <
`artifact-gate`, tracking the REQ-40 reorder.

`test_report.py`'s `test_report_links_redteam_plan_and_shows_receipts` now calls `write_report`
with `has_redteam_plan=True`, since the probe it used to rely on is gone. Three REQ-03 tests —
`test_below_bar_ndt_next_action_points_at_the_gaps_section`,
`test_unrunnable_ndt_next_action_points_at_the_preconditions_section`, and
`test_directive_ndt_next_action_points_at_the_directive_section` — gained the same keyword on
their `to_markdown` calls, because `_ndt_next_actions` returns a fixed no-plan action for every
finding when the caller omits it.

`test_report.py` gained `test_main_probes_redteam_plan_when_present` and
`test_main_omits_redteam_plan_when_absent` (REQ-40 fix round 1). They call `report.main()` with
an argument vector, not `write_report()` directly. `main()` is a CLI boundary with no phase
context, so it probes `redteam-plan.md` on disk instead of taking `write_report`'s `False`
default.

`test_phase_artifact_contract.py`'s `test_report_module_holds_no_redteam_plan_probe` is reversed
to `test_only_the_report_cli_probes_for_the_redteam_plan` (REQ-40 fix round 1). The old test
banned the probe substring anywhere in the module, which was broader than REQ-40 states. The
replacement asserts the probe appears exactly once in `report.py`, inside `main()`, and confirms
`write_report` and `write_finding_details` hold none.

`test_phase_artifact_contract.py` gains four tests pinning REQ-43: `validate-fix` must sit
between `patch` and `verify` as an agent phase naming `validate-fix.md`; `verify` must declare
`kb/gates/validate-fix.json` as an input; `apply_fix_gates` must stamp a scored verdict into a
finding's history without changing its `status`; and `sec_overlay.verify` must name `score_fix`.
All four fail: `validate-fix` is absent from `PHASE_TABLE`, `verify` declares no such input,
`apply_fix_gates` does not exist, and `verify.py` names `score_fix` nowhere.

When you add or change a test file, update this README's counts and guard list in the same commit
(enforced by the pre-commit hook).

The review-improvements test files (`test_cluster.py`, `test_selfscore.py`, `test_sarif.py`,
`test_calibrate.py`, `test_report.py`) are `ruff format`-clean; run `ruff format` before
committing edits. (`test_scope.py` is deleted — REQ-47.)

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

Four more guards pin the site-keyed surface. Two sinks in the same class at different files
produce two surfaces, `ssrf@a.py:10` and `ssrf@b.py:20`, instead of one shared class surface.
A candidate sink at one site keeps its own surface `needs_follow_up`. The ledger stays
`partial` even though a sibling site in the same class is confirmed. A class with no finding
still emits one class-level surface keyed by the bare class name. Two findings landing on the
same site collapse into one surface, so `surfaces` ids stay unique.

Two more guards pin Fix round 1's C1/I1/I2 fixes. `test_per_site_surface_carries_cls_and_site`
asserts a per-site surface keeps its `cls` and `site` fields.
`test_per_site_pending_surface_validates_and_has_reason_and_next_step` asserts a per-site
`needs_follow_up` surface carries a non-empty `reason` and `next_step` and that
`validate_coverage_ledger` accepts the builder's own output.

`test_correlate_rethreshold.py` gained
`test_demote_when_enforcer_ledger_is_site_keyed`. It builds a real, site-keyed coverage ledger
via `build_coverage_ledger`, not a hand-written dict. It asserts `rethreshold`'s demote path
still resolves the enforcer's disposition through `_ledger_disposition`'s `cls`-field match.

`test_route_control.py` (new, ISSUE-027/029/036) covers `route_control.py`: a table control the
architecture markdown omits is a `needs_follow_up` gap, a table entrypoint the threat model drops
is a gap, no gap when everything is present, and `record_route_gaps` round-trips a gap's
`reason`/`next_step` through `kb/coverage-ledger.json` while `validate_coverage_ledger` still
returns no errors. Word-boundary gap tests pin the fix for substring false-negatives: a control
that is a substring of a longer word (`auth` inside `authorization`) is still a gap, the same
control as a standalone token is covered, and an entrypoint carrying path punctuation (`/login`)
still matches as a standalone mention. Four more guards pin the census-first table. It stamps
`source: "route-census"` and includes the census route when a `census=` list is passed. It falls
back to `source: "scan-profile"` when no census exists. `check_census_routes` reports a
code-registered route the profile never mentions, staying silent when the profile names the route
anywhere in its JSON.

Two more guards cover `check_catalog_classes`. The OPA catalog entry (`opa-rego-http-send`,
class `ssrf`) becomes a `needs_follow_up` gap when `attack_surface` omits `ssrf`. The same entry
stays silent when `attack_surface` already names `ssrf`.

A third guard passes two catalog entries that share a class. Both `cel-go-expression-eval` and
`starlark-go-exec` route `expr-eval-rce`, so the guard asserts exactly one gap. This pins the
dedupe branch a mutation test once found untested.

`test_route_census.py` (new) covers `route_census.py` with eight guards: every framework entry
carries a pattern and globs, framework names are unique, `FRAMEWORKS_PATH` resolves to the
tracked reference file, `census()` finds every route in the `fixtures/route_repo` fixture
(Flask and Go net/http), site ids are stable and unique across two runs, a failing ripgrep
runner returns an empty list rather than raising, `write_census`/`load_census` round-trip a
list of `RouteSite` records through `kb/route-census.json`, and `load_census` returns an empty
list when the file is absent. The two fixture-reading tests skip when `rg` is not installed.

`test_phase_gate.py` gained two guards for `recall_claims` (new, F2/F6). One builds a workspace
with `_workspace_with_census`. That helper round-trips through `route_census.write_census`, not
a hand-written JSON file. The guard asserts a census route recon never mentioned produces a
claim carrying a `file:line` ref. The other asserts an empty claim list when recon's
`entrypoints` already name the route.

A third guard covers the catalog half of `recall_claims`. It writes the declaring manifest into
a subdirectory and asserts every claim ref resolves under the target root. That fails on the old
overlay-relative ref, which the adversary's drop rule discarded.

`test_contracts.py` gained two guards. One confirms `agents/recall-adversary.md` exists and
states both its `OMISSION` row format and the `NO OMISSION FOUND` line, and mentions opus. The
other pins `agents/phase-adversary.md` unchanged, asserting `OMISSION` never appears in it —
the count-invariant verdict tables stay load-bearing.

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

`test_report.py`, `test_models.py`, `test_citations.py`, and `test_baseline_envelope.py`
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
`builtin_rule_docs_dir`, not real files), and that `resolve_rule_doc` is idempotent. Its
`test_builtin_path_rule_map_has_thirty_six_distinct_docs` pins the map at 36 docs after the
REQ-P2 port (Task 11).

`test_rule_glob.py`'s Task 11 (REQ-P2) block covers the 27 rule docs ported from open-code-review
(`_PORTED_DOCS`): each is on disk, carries the `Adapted from open-code-review (Apache-2.0)`
attribution line, and is referenced by a `BUILTIN_PATH_RULE_MAP` entry. `_NEW_PATH_RESOLUTIONS`
checks representative paths resolve to the right doc, including first-match order cases — the two
`.github` patterns before the plain `**/*.{yaml,yml}` pattern, and `package.json` / `Cargo.toml` /
`pom.xml` before the generic `json`/`xml` patterns.

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
omits (`demote-noise`, `selfscore`) are exempt from presence but a reorder of any
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

REQ-02 (Task 1 GREEN) changed both mirrored files, so `_MODELS_SHA256` and
`_EVIDENCE_SHA256` moved to the new digests in the same commit. No Go port is
reachable from this repository (`git ls-files "*.go"` returns only fixture
files), so the sign-off step named in the pin's failure message is the plan
author's ruling on this repository's copy, not a Go-port sync.

A follow-up fix to `models.py`'s module docstring (fix round 1, same GREEN
commit) moved `_MODELS_SHA256` again; `_EVIDENCE_SHA256` was untouched since
`evidence.py` did not change.

Phase 7 (v5.1 tech-debt cleanup, PR #23 nitpicks) tightens two existing suites without
adding tests. `test_rule_glob.py`'s CLI-forwarding test now passes `--workspace` and
asserts the value reaches `run_review` (TEST-01). `test_review_live.py`'s three WR-01
guard tests share a `_git_spy` helper that monkeypatches `subprocess.run` with a
recording spy and assert an empty call list, proving the `--root` guard exits 2 before
any git subprocess runs (TEST-02). `test_cli.py`'s pre-existing ruff `I001` import
order is fixed, so a full-repo `ruff check` runs clean (LINT-01).

Phase 8 (v5.1, DOC-03) promotes `selfscore` from a deliberately-omitted PHASE_TABLE row to
an enforced label in `test_docs_invariants.py`'s `_PHASE_DOC_LABELS`: the CLAUDE.md
phase-order block must now carry `Selfscore` between `Report` and `Red Team`, in
PHASE_TABLE order. Only `demote-noise` remains a condensed-view omission.

`test_dependency_sinks.py` (new) covers `sec_overlay.dependency_sinks`: the shipped
catalog loads and passes `validate_catalog` with zero errors; the `opa-rego-http-send`
entry exists with `cls == "ssrf"`, `package == "github.com/open-policy-agent/opa"`,
`"go.mod"` in its manifests, and a non-empty `safe_option`; `catalog_ids()` returns the
same id set as loading the catalog directly, with no duplicate ids; and
`validate_catalog` reports a defect fragment (`entries`, `package`, or `duplicate`) for
each of three malformed documents — an empty entries key, an entry missing a required
field, and an entry list with a duplicate id. Four more guards cover manifest matching
against the `fixtures/dep_sink_repo` fixture (a `go.mod` declaring the OPA dependency
plus a `policy.go` using it): `match_manifests` finds only `opa-rego-http-send` in that
fixture; `matched_classes` reduces it to `["ssrf"]`; a repo with an unrelated `go.mod`
matches nothing; and a `go.mod` planted under `node_modules/` is ignored, proving the
vendored-directory skip.

Three guards in `test_partition.py` cover `reconcile_plan`'s new `target_root` keyword:
passing the `dep_sink_repo` fixture as `target_root` adds `ssrf` to a plan that only
named `authz`, with `authz` still first (a planned class is never removed or reordered);
omitting `target_root` leaves a plan unchanged; and passing `target_root` when `ssrf` is
already planned does not duplicate it.

Two more guards in `test_findings_gate.py` cover the catalog-id check:
`test_findings_gate_rejects_an_unknown_catalog_id` writes a `dependency-catalog:not-a-real-entry`
source and checks the gate names that id in an error; `test_findings_gate_accepts_a_known_catalog_id`
writes `dependency-catalog:opa-rego-http-send`, a real catalog id, and checks the gate
raises no `dependency-catalog` error for it.

Two more guards in `test_bucket_b.py` cover `emit_semgrep_rule`'s `safe_option` keyword.
`test_emit_semgrep_rule_emits_the_absence_shape_when_a_safe_option_is_named` checks three
things: the rule id sits under `sec-overlay.absence.`, a `pattern-not` half names the safe
option, and `metadata.safe_option` records it.
`test_emit_semgrep_rule_without_a_safe_option_is_unchanged` checks the plain rule id and
patterns stay unaffected.

Two new guards in `test_phases.py` cover the `route-census` row wired into `PHASE_TABLE`.
`test_route_census_runs_before_recon` asserts its index precedes `recon`'s index.
`test_route_census_declares_no_inputs` asserts the spec is deterministic, takes no inputs,
and declares exactly one output — the census never reads recon's own artifact. A new guard
in `test_driver.py`, `test_route_census_phase_writes_the_census_file`, runs
`DETERMINISTIC_ACTIONS["route-census"]` against the `fixtures/route_repo` fixture and
checks `kb/route-census.json` exists afterward. `test_docs_invariants.py`'s
`_PHASE_DOC_LABELS` gained a `"route-census": "Route census"` entry, so the CLAUDE.md
phase-order guard also enforces this new row's position ahead of `Recon`.

`test_preflight.py::test_rg_is_a_required_tool` checks `TOOLS` names `rg` and that
`_OPTIONAL` excludes it. Both `route_census.py` and `structural_index.py` shell out
to ripgrep, so a missing binary must fail preflight rather than the phase itself.

`test_driver.py` gained
`test_recall_gate_phase_records_an_unmentioned_census_route_as_a_ledger_gap`. It runs
the new `DETERMINISTIC_ACTIONS["recall-gate"]` action against a workspace whose census
names a route the scan profile never mentions, then asserts `kb/coverage-ledger.json`
holds that gap. `recall_claims` still reshapes the same checks for the recall
adversary. The ledger write itself now comes from this deterministic phase, not from an
adversary call that no code path reaches.

`test_phase_gate.py` gained
`test_recall_claims_include_a_real_catalog_class_recon_omitted`. It uses
`dependency_sinks.load_catalog()`'s real `ssrf` entry, not a synthetic `SinkEntry`. A
deleted `check_catalog_classes` loop inside `recall_claims` fails this test, instead of
leaving the suite green.

`test_docs_invariants.py`'s `_PHASE_DOC_LABELS` gained a `"recall-gate": "Recall gate"`
entry. The CLAUDE.md phase-order guard had silently skipped `recall-gate` on the earlier
label miss. It now enforces the row's position right after `Recon`.

- `test_bench.py` also locks the REQ-M1 F1 contract: `_metrics` carries `f1`
  (`2PR/(P+R)`), `None` when undefined; the scorecard markdown renders it.

- `test_bench.py` locks REQ-M5 variance: `aggregate_scorecards(cards)` reports
  mean/min/max per metric (precision, recall, f1, fp_rate) across repeated runs,
  and skips `None` metrics (a metric with no defined value yields
  `{"mean": None, "min": None, "max": None}`); `test_run_repeated_writes_aggregate`
  locks that `run_repeated(..., repeats=N)` writes each `run-<n>/scorecard.md` and
  the parent `scorecard_agg.{json,md}`.

- `test_bench.py` locks REQ-M6 cost columns: `tally(results, corpus, cost=...)`
  attaches a `cost` block (`tokens`, `wall_time_s`, `usd_per_confirmed_tp`) to
  `to_dict`/markdown; `usd_per_confirmed_tp` is `usd_estimate / real-confirmed TP`
  (`None` when no TP), rendered as a labeled estimate; the section is omitted when
  no cost is supplied. Per-class FP-rate rows render in the "By class" table.

- `test_bench.py` locks REQ-T3c/T3h verified-fix rate: `tally(results, corpus,
  findings_by_id=...)` reports a `verified_fix` block (`fixed`, `confirmed`,
  `rate` = (`FIXED` ∪ `verified-static`) / confirmed true-positives) plus a
  headline markdown row, and omits it when no fix data is supplied.

- `test_bench.py` locks REQ-T3d coverage honesty: `tally(results, corpus,
  coverage_ledgers=...)` reports a `coverage_honesty` block (`runs`,
  `unsupported`, `rate`), flagging any run whose ledger claimed
  `completeness == "complete"` while surfaces need follow-up or `deferred` /
  `open_questions` were non-empty, plus a "Coverage honesty" markdown section;
  omitted when no ledgers are supplied.

- `test_bench.py::test_scorecard_markdown_states_scope_confound` and
  `test_docs_invariants.py::test_bench_readme_documents_annotation_and_reproducibility`
  lock REQ-R3 + REQ-R1/R4: the scorecard markdown states the scope confound
  ("reviews less"), and `bench/README.md` carries the "## Annotation protocol",
  "## Reproducing the benchmark", and "## Scope confound" sections with
  single-maintainer adjudication stated plainly.

- `test_calibrate.py` also locks REQ-P9: a judge `severity-inflated`/`downgrade`
  verdict writes the downgraded severity band back to `f.severity` with a
  `calibrate:severity-downgraded` history event; no verdict leaves severity alone.

- `test_bench_driver.py` locks REQ-M2: `HeadlessDriver` token substitution,
  failure recording (never raises, never fabricates), and `CCSkillAdapter`
  grading the driven workspace via `reportable`.

- `test_bench.py::test_seed_corpus_has_min_entries` locks REQ-M4: the seed
  corpus holds at least 30 entries with at least 3 `dep-cve`, 5 `public-app`,
  1 negative, and 1 locked entry, and validates clean.

- `test_bench.py::test_tier1_detected_reads_receipt_candidates` locks the
  detection-grading reader (REQ-M4): `tier1_detected` returns any-status findings
  backed by a Tier-1 receipt, where `reportable` (confirmation) returns none.

- `test_bench.py::test_run_benchmark_only_local_skips_http` locks the offline CI
  gate (REQ-M4): `run_benchmark(only_local=True)` grades local fixtures and never
  clones http targets.

- `test_review_agent.py` + `test_bundle.py` lock REQ-P1 (sibling context): the
  review prompt embeds sibling diffs as fenced blocks, renders them largest-first,
  truncates any sibling over `cap_tokens` with an `omitted (token cap)` marker, and
  annotates each embedded sibling in the changed-files block; `group_bundles` pairs
  C/C++ header-impl files (`.h/.c`, `.hpp/.cpp`) and interface/impl stems
  (`svc.ts`/`svc.impl.ts`) within a directory, and splits any unit over
  `MAX_UNIT_TOKENS` when per-file `diffs` are supplied. The size estimate is
  `review_budget.estimate_tokens` (`len // 4`), shared with REQ-P4.

- `test_aacr_adapter.py` locks REQ-M3: `aacr_entries` maps AACR dataset rows to
  `source="aacr"` corpus entries that validate and never move the real-confirmed
  headline; `ocr_findings` parses `ocr review --format json` into benchmark-only
  CONFIRMED findings tagged `llm-claimed:ocr`; and `Scorecard.to_markdown` carries
  the same-judge caveat block for cross-tool comparisons. REQ-T3e: a
  security-category row is tagged `source="aacr-security"` (a distinct slice that
  `tally` emits in `by_source`), and that slice never moves the real-confirmed
  headline.

`test_rule_glob.py`'s `fake_run_review` spy gained `commit`, `workspace_dirty`,
`plan`, `token_budget`, `background`, and `tier` keyword parameters to match the
real `run_review` signature after the `--commit`/`--workspace-dirty` review scopes
(4918b39) added those keyword arguments to `main()`'s `review` dispatch — the same
stub-drift `TypeError` class the `model`/`workspace` fixes closed before.

`test_contract_lint.py` (REQ-32, Task 5 RED) adds three failing tests for the last
open contract-lint property. `test_precondition_cap_thresholds_are_published` checks
`prompt-constants.md`'s `SEVERITY_PRECONDITION` block states every cap in
`calibrate.PRECONDITION_CAPS` plus `PRECONDITION_CAP_FLOOR`, and calls out "weight"
so the block cannot silently drift back to a count-based claim.
`test_precondition_cap_reads_the_published_table` checks `_precondition_cap` derives
its ceiling from `PRECONDITION_CAPS` instead of a second hardcoded copy.
`test_dispatch_tokens_are_a_single_source` checks `driver.DISPATCH_TOKENS` holds
`TARGET`, `WORKSPACE`, `SHA`, and `ATTACK_CLASS` as valid token names. All three
fail to import: `PRECONDITION_CAPS`, `PRECONDITION_CAP_FLOOR`, and `DISPATCH_TOKENS`
do not exist yet on `calibrate.py` and `driver.py`. (REQ-08, Task 5 GREEN gave this
test teeth: it now calls `render_dispatch` and asserts the rendered `substitute:`
line's token set equals `DISPATCH_TOKENS`, so it fails if `render_dispatch` ever
stops reading that constant — see the REQ-08 entry below.)

New `test_dispatch_classes.py` (REQ-17, RED) covers the attack-class fan-out
value in the dispatch block. It asserts a multi-class list, a single-class
list, and the omitted-token case round-trip through `render_dispatch`'s
`{{ATTACK_CLASS}}` substitute value as JSON. Two of the four tests fail
against the pre-fix comma-joined string.

New `test_prompt_tokens.py` (REQ-08, RED) checks every token an audit-lane
prompt uses is in `driver.DISPATCH_TOKENS`. `test_every_dispatched_prompt_token_is_substitutable`
scans the 11 `PHASE_TABLE` prompts and fails naming three gap tokens:
`OVERLAY_ROOT` (11 files), `HELPERS_DIR` (5 files), `FP_FEEDBACK` (2 files).
`test_fp_feedback_token_names_a_written_file` calls `render_dispatch` and
fails because `{{FP_FEEDBACK}}` is not in the substitute line yet.

`test_prompt_tokens.py` (REQ-08, GREEN): both tests pass now that
`DISPATCH_TOKENS` carries `OVERLAY_ROOT`, `HELPERS_DIR`, and `FP_FEEDBACK`.
`render_dispatch` writes the prior-rejection block to `<ws.kb>/fp-feedback.md`
and substitutes that path — a multi-line `<untrusted>` envelope cannot ride
the space-joined `substitute:` line. `test_dispatch_classes.py`'s
`test_attack_class_value_carries_no_space` hardcoded the old token count (`4`)
and needed a fix to `len(DISPATCH_TOKENS)`; no other pre-existing test needed
a change.

New `test_canonical_classes.py` (REQ-09, RED) covers a finding's `cls` against
a canonical attack-class key set. It fails to import: `clsmap.canonical_classes`
does not exist yet.

`test_canonical_classes.py` (REQ-09, GREEN): all five tests pass now that
`clsmap.canonical_classes()` exists. `test_contracts.py`'s
`test_investigate_example_passes_the_gate` gained one normalization —
`investigate.md`'s documented example carries the `{{ATTACK_CLASS}}` token as
its `cls`, so the test rewrites it to `"sqli"` before writing the finding,
matching the two normalizations already there for `file`/`line`. No other
pre-existing test needed a change: a census of every `cls=`/`"cls":` literal
under `helpers/` found no other value outside the derived 51-key set.

New `test_report.py::test_report_renders_no_dataflow_percentage_line` and
`test_prefilter.py::test_run_prefilter_writes_no_coverage_artifact` (REQ-04)
now pass: `coverage.py` is deleted, `to_markdown` no longer prints a
"Dataflow coverage" line, and `run_prefilter` returns no `"coverage"` key
and writes no `kb/coverage.json`. `test_report_renders_coverage_section` and
`test_run_prefilter_result_has_coverage` — the two tests that pinned the
deleted behaviour — are deleted with it, and so is `test_coverage.py` (its
whole module is gone). `test_a_partial_ledger_claims_no_full_coverage`
(REQ-04) already passed — a pre-existing regression guard, not a red test.

New `test_profile.py::test_from_dict_accepts_a_route_summary_key` and
`::test_validate_profile_rejects_a_non_object_route_summary`, plus
`test_driver.py::test_recall_gate_derives_route_summary_from_the_census`
(REQ-11, RED). `route_summary` moves from a hand-authored recon field to a
derived census-coverage object; the three tests fail today because
`ScanProfile` has no such field, `validate_profile` names no such error, and
the recall gate writes no such key back into the profile.

The three tests pass at GREEN. `test_profile.py`'s `_valid_dict()` gained a
`"route_summary": {}` entry because `test_scanprofile_roundtrip` asserts
`from_dict(d).to_dict() == d`, and `to_dict` now emits the new field.
`test_run.py`'s `_profile()` builder gained the same entry so both canonical
profile fixtures carry the full field set.

Three more tests land RED for REQ-25:
`test_dependency_sinks.py::test_indicator_classes_routes_without_a_manifest`,
`::test_indicator_classes_is_empty_without_an_indicator`, and
`test_partition.py::test_reconcile_plan_routes_a_class_on_an_indicator_hit`.
A Bazel or vendored target declares no manifest, so manifest matching alone
leaves its whole attack surface unrouted. The first two fail today with
`ImportError: cannot import name 'indicator_classes'`; the third fails because
`reconcile_plan` returns `['authz']` with no `ssrf`.

Four more tests land RED for REQ-24: `test_driver.py`'s
`test_findings_gate_records_a_discovery_wave`,
`::test_repeated_findings_gate_runs_reach_a_terminal_reason`,
`::test_a_saturated_ledger_stops_re_dispatching_investigate`, and
`test_contracts.py::test_investigate_prompt_carries_wave_language`. The
discovery ledger exists as a library but nothing calls it, so the
loop-until-dry bound is prose in a manual, not a mechanism. The first two fail
with `FileNotFoundError` on `kb/discovery-ledger.json`, the third with
`ImportError: cannot import name '_investigate_is_saturated'`, and the fourth
because `agents/investigate.md` names neither a wave nor saturation.

## 2026-08-31 — REQ-03 red: the next action names the wrong section

`test_report.py` gains three tests that read the "Next action" cell of a
triage row. `test_below_bar_ndt_next_action_points_at_the_gaps_section`,
`test_unrunnable_ndt_next_action_points_at_the_preconditions_section`, and
`test_directive_ndt_next_action_points_at_the_directive_section` each build a
needs-runtime finding that `redteam.discriminate` sorts into a different
bucket. `report.py` hardcodes one action for all three, so every row tells the
reader to run a directive. Two of the three findings have no directive to run.
All three fail with `assert 'run redteam-plan test' == '<expected>'`.

## 2026-08-31 — REQ-05 red: an empty measurement still prints its header

`test_report.py` gains two tests on the run-economics section.
`test_run_economics_omits_a_measured_header_with_no_body` passes an economics payload that holds
wall-clock data and nothing else, then asserts that the two token headers do not print.
`test_run_economics_section_absent_when_nothing_was_measured` passes an empty payload and asserts
the `## Run economics` heading is absent. `report.py` prints both token headers unconditionally
and the heading whenever the payload is truthy, so a run that measured nothing still claims two
measurements. Both fail on the header assertion.

## 2026-08-31 — REQ-31 red: no terminal gate reconciles the artifacts

`test_artifact_consistency.py` is new. Twelve tests drive the terminal consistency gate through
its six checks — dangling `findings/<id>.md` links, a next action whose `redteam-plan.md` section
omits the finding, a completeness claim the coverage ledger denies, a self-score that contradicts
the rendered counts, a `(measured):` header over an empty body, and a triage title truncated
mid-word — plus its `kb/gates/artifact-consistency.json` audit trail, its
`scan_options.consistency_gate` opt-out, its degrade-to-no-op path on a workspace with no report,
and its position between `artifact-review` and `postflight` in `PHASE_TABLE`. All twelve fail at
collection with `ModuleNotFoundError: No module named 'sec_overlay.artifact_consistency'`.

`test_report_optional_sections.py` pins REQ-33: the eight Part D elements a finding page must carry. It builds one `Finding`, stashes the eight keys on the finding overflow attribute that `workspace.read_findings` uses, and renders it. Five tests assert that every label appears, that a list value renders as bullets, that `exact_request` renders inside an ```` ```http ```` fence, that an absent key renders nothing, and that the condensed medium tier still carries the sections. Four of the five fail against `report.render_finding`, which has no reader for the overflow.

`test_signal_channels.py` pins REQ-34: a red-team `expected_signal` may name several observation channels. Six tests drive `render_util.signal_lines` with a two-channel list — an in-band boolean that needs no egress and an out-of-band collector hit that does. Three assert the channel names, the egress markers, and one secure plus one insecure line per channel. Three more hold the shapes that already work: the `{secure, insecure}` dict, a bare string, and an empty value. The three list tests fail because `signal_lines` has no list branch and returns nothing.

`test_ste_lint_wrapped.py` pins REQ-12: the STE linter must not reject the sentence its own rule block mandates. Five tests cover two things. Two assert the reworded three-sentence form lints clean and that `references/prompt-constants.md` publishes it in place of the semicolon form. Three assert `_prose_blocks` folds a wrapped list item into one block, still flags an over-long sentence spread across the wrap, and keeps an unindented paragraph after a list separate. Two fail: the constants file still carries the semicolon form, and a continuation line still becomes its own block.

Two deviations from the plan are recorded here. The plan's two wrapped-item tests asserted on `lint_prose` errors; both passed against the unmodified linter, because a split block is error-free in the first case and already over the word cap in the second. The tests assert on `_prose_blocks` output instead, which is the behaviour REQ-12 changes. Cost: the tests pin a private helper, so a refactor that preserves `lint_prose`'s contract but renames `_prose_blocks` breaks them. A third test asserting the whole of `prompt-constants.md` lints clean was written and then removed — the file carries 37 pre-existing violations, and REQ-12 does not ask for a full-file cleanup.

`test_codeql_go_build.py` pins how a Go CodeQL database is built (REQ-14). CodeQL's default Go extractor runs an autobuild, which compiles the target in its own tree. That write breaks the read-only-source invariant. Six tests cover two layers. Three capture the `codeql database create` argv through a stub runner and assert that Go passes `--build-mode=none`, that Python passes no build mode at all, and that Go still names the source root. Three drive `run_prefilter` with a CodeQL unit that raises, and assert that a Go failure records `skipped_reasons["codeql-go"] = "build-unfenceable"`, that a Python failure records no such key, and that the key never appears in `backends_run`. Two fail: the create argv carries no build mode, and the prefilter fold records no Go reason.

The reason key is deliberately not a backend name. `run_prefilter` asserts that every planned backend reports a result, and `codeql-go` is a reason attached to the `codeql` backend, not a seventh backend. The third prefilter test guards that distinction.

The REQ-14 import block was reordered by `ruff --fix` after the red commit. The change is import order only.

`test_prove.py` pins the opt-in proof-by-execution lane (REQ-30). Nineteen tests cover seven layers. Three assert the flag gate: `prove_enabled` is False without a scan profile, False when `scan_options.prove_findings` is absent, and True only when the key is exactly `true`. One asserts that `run_prove` mutates no finding when the lane is off. Two pin the receipt vocabulary — `prove.is_reproduction_receipt` accepts `reproduction` and rejects `semgrep:x`, while `evidence.is_tool_receipt("reproduction")` stays False, because `"reproduction"` is not a member of `_MECHANICAL`, the union of the two tool-receipt tiers. Five pin the soundness guard: an `entrypoint` proof promotes an `ssrf` finding to `confirmed`, a `slice` proof leaves it `raw` and `needs-runtime`, a `slice` proof records `prove: slice-unbuildable`, a `sqli` finding never promotes, and a missing toolchain records `prove: toolchain-absent`. One asserts that `findings_gate` accepts a `confirmed` finding whose only evidence source is `reproduction`. One drives the stdlib loopback collector and asserts it reports the observed request path. The last five cover the wiring: `Workspace.repro` exists after `ensure()`, `finding.schema.json` declares the seven-key `reproduction` object, the driver skips the phase when the lane is off and dispatches it when the lane is on, and `preflight_report` reports the prove-lane toolchains. A fifth wiring test originally pinned `prove` directly after `redteam`; REQ-40 moved `report` and `selfscore` between them, so the test is renamed `test_the_phase_table_places_prove_directly_before_the_artifact_gate` and now asserts only `redteam` < `prove` and `prove` immediately before `artifact-gate`.

All nineteen fail at collection: `sec_overlay.prove` does not exist.

The prove lane is now green: `sec_overlay/prove.py` exists, and the six wiring points it needs are
in place. One correction to the paragraph above — `test_prove.py` holds twenty tests, not nineteen.
The twentieth asserts that `sec_overlay.evidence` still imports, which proves the module-level
partition assert survives the new receipt vocabulary.

One test needed a fixture repair. `test_the_gate_accepts_a_reproduction_only_confirmed_finding`
failed on an unrelated pre-existing gate rule: a shipping finding must carry a non-empty `impact`.
The finding now sets `impact`, so the test asserts the one thing it was written to assert.

New `test_phase_artifact_contract.py` pins REQ-42: no phase reads an artifact no earlier phase
writes. Three tests assert `factcheck` is absent from `PHASE_TABLE` and `DETERMINISTIC_ACTIONS`,
`fact-checked` is absent from `VERIFICATION_VALUES`, and no `sec_overlay.factcheck` module or
`agents/factcheck.md` prompt exists. All three fail: the phase's only input, `kb/verdicts.json`,
had no producing phase, so every run recorded `factcheck: done` after doing nothing.

`test_phase_artifact_contract.py` gains two tests pinning REQ-41: `calibrate_findings` must
demote a `CONFIRMED` external-boundary finding to `NEEDS_DEPLOYMENT_TESTING`, and `validate.md`
must no longer carry the `external-boundary` ban it could not enforce — `trace` runs after
`validate`, so a blocker `trace` sets was never checked. Both fail: the status stays `CONFIRMED`,
and the banned phrase is still in the prompt.

The REQ-41 `risk_score` assertion now reads `f.risk_score is not None and f.risk_score <= 3`,
matching the null-check idiom already used in `test_calibrate.py` — `risk_score` types as
`int | None`, so a bare `<= 3` fails the type checker.

`test_phase_artifact_contract.py` gains one test pinning REQ-44: `verify_findings` reads the
whole finding set, then writes the whole set back, so a finding it never touched overwrites a
concurrent writer's change to that same finding with the stale copy from its own read. The test
writes two findings, has the injected verifier simulate a second writer changing the untouched
one mid-run, then asserts the untouched finding keeps the concurrent writer's value after
`verify_findings` returns. It fails: the untouched finding reverts to its pre-race value.

The REQ-44 test's `config` argument reads `""`, not `{}`: `verify_findings`'s `config` parameter
types as `str`, and the injected stub verifier ignores its `configs` argument entirely, so an
empty string satisfies `ty check` with no change in what the test exercises.

New `test_dead_lever.py` pins REQ-45: `run_postflight` must derive its drift set from a `target`
argument instead of dropping the parameter every caller left unpassed. Four tests build a
workspace whose prior context holds one settled non-finding, then drive `run_postflight` with a
fake git runner. One asserts a prior item on a file `git diff` reports as changed is dropped from
the merged context, and that the runner's `cwd` and argv carry `target` and the prior context's
pinned SHA. One asserts a prior item on an unchanged file survives. One asserts the merge key
strips a prior item's leading `./` before comparing it against `git diff`'s bare paths. Three
fail: `run_postflight` takes no `target` keyword at all.

New `test_constraint_enforcer.py` pins REQ-49: `_validate_object_fields` must reject a key no
`properties` entry declares when the schema sets `additionalProperties: false`, must still accept
every declared key, and must leave the object open when `additionalProperties` is the dict form
(a subschema for undeclared keys, not the closing boolean). Two more tests assert
`finding.schema.json` itself sets `additionalProperties: false` and that the golden fixture with
`render_stale: true` grafted on now fails — the deleted re-render lever's key no longer validates.
A prompt-scan test asserts no `agents/*.md` file still offers `render_stale`, and a text test
asserts `artifact-review.md`'s verdict vocabulary dropped to `"clean" | "downgrades"` with no
`forced_rerender` id list. `test_finding_schema.py`'s `test_unknown_extra_key_is_not_flagged`
becomes `test_unknown_extra_key_is_flagged`: the schema is closed now, so an undeclared key is an
error, not silent overflow.

All eight now pass. `_validate_object_fields` (`sec_overlay/schema.py`) gains a branch: when
`schema.get("additionalProperties") is False`, every key in `data` absent from `properties`
appends an `"<path>.<key>: unknown field"` error. `finding.schema.json` sets
`additionalProperties: false` at its root only — every nested object schema stays open, so a
later task's nested addition never trips this same branch. `artifact-review.md` drops the
`render_stale` lever and its `"re-render"`/`forced_rerender` verdict shape; `agents/README.md`'s
phase-6 row drops the same clause.

`test_artifact_consistency.py` gains three tests pinning REQ-53 clause (g): a report whose stated
`Needs runtime proof` count sits below the needs-runtime finding ids the report renders (triage
row, `## Detail` link, or `### <id> — ` heading) must be flagged, a SARIF result count that
disagrees with the report's total rendered finding count must be flagged, and a report that
states both the needs-runtime total and a `Leads pending external verification` split reconciles
against SARIF with no error. `test_report.py` gains one test asserting the stated needs-runtime
count includes external-unverifiable leads and that the report renders the split line — its
`dataclasses.replace` call needs a local `import dataclasses`, matching the two other tests in the
file that build a modified `Finding` this way; the module has no top-level `dataclasses` import.
All four fail before the fix: `artifact_consistency.py` has no clause reading SARIF or the
rendered id set, and `report.py`'s `Needs runtime proof` line counts only the non-external
needs-deployment-testing findings with no split line.

A fifth test, `test_gate_flags_a_triage_heading_with_no_rows_against_a_stated_count`, pins a fix
round on clause (g)'s render-surface guard: the guard narrowed from an OR across triage rows,
`## Detail` links, and section headings down to one structural check, `"## Triage" in report_md`.
The broader OR went silent on a report that emits the `## Triage` heading but no data rows while
the stated count stays non-zero — a `to_markdown()` rendering bug, not a missing artifact — and
this test fails against that broader guard while passing against the single-heading check.

`test_report.py` gains three tests pinning REQ-56. One test proves a high-severity needs-runtime
finding forces the "High-severity findings require immediate remediation" sentence, not a
"medium/low" sentence keyed only off confirmed findings. Two tests pin the new `triage_what`
helper: it drops a leading status sentence ("Confirmed.", "Provenance unresolved.") from a
finding's message before the What column renders it, so a rendered triage row never leaks the
finding's lifecycle state. The three tests use `dataclasses.replace` through a new module-level
`import dataclasses`; earlier tests in the file keep their own local `import dataclasses` lines,
left untouched.

`test_sarif.py` gains three tests pinning REQ-57. One test pins a cluster's `relatedLocations`:
each entry of `Finding.affected_sites` must become its own SARIF location, in list order, so a
systemic cluster stops shrinking to the single primary location. A second test pins the negative
case: a finding with no `affected_sites` carries no `relatedLocations` key at all. A third test
pins `result.properties.findingId`, so a SARIF consumer can name the finding a result came from.
`test_suppressed_findings_carry_insource_suppression` is renamed to
`test_suppressed_findings_carry_an_external_suppression` and its final assertion now expects
`kind == "external"`, not `"inSource"` — the prior kind asserted an in-file annotation that never
existed. The cluster and finding-id tests fail before the fix with `KeyError`; the renamed test
fails on the kind string. The negative test (no `affected_sites`, no `relatedLocations` key)
already holds against the unfixed code and stays green as a regression guard, not a red test.

`test_dedupe.py` gains `test_dedupe_stamps_a_fingerprint_on_a_rejected_finding`, pinning REQ-58.
Two `REJECTED` findings share one file and line but carry different `rule_id` values. The test
asserts both end up with a 12-character fingerprint and that the two fingerprints differ. It
fails before the fix because the stamping loop in `dedupe.py` only stamps findings whose status
is `RAW` or `CONFIRMED`, so both rejected findings keep a `None` fingerprint.

## Two artifact-consistency false halts, fixed (P4-15)

`test_artifact_consistency.py` gains `test_confirmed_only_report_does_not_halt_the_gate`, pinning
the fix to clause (g) part two. It drives the real pipeline end to end —
`write_report(ws, confirmed_only=True)` then `write_self_score(ws)` — on a workspace holding one
`CONFIRMED` finding and one needs-runtime finding, then asserts `run_artifact_consistency(ws) ==
[]`. It fails before the fix: `write_report` in confirmed-only mode writes SARIF from the
reportable set alone but still renders the needs-runtime row into the Markdown, so clause (g)
always saw a SARIF/report count mismatch on an otherwise-correct run.

`test_artifact_consistency.py` also gains `test_gate_degrades_a_legacy_score_missing_the_collapsed_key`,
pinning the fix to clause (d). It writes a self-score with a `needs_runtime` key but no
`needs_runtime_collapsed` key — the shape a `state.json` predates REQ-54 or a standalone
`sec_overlay.artifact_consistency` run supplies — against a report stating a different count, then
asserts `run_artifact_consistency(ws) == []`. It fails before the fix: the old fallback,
`score.get("needs_runtime_collapsed", score.get("needs_runtime", 0))`, ran the exact-equality
check against the uncollapsed count and flagged a contradiction that was never real.

`test_gate_flags_any_self_score_mismatch_against_the_report`'s score fixtures now carry
`needs_runtime_collapsed` alongside `needs_runtime` — the modern (post-REQ-54) shape. The test's
assertions are unchanged; only the input shape moved off the legacy path the fix above now
degrades instead of checks, so the test still exercises a genuine mismatch under clause (d)'s
current logic.

## 2026-09-01 — REQ-59 red: a verify hit matches by base filename, not by path

`test_verify_paths.py` pins the fix. Two tests assert `_rel_path` strips a scan root from a path
and leaves an unprefixed path untouched. Three assert `_path_matches`: it accepts two paths naming
the same file, accepts a repo-relative finding path under a scoped scan target, and rejects a
same-named file in another directory. One drives `_file_has_hit` end to end: a hit reported for
`b/util.py` must not satisfy a finding filed against `a/util.py`.

All six fail: `sec_overlay.verify` has no `_rel_path` or `_path_matches` attribute, and
`_file_has_hit`'s basename comparison treats `a/util.py` and `b/util.py` as the same file.

## 2026-09-01 — REQ-59 red: a cross-file fix reads as `not-fixed`

`test_verify_paths.py` gains three more tests. `test_patch_files_reads_the_post_image_paths`
asserts `_patch_files` returns the `+++ b/<path>` paths a diff writes, skips a `/dev/null`
deletion header, and returns an empty set for text with no diff header at all.
`test_a_cross_file_fix_is_not_reported_as_not_fixed` asserts `verify_patch` returns the new
cause `rule-no-target-file`, not `not-fixed`, when the patch never touches the finding's own
file. `test_the_new_cause_maps_to_a_legal_verification` asserts the cause is a member of
`VERIFY_CAUSES` and maps to `static-only`.

All three fail: `sec_overlay.verify` has no `_patch_files` attribute, and `VERIFY_CAUSES`
has no `rule-no-target-file` member.

## 2026-09-01 — REQ-60 red: a rule that fires on both constructions reads as `not-fixed`

`test_verify_paths.py` pins the `rule-no-discriminate` cause. `_evidence_hit` builds a `Finding`
with a chosen `line` and `evidence` string. `test_a_rule_that_matches_both_constructions_reports_no_discriminate`
stubs `_file_has_hit` to append a pre-patch hit then a distinct post-patch hit to its new
`detail` list, and asserts `verify_patch` returns `rule-no-discriminate`, not `not-fixed`.
`test_a_surviving_construction_still_reports_not_fixed` stubs the same hit twice and asserts
`not-fixed` — the same construction surviving is a real miss, not a discrimination failure.
`test_the_history_reason_names_both_lines` drives `verify_findings` end to end and asserts the
`verify:cause:rule-no-discriminate` history entry carries a `reason` naming both matched lines.

A fourth test, `test_a_stale_last_lines_record_does_not_leak_into_the_next_verification`, guards
a module-level pitfall: the line-carrying record a later fix introduces must be scoped per
`verify_findings` call, not per process. It runs two verifications back to back — the first with
a stubbed `_file_has_hit` that populates evidence, the second with a stub verifier that never
touches the record — and asserts the second finding's history entry carries no leftover `reason`.

All four fail: `_file_has_hit` accepts no `detail` keyword yet, so `verify_patch` cannot compare
pre-patch and post-patch evidence, and `sec_overlay.verify` has no `_LAST_LINES` attribute.

## 2026-09-01 — REQ-60 green: `rule-no-discriminate` compares evidence text

`_file_has_hit` and `_check` gain a keyword-only `detail` out-parameter. When given, every matching
scanner finding is appended instead of returning `True` on the first match. `verify_patch` collects
a `pre_detail` and a `post_detail` list this way, then calls a new `_post_verdict` helper. The
helper compares stripped evidence text, never line numbers, since an inserted line shifts every
later line and a same-line comparison would call an unfixed finding new. Disjoint non-empty
evidence sets return `rule-no-discriminate`. Any other case returns `not-fixed`.

`_post_verdict` records the pre-patch and post-patch line on a module-level `_LAST_LINES` dict,
since the cause is a plain string that carries no line data on its own. `verify_findings` reads
this dict right after calling `verifier` and adds a `reason` key to the history entry only when the
dict is non-empty, so `test_verify_findings_records_the_cause`'s exact-dict membership check for
causes with no evidence still holds.

`verify_findings` clears `_LAST_LINES` immediately before every `verifier` call, not only inside
`verify_patch`. A stub `verifier=` callable injected in a test bypasses `verify_patch` outright, so
clearing only inside `verify_patch` would let one finding's real line numbers leak into a later
finding's history entry that used a stub. The fourth test above pins this: two `verify_findings`
calls in one process, the second with a stub verifier, and asserts the second's history entry
carries no `reason` key.

`tests/test_verify.py`'s `fake_hit` at line 126 widens from five fixed positional parameters to
`(target_dir, config, file_path, cls, rules, **kw)`, so the new keyword-only `detail` argument
still binds when a test's stub does not care about it.

All 42 targeted tests pass. The full suite passes at 1843 tests (1839 plus these four).

## 2026-09-01 — P5-9 and F2: the cross-file guard and the multi-config loop

`test_verify_paths.py` gains three tests and updates one.

`test_a_cross_file_fix_with_a_clean_re_scan_is_verified` pins ruling P5-9. The
`rule-no-target-file` guard used to return before the copy, the apply, and the post-patch
re-scan, so a cross-file fix a cross-file backend (`codeql:dataflow`, or `sca` where the
finding cites the lockfile and the patch edits the manifest) would prove clean could no
longer reach `verified-static`. The test counts `_file_has_hit` calls and asserts the second
one ran. It failed with `assert 1 == 2` before the guard moved after the re-scan.

`test_a_cross_file_fix_is_not_reported_as_not_fixed` now monkeypatches `shutil.copytree`.
The guard no longer short-circuits the copy, so the test's fictional `/repo` target would
otherwise raise from `copytree`. Its assertion is unchanged: a surviving post-patch hit on a
patch that writes no file the rule fires in still returns `rule-no-target-file`.

`test_detail_accumulates_across_every_planned_ruleset` pins the multi-config loop. Two
configs, one firing pre-patch only and one firing on both sides with identical evidence text,
used to yield `pre_detail` and `post_detail` drawn from different rulesets and a false
`rule-no-discriminate`. `_check` now runs every config when the caller passes a `detail` list
and keeps the early return only on the detail-free path.

`test_path_matches_rejects_an_empty_path` pins the `_path_matches` guard. An empty `a` or `b`
made `a.endswith("/" + b)` true for any counterpart ending in `/`.
