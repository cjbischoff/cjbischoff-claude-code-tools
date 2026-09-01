# Changelog

This file follows the [Common Changelog](https://common-changelog.org) format.

## Unreleased

### Added

- New `tests/test_no_dead_helpers.py` pins REQ-48: an AST-precise scan walks every public
  function in `sec_overlay/`, and each one must either have a real Python caller in
  non-test `sec_overlay/`/`bench/` code, appear in `DEAD_ALLOWLIST` with a one-line reason,
  or appear in `PROMPT_ONLY` naming the agent prompt or `SKILL.md` that runs it by name. A
  second test fails the moment a listed entry gains a real caller, and a third fails the
  moment a listed entry names a function that no longer exists, so the two lists cannot
  drift from the tree silently. Reconciling the lists against the current tree dropped one
  stale `PROMPT_ONLY` entry (`scoring.py:score_fix`, now called directly by `verify.py`) and
  added one (`reflection.py:validate_verdict`, named only by `agents/README.md`).
  `report.to_markdown`'s unreached `token_spend` branch needs no entry: the scan is
  function-level, and `to_markdown` itself is still called by `write_report` and by
  `test_report.py`.

- `tests/test_dead_lever.py` pins REQ-47: `sec_overlay.scope` must no longer import, `sec_overlay.scanscope` must expose only `ScanScope`, `resolve`, `write_scope`, and `load_scope`, and `SKILL.md` must source the scope tokens from `run.env` instead of restating the old `kb/scan-scope.json` sentence. All three fail: `sec_overlay.scope` still imports, `scanscope` still exposes `rel_to_root`, and `SKILL.md` names neither `run.env` nor the replacement wording.

- `tests/test_dead_lever.py` pins REQ-46: `sec_overlay.cost` must expose exactly `record_timing` and `aggregate_timings_by_phase`, a bare workspace's rendered report must hold no "Tokens by" or "Estimated cost" line, and `SKILL.md` must never name `record_agent(`. Two of three fail: `cost` still exposes `record_agent`, `aggregate_by_phase`, `aggregate_by_model`, and `estimate_cost_usd`, and `SKILL.md` still names `record_agent(` in its cost-recording convention.

- `tests/test_phase_artifact_contract.py` gains a test pinning REQ-44: `verify_findings` must write back only the findings it read a verdict for, not the whole in-memory set. It fails: a concurrent writer's change to an untouched finding is overwritten with `verify`'s stale copy of that finding.

- `tests/test_phase_artifact_contract.py` pins REQ-43: `validate-fix` must sit between `patch` and `verify` as an agent phase, `verify` must declare the gate file `kb/gates/validate-fix.json` as an input, `sec_overlay.verify` must export `apply_fix_gates`, and `apply_fix_gates` must record a scored verdict in a finding's history without changing its `status`. Four tests fail: `validate-fix` is absent from `PHASE_TABLE`, `verify` declares no such input, `apply_fix_gates` does not exist, and `verify.py` names `score_fix` nowhere.

- `tests/test_report.py` gains two tests pinning REQ-40's CLI boundary (fix round 1). `report.main()` must probe `redteam-plan.md` on disk. It must not take `write_report`'s `False` default. One test fails. The CLI passes no `has_redteam_plan`, so the report omits the pointer even when the file exists.

- `tests/test_phase_artifact_contract.py` gains four tests pinning REQ-40: `report` must declare `reports/redteam-plan.md` as an input, `redteam` must precede `report`, `render_ndt` must accept a `has_redteam_plan` keyword and omit the pointer when false, and `report.py` must hold no `redteam-plan.md` filesystem probe. All four fail: `report` declares no such input, `redteam` still runs after `selfscore`, `render_ndt` rejects the keyword, and the probe is present.

- `tests/test_phase_artifact_contract.py` pins REQ-42: the factcheck phase must be deleted. Three tests assert `factcheck` is absent from `PHASE_TABLE` and `DETERMINISTIC_ACTIONS`, `fact-checked` is absent from `VERIFICATION_VALUES`, and no `sec_overlay.factcheck` module or `agents/factcheck.md` prompt exists. All three fail: the phase, the value, the module, and the prompt still exist.

- An opt-in proof-by-execution lane (REQ-30). `helpers/sec_overlay/prove.py` is the one module that runs target-derived code, and it runs only when `scan_options.prove_findings` is exactly `true` in `kb/scan-profile.json`. A new `prove` agent phase sits between `redteam` and `artifact-gate` and is driven by `agents/prove.md`; the driver skips it and records the stage when the lane is off, so a default run costs no model dispatch. A proof promotes a finding to `confirmed` only when the agent drove a real entrypoint, the class is one of `ssrf`, `cmdi`, `path-traversal`, `deserialization`, or `expr-eval-rce`, and the oracle observed the effect. `sqli` and `authz` route to a human-run harness. Every weaker outcome records a degradation reason and leaves the finding where it was. `Workspace.repro` gives the lane an out-of-tree build and run root, `findings_gate` accepts a `reproduction` receipt in place of a Tier-1 tool receipt, `finding.schema.json` declares the `reproduction` object, and `preflight_report` reports the lane's toolchains without blocking. The oracle is a stdlib loopback HTTP collector, so the lane needs no network egress and no new dependency. Trade-offs: `evidence.py` stays byte-identical for the D-15 frozen-contract test, so a `reproduction`-only confirmed finding leaves `receipt_tier` null and takes `runtime_disposition` `static-settled`.

- Failing tests pin the opt-in proof-by-execution lane (REQ-30). `helpers/tests/test_prove.py` asserts the `scan_options.prove_findings` flag gate, the `reproduction` receipt vocabulary, the scope soundness guard (an `entrypoint` proof promotes an auto-confirmable class, a `slice` proof never does, `sqli` never does), the two degradation strings, the phase-table position, `Workspace.repro`, the schema object, the driver skip, and the preflight toolchain report. All nineteen fail: `sec_overlay.prove` does not exist.

- `tests/test_phase_artifact_contract.py` gains two tests pinning REQ-41: `calibrate_findings` must demote a `CONFIRMED` external-boundary finding to `NEEDS_DEPLOYMENT_TESTING`, and `validate.md` must drop the `external-boundary` ban it never enforced. Both fail: the status stays `CONFIRMED`, and the prompt still bans the phrase.

- `tests/test_dead_lever.py` pins REQ-45: `run_postflight` must take a `target` argument and drop a prior item whose file `git diff` reports as changed against the prior context's pinned SHA. Three of four tests fail: `run_postflight` has no `target` keyword.

### Fixed

- `sec_overlay.scope` and `helpers/tests/test_scope.py` are deleted (REQ-47): `is_external_package` had no caller. `scanscope.py`'s `rel_to_root` is deleted too, for the same reason; the module now exposes only `ScanScope`, `resolve`, `write_scope`, and `load_scope`. `SKILL.md`'s scope-token paragraph now points at `run.env` (`run.py`'s `write_env`) instead of restating the old, inaccurate `kb/scan-scope.json` sentence.

- `sec_overlay.cost` holds only `record_timing` and `aggregate_timings_by_phase` (REQ-46). The harness never surfaced a subagent's token usage, so `record_agent`, `aggregate_by_phase`, `aggregate_by_model`, and `estimate_cost_usd` always rendered an empty "Tokens by" table or a zero "Estimated cost" line; all four and the `_RATES_USD_PER_MTOK` table are removed. `report.py`'s `_render_economics` now reads only a `by_phase_seconds` key and drops the "Run economics" heading when it is empty, unchanged from before. `bench/run.py` and `bench/tally.py` keep only the wall-time cost record (`wall_time_s`); the "Cost & latency" section keeps its latency row and drops the token/USD ones. `SKILL.md`'s cost-recording convention now names `cost.record_timing` instead of the removed `cost.record_agent`. `test_cost.py`, `test_report.py`, and `test_bench.py` drop their token/USD assertions and keep their wall-clock ones.

- `run_postflight` derives its drift set from a `target` argument instead of never receiving one (REQ-45). `_drift_since` diffs the prior context's pinned SHA against the current pass's SHA in `target`'s working tree and returns the changed files; `_merge` drops prior items on those files and keeps the rest. `_act_postflight` now passes `ctx.target` through, and the CLI gains a `--target` flag. `changed_files`/`target` merging is unchanged when both are supplied explicitly, and passing neither keeps every prior item, matching a first pass with no drift signal.

- The `validate-fix` node in the pipeline diagram carries its step number `11.5` (`skills/sec-overlay/README.md`), matching every neighbouring node's numbering style.

- `verify_findings` writes back only the findings it touched (REQ-44). It read the whole finding set with `read_findings`, then wrote the whole in-memory list back with `write_findings` regardless of which findings it changed — overwriting any finding another writer had mutated between the read and the write with `verify`'s stale copy. The `changed: bool` flag is replaced with a `touched: list[Finding]` accumulator; each of the two sites that used to set `changed = True` now appends the finding it just mutated, and the final write passes only `touched`. `write_findings` writes one file per finding (`workspace.py`), so a subset write needs no additional barrier.

- `calibrate` demotes a `CONFIRMED` external-boundary finding to `NEEDS_DEPLOYMENT_TESTING` (REQ-41). The rule lived only in the `validate` prompt, which cannot see the blocker `trace` sets afterward, so nothing enforced it. `calibrate.py`'s external-boundary block now flips `status` on top of the existing `risk_score` cap and `completeness_tier` set, so the report's external bucket — which reads NDT findings, not confirmed ones — sees it. `agents/validate.md` and `agents/README.md` drop the unenforced ban.

- `validate-fix` is wired as a phase between `patch` and `verify` (REQ-43). `phases.py` adds a `validate-fix` agent row naming `agents/validate-fix.md`, with `kb/gates/validate-fix.json` as its output and `verify`'s new input; `verify.py` gains `apply_fix_gates`, which reads that gate file, scores each finding's four gate statuses with the existing `sec_overlay.scoring.score_fix`, and appends a `validate-fix:<verdict>` history event without touching `status` or `verification` (a `partial`/`not_fixed` verdict sets `verification` to `not-fixed`; `unverifiable` sets it to `verify-error`). `driver.py`'s `_act_verify` calls `apply_fix_gates` before `verify_findings`, so the scored gate always lands before static re-verification runs. `agents/validate-fix.md`'s Output section now tells the agent to write per-gate statuses only, never a verdict, and never to edit a finding's `status` or `verification` directly. `verify.py` was also missing a `Finding` import needed by the new function; that import is added alongside the existing `FindingStatus` one.

- `report.main()` probes `redteam-plan.md` on disk again (REQ-40 fix round 1). The CLI entry point has no phase context, so `write_report`'s `False` default silently dropped the pointer even when the file existed. `write_report`'s docstring now states the reason as two sentences instead of one semicolon-joined sentence. `tests/test_phase_artifact_contract.py` replaces `test_report_module_holds_no_redteam_plan_probe`, which banned the probe substring anywhere in the module, with `test_only_the_report_cli_probes_for_the_redteam_plan`. The module-wide ban was broader than REQ-40 requires; the replacement pins the probe to exactly one occurrence, inside `main()`, and confirms `write_report` and `write_finding_details` hold none.

- `redteam` now runs before `report`, and `report.py` holds no filesystem probe (REQ-40). `phases.py` moves the `redteam` row ahead of `report` in `PHASE_TABLE`; `report` declares `reports/redteam-plan.md` as an input instead of checking `Path.exists()` at render time. `render_ndt`, `_ndt_next_actions`, `to_markdown`, `write_finding_details`, and `write_report` each take a `has_redteam_plan` keyword, defaulting to the pre-REQ-40 behaviour where a caller omits it. `driver.py`'s `_act_report` passes `has_redteam_plan=True`, since the driver only reaches `report` after `redteam` has run. `artifact_gate.run_artifact_gate` still hard-requires `redteam-plan.md` to exist, and still runs after `report`.

- The factcheck phase is deleted (REQ-42). Its only input was `kb/verdicts.json`. No phase wrote that file, so `_act_factcheck` did nothing on every run, and every run still recorded `factcheck: done`. The `fact-checked` verification value had no writer for the same reason. This change removes the `factcheck` phase row, the `sec_overlay.factcheck` module, the `agents/factcheck.md` prompt, and the `fact-checked` verification value from `evidence.VERIFICATION_VALUES`. `test_frozen_contract.py`'s two byte-identity digests move to match the trimmed `models.py` and `evidence.py`. A workspace resumed from an older run carries a `factcheck` stage key that no longer maps to a phase.

- A Go CodeQL database no longer builds inside the target tree (REQ-14). `codeql.run_codeql` appends `--build-mode=none` to `codeql database create` for Go only, because the default Go extractor autobuilds and writes into the reviewed source. `prefilter.run_prefilter` tags each CodeQL work unit `codeql:<lang>` so its result fold can record `skipped_reasons["codeql-go"] = "build-unfenceable"` when a Go unit fails; the `failed` entry keeps the bare backend name `codeql`, and `codeql-go` never joins `backends_run`. Trade-off: `--build-mode=none` resolves fewer cross-package references, so a Go target loses some dataflow an autobuilt database would find.

- The STE rule no longer breaks its own linter (REQ-12). `references/prompt-constants.md` mandated a front-matter sentence that used a semicolon, which the same block forbids; it now reads as three sentences. `ste_lint._prose_blocks` folds a wrapped list item into one block instead of two, so a sentence spread across a hard wrap has its words counted once. The splitter also closes an open paragraph on a heading, a table row, and a code fence, which it did not do before, so prose on either side of a heading is no longer merged into one block. Trade-off: the rest of `prompt-constants.md` still carries pre-existing lint violations that no gate checks.

### Added

- `tests/test_codeql_go_build.py` pins the Go CodeQL build mode (REQ-14). Six tests assert that `codeql database create` passes `--build-mode=none` for Go and no build mode for another language, and that a Go CodeQL failure records `skipped_reasons["codeql-go"] = "build-unfenceable"` without adding a backend. Two fail: the create argv carries no build mode, and the prefilter fold records no Go reason.

- `tests/test_ste_lint_wrapped.py` pins the STE self-consistency rule (REQ-12). Five tests assert that the sentence `prompt-constants.md` mandates lints clean, that the file publishes the reworded three-sentence form, and that `_prose_blocks` folds a wrapped list item into one block while keeping an unindented paragraph separate. Two fail: the file still carries the semicolon form, and a continuation line still becomes its own block.

- A runtime test may now name several observation channels (REQ-34). `render_util.signal_lines` gained a list branch: each entry is `{name, needs_egress, secure, insecure}`, and a new `_channel_lines` helper renders the name and an explicit `no egress` or `needs egress` marker above the two signal lines. The dict and bare-string shapes render exactly as before. `references/finding.schema.json` widens `expected_signal` to accept an array. `agents/redteam.md` requires every no-egress channel first, and requires the in-band channel first whenever the sink reply is caller-observable, so a tester behind a network fence still has a runnable oracle. Trade-off: a channel entry is schema-checked only, and a non-dict entry is skipped without a report.

- `tests/test_signal_channels.py` pins a multi-channel `expected_signal` (REQ-34). Six tests assert that a list of observation-channel objects renders each channel by name, marks each one `no egress` or `needs egress`, and carries a secure and an insecure line per channel. Three more tests hold the existing dict, bare-string, and empty shapes. Three of the six fail against `render_util.signal_lines`, which has no list branch.

- The eight Part D elements now render on a finding page (REQ-33). `report.render_finding` emits `attacker`, `privilege`, `exact_request`, and `exfil_channels` after the Compliance line, then `library_version`, `refutation`, `negative_results`, and `baseline` after the Severity Rationale. A new `_optional_sections` helper renders both groups: a list value becomes a bullet list, `exact_request` renders in an `http` fence, and every other value renders inline. An absent key renders nothing. The eight values ride the finding overflow and are declared in `references/finding.schema.json`, because `models.py` is byte-pinned by the D-15 frozen-contract test. `agents/investigate.md` and `agents/validate.md` each gained an evidence-gated block naming the keys the phase may record. Trade-off: the fields are schema-checked, not dataclass-typed.

- Failing tests for REQ-33 in `helpers/tests/test_report_optional_sections.py`. They pin the eight Part D elements a finding page must carry: `attacker`, `privilege`, `exact_request`, `exfil_channels`, `library_version`, `refutation`, `negative_results`, and `baseline`. The fields ride the finding overflow rather than a `Finding` field, because `models.py` is byte-pinned by the D-15 frozen-contract test. Four of the five tests fail against the current `report.render_finding`.

- A terminal artifact-consistency gate (REQ-31). The new `artifact-consistency` phase runs between
  `artifact-review` and `postflight`. It reconciles a finished run's own artifacts against each
  other: report cross-references resolve to files, every triage next-action names a `redteam-plan.md`
  section that holds its finding, the rendered completeness matches `kb/coverage-ledger.json`, the
  self-score does not undercount the report, no `(measured):` header stands above an empty body, and
  a truncated triage title matches its source. The gate halts the run on a contradiction, writes
  `kb/gates/artifact-consistency.json` on every run, degrades to a silent pass when an artifact is
  absent, and turns off through `scan_options.consistency_gate`.
- Failing tests for the terminal artifact-consistency gate (REQ-31). Twelve tests in
  `tests/test_artifact_consistency.py` pin the six terminal checks, the gate's
  `kb/gates/artifact-consistency.json` audit trail, its `scan_options.consistency_gate` opt-out,
  its degrade-to-no-op path on a workspace with no report, and its position between
  `artifact-review` and `postflight`. No `sec_overlay.artifact_consistency` module exists yet, so
  all twelve fail at collection.
- The run-economics section prints only what the run measured (REQ-05). Both token headers
  printed unconditionally, so a run that collected neither published `(measured):` over an empty
  body. `report._render_economics` keeps a measurement group only when it holds rows, appends the
  estimated cost only when `usd_estimate` is present, and returns no lines at all when nothing
  was measured — which drops the `## Run economics` heading with it. REQ-05's other clause is not
  built: five report sections render when empty by D-13, D-14, and D-15 design, so R-41, R-42,
  and R-43's "No X" half stays open. The word-boundary truncation clause already holds through
  `_short_title`.
- A needs-runtime triage row names the `redteam-plan.md` section that holds the finding
  (REQ-03). Every such row carried the same `run redteam-plan test` action, but
  `redteam.discriminate` files the finding into one of three plan sections, so most rows sent the
  reader to a section their finding is not in. `report._ndt_next_actions` calls `discriminate` on
  the needs-runtime list and maps each id to `run redteam-plan directive`, `see redteam-plan
  preconditions`, or `see redteam-plan gaps`. The map has three entries, not four:
  `redteam.wants_runtime` returns True for every `needs-deployment-testing` finding, so the
  `static_settled` bucket is unreachable from this list. Confirmed rows are unchanged.
- The investigate saturation loop is enforced by the driver (REQ-24). `discovery_ledger`
  shipped as a complete library with no production caller, so the loop-until-dry bound was an
  instruction in the operating manual rather than a mechanism.
  `driver._record_discovery_wave` folds one wave per `findings-gate` run — it records every
  current finding's fingerprint into `kb/discovery-ledger.json` before the gate validates, so a
  rejected wave still counts. `driver._investigate_is_saturated` reads the ledger back in the
  dispatch loop; once `terminal_reason` is `saturated` or `capped`, the driver records the
  `investigate` stage and advances instead of printing another dispatch block. A missing or
  unreadable ledger reads as not-saturated. `agents/investigate.md` gains a "Discovery loop"
  section telling the agent it is one wave of a bounded loop, and that a class counts as
  exhausted only when a wave adds nothing new.
- `dependency_sinks.indicator_classes(root)` routes a dependency-sink class on a source
  indicator, not only on a manifest declaration (REQ-25). A Bazel or vendored build declares
  no manifest, so `match_manifests` alone left its whole dependency-sink surface unrouted. The
  matcher reads target source files under the existing vendored-tree skip list and returns the
  sorted classes of every catalog entry with at least one indicator token present.
  `partition.reconcile_plan` unions it with `matched_classes` under the existing `target_root`
  keyword; a planned class is still never removed and never duplicated.
- `route_summary` is a derived field on `ScanProfile` (REQ-11). `driver._act_recall_gate`
  computes it from the route census after recon — `total` census sites, `covered` sites the
  profile mentions, and `uncovered` ids it never mentions — then writes the profile back.
  `validate_profile` rejects a non-object value, so the legacy list of route strings no longer
  validates. `route_control.check_recon_routes` still reads the legacy list form for a
  non-census table and treats any other shape as "nothing summarised", so every table route
  stays a logged gap. `agents/recon.md` no longer instructs recon to emit the field, and
  `references/scan-profile.schema.json` documents it as derived.

### Fixed

- Failing run-economics tests for REQ-05: `test_report.py`'s
  `test_run_economics_omits_a_measured_header_with_no_body` and
  `test_run_economics_section_absent_when_nothing_was_measured` pin that the report prints no
  `(measured):` header above an empty body and no `## Run economics` heading when nothing was
  measured. Both fail because the two token headers print unconditionally.
- Failing next-action tests for REQ-03: `test_report.py`'s
  `test_below_bar_ndt_next_action_points_at_the_gaps_section`,
  `test_unrunnable_ndt_next_action_points_at_the_preconditions_section`, and
  `test_directive_ndt_next_action_points_at_the_directive_section` pin that a needs-runtime
  triage row names the `redteam-plan.md` section that actually contains the finding. All three
  fail with `assert 'run redteam-plan test' == '<expected>'`, because the report hardcodes one
  action for every needs-runtime row.
- Failing saturation-loop tests for REQ-24: `test_driver.py`'s
  `test_findings_gate_records_a_discovery_wave`,
  `test_repeated_findings_gate_runs_reach_a_terminal_reason`, and
  `test_a_saturated_ledger_stops_re_dispatching_investigate` pin that the findings gate folds a
  discovery wave and that a terminal ledger stops another investigate dispatch.
  `test_contracts.py::test_investigate_prompt_carries_wave_language` pins that the prompt names
  the bounded loop it runs inside.
- Failing indicator-routing tests for REQ-25: `test_dependency_sinks.py`'s
  `test_indicator_classes_routes_without_a_manifest` and
  `test_indicator_classes_is_empty_without_an_indicator` pin a new `indicator_classes`
  matcher, and `test_partition.py`'s `test_reconcile_plan_routes_a_class_on_an_indicator_hit`
  pins that an indicator hit routes the entry's class with no manifest present.
- Failing route-summary tests for REQ-11: `test_profile.py`'s
  `test_from_dict_accepts_a_route_summary_key` and
  `test_validate_profile_rejects_a_non_object_route_summary` pin the new field and its shape
  guard, and `test_driver.py`'s `test_recall_gate_derives_route_summary_from_the_census` pins
  that the recall gate writes a derived coverage summary back into the profile.
- `sec_overlay/README.md` carried two paragraphs stating the post-REQ-04 module map: one on
  `coverage.py`'s removal, a second repeating that `coverage_ledger.py` is the single coverage
  source and adding process notes on the docstring fix. Folded into one paragraph that states
  the module map once, keeping the fact only the second paragraph carried: the two docstrings no
  longer name the deleted module, and `test_frozen_contract.py` pins only `models.py` and
  `evidence.py`.
- Two module docstrings still named the deleted `coverage.py` (REQ-04):
  `review_coverage.py`'s docstring called it "shipped" and a "frozen milestone contract" — it
  was never one of the two files `test_frozen_contract.py` pins (`models.py`, `evidence.py`
  only) — and `coverage_ledger.py`'s docstring claimed to complement its per-language
  accounting. Both now describe the code as it stands: `coverage_ledger.py` is the single
  coverage source.
- `kb/coverage-ledger.json` is now the single coverage source (REQ-04): `coverage.py` is
  deleted, `prefilter.py` no longer computes a per-language dataflow percentage or writes
  `kb/coverage.json`, and `report.py` no longer reads that file or renders a second, competing
  "Coverage & limitations" section from it. `kb/coverage.json` was the transcript's last
  surviving backend-provenance trace before REQ-16 made the `prefilter` receipt survive a
  fence abort; the receipt call now drops its `artifacts=` argument along with the file.
- An unknown finding key now survives a load-and-save round trip (REQ-27):
  `workspace.read_findings` stashes any key not in `Finding.__dataclass_fields__` on the
  returned instance, in sorted order, and `workspace.write_findings` merges it back before
  writing. Previously the round trip silently dropped it. `models.py` (`models.py:177` drops
  unknown keys on `from_dict`; the requirement cited `models.py:154`, since moved) is
  untouched — it is a byte-identical mirror of a separate Go port (D-15) with a pinned sha256.
  `findings_gate.py:100` and `bench/run.py:101` still drop unknown keys; both are terminal
  consumers, not round-trippers, so no rewrite loses data there.
- `check_patch_applied` now runs the forward `git apply --check` before the reverse one
  (REQ-01): a patch is `APPLIED` only when it does NOT apply forward AND does apply
  reversed. The prior reverse-first order could call an unapplied additive patch
  `APPLIED` and suppress the deployment caution. `tests/test_patch_status.py`'s two
  order-pinning tests were re-pinned to the new call order.

### Added

- Failing report/prefilter coverage-absence tests for REQ-04: `test_report.py`'s
  `test_report_renders_no_dataflow_percentage_line` pins that a stale `kb/coverage.json` no
  longer prints a "Dataflow coverage" line, and `test_prefilter.py`'s
  `test_run_prefilter_writes_no_coverage_artifact` pins that `run_prefilter` returns no
  `"coverage"` key and writes no `coverage.json`. `test_a_partial_ledger_claims_no_full_coverage`
  already passes — a pre-existing ledger regression guard, not a new red test.
- Failing finding-overflow tests for REQ-27: `tests/test_findings_overflow.py` pins that an
  unknown finding key must survive a `read_findings`/`write_findings` round trip, that known
  fields stay unchanged, and that `read_findings` warns on stderr naming each preserved key.
- Failing patch-order tests for REQ-01: `tests/test_patch_status_real_git.py` drives real
  `git apply --check` against an additive-patch fixture, and `tests/test_patch_status.py`'s
  two order-pinning tests were rewritten to expect a forward-then-reverse call order instead
  of reverse-then-forward.
- Typed the REQ-20 evidence-score test fixture: `test_calibrate_evidence.py`'s `_f` builder
  now builds a base `Finding(...)` and layers overrides with `dataclasses.replace`, instead
  of a `dict()`-splat construction. This clears a ruff `C408` finding and 34 `ty`
  `invalid-argument-type` diagnostics the brief's original fixture carried; it changes no
  assertion — all six REQ-20 tests still pin the same comparisons.
- Evidence strength and reachability move the derived score (REQ-20):
  `calibrate.py` gained `_evidence_adjust`, called from `_derived_score`
  before the precondition cap. A stronger tool-receipt tier, a
  `verified-static` verification, and an assessed-reachable finding each add
  to the score. The adjustment is reward-only, so a finding with none of
  these fields set scores exactly as it did before. REQ-20's other half — the
  `_precondition_weight`/`prompt-constants.md` regeneration — was already
  closed in group 1; this change is the scoring half only.
- Evidence-adjust score tests (REQ-20, RED): `test_calibrate_evidence.py` pins
  that `calibrate_score` ranks a stronger tool receipt above a weaker one,
  `verified-static` above `static-only`, and an assessed-reachable finding
  above an assessed-unreachable one, while an unassessed finding scores the
  same as before the change (reward-only, no penalty).
- The trace prompt widens its scope and names its channels (REQ-06, REQ-19):
  `agents/trace.md` now traces findings with `status` in `{"confirmed",
  "needs-deployment-testing"}`, not `confirmed` alone, so a real-but-unproven
  finding gets a reachability verdict before a human tests it. The procedure
  gained a step that enumerates every source-to-sink path and records an
  in-band channel — a sink reply the caller can observe, such as a response
  body, an error, or a log line — before any out-of-band channel. Both
  requirements edit the same two lines of `agents/trace.md`, so they ship in
  one commit.
- Trace prompt scope and channel tests (REQ-06, REQ-19, RED):
  `test_trace_prompt.py` pins that `agents/trace.md` traces
  `needs-deployment-testing` findings, not only `confirmed` ones, and names an
  in-band channel — a sink reply observable to the caller — before any
  out-of-band channel.
- Verify-config resolver tests (REQ-22, RED): `test_verify_configs.py` pins a
  `resolve_configs(ws, fallback)` helper that reads the semgrep rulesets the
  scan profile planned, falling back to the caller's scalar only when the
  profile is missing, unreadable, or plans no rulesets, and pins that
  `verify_findings` passes the resolved list to the verifier instead of its
  own scalar.
- The verify verdict reads the planned rulesets (REQ-22): `resolve_configs(ws,
  fallback)` reads `profile.sast_plan["semgrep"]["rulesets"]` from the scan
  profile and falls back to the caller's scalar only when the profile is
  missing, unreadable, or plans no rulesets. `verify_findings` resolves this
  list once and passes it to the verifier instead of its own scalar, so a
  finding is re-scanned with the ruleset that actually flagged it.
  `verify_patch`'s `config` parameter now accepts `str | list[str]`, and
  `_check` calls `_file_has_hit` once per config for the semgrep backend,
  OR-combining the tri-state result: `True` if any config flags the file,
  `None` if none flags it and at least one could not run, `False` only when
  every config ran and none flagged the file; codeql/sca ignore the list
  and run once.
- Named verify-cause tests (REQ-21, RED): `test_verify_causes.py` pins that
  `verify_patch` returns one of five named causes instead of overloading
  `"static-only"`, and that `verify_findings` maps each cause to a legal
  verification value and records it in history. `test_verify.py` renames the
  test that pinned the old `"static-only"` overload to expect `"rule-no-match"`.
- The verify verdict names its cause (REQ-21): `verify_patch` now returns one
  of five members of `VERIFY_CAUSES` (`verified-static`, `not-fixed`,
  `patch-not-applied`, `rule-no-match`, `unconfirmed`) instead of overloading
  `"static-only"` from three distinct sites. `verify_findings` maps the cause
  to a legal `Finding.verification` value through `_CAUSE_TO_VERIFICATION`
  and records `{"event": "verify:cause:<cause>"}` in the finding's history.
  An unmapped cause degrades to `static-only` rather than laundering an
  unknown verdict clean.

- Prefilter receipt survives a fence abort (REQ-16, RED): `test_prefilter_receipt.py`
  gains two tests — one failing, pinning that `run_prefilter` writes its receipt
  to disk, and one already passing, pinning that a backend abort leaves the
  `prefilter` stage unrecorded.
- Repo-root-relative candidate paths (REQ-15, RED): `test_prefilter_paths.py`
  gains three failing tests pinning that `run_prefilter` rewrites an absolute
  backend path to a `target`-relative one, leaves an already-relative path
  alone, and leaves a path outside `target` verbatim.
- Attack-class fan-out as JSON (REQ-17, RED): `test_dispatch_classes.py` gains
  four tests pinning that the dispatch block's `{{ATTACK_CLASS}}` value is a
  compact JSON array. Two fail against the pre-fix comma-joined string.
- Every dispatch token is fillable (REQ-08, RED): `test_prompt_tokens.py`
  gains two failing tests. One scans the 11 `PHASE_TABLE` prompts and finds
  three tokens the dispatch map cannot fill: `OVERLAY_ROOT` (11 files),
  `HELPERS_DIR` (5 files), `FP_FEEDBACK` (2 files). The other calls
  `render_dispatch` and fails because `{{FP_FEEDBACK}}` is absent from the
  substitute line.
- A finding's class must be a canonical key (REQ-09, RED): `test_canonical_classes.py`
  gains five tests (one parametrized over 14 keys). All fail to import:
  `clsmap.canonical_classes` does not exist yet.
- A finding's class must be a canonical key (REQ-09): `clsmap.canonical_classes()`
  unions every publisher of an attack-class key — the two tables in
  `attack-classes.md`, `CWE_CLS`/`_RULE_ID_CLS`, `review_findings.GENERAL_DEFECT_CLASSES`,
  every `agents/classes/*.md` stem, and `context.py`'s `manual-review` — into one
  51-key set. `findings_gate.validate_findings` now rejects a finding whose `cls`
  is outside that set. A missing `agents/classes/*.md` file still ships as a
  `class_ext.py` gap, never a rejection: validity and coverage stay separate.

### Changed

- Parity plan tracking: marked Task 22 (REQ-T3c/T3h), Task 23 (REQ-T3d), and
  Task 24 (REQ-T3e) complete in `docs/superpowers/plans/2026-08-23-ocr-parity.md`
  (maintainer doc, not shipped).
- Parity plan tracking: marked all four Task 25 sub-steps complete in
  `docs/superpowers/plans/2026-08-23-ocr-parity.md` (test suite + PARITY-AUDIT.md
  + zero-loss re-read + completion report). Closes the OCR-parity milestone.

### Fixed

- Prefilter receipt survives a fence abort (REQ-16): `run_prefilter` now writes
  its `prefilter` receipt before calling `record_stage`, so the receipt and the
  state transition land in the same order the driver's other phases use. Before
  this, a fence abort in the driver's `on_complete` could leave `state.json`
  saying `prefilter` is done with no receipt on disk.
- Repo-root-relative candidate paths (REQ-15): `run_prefilter` now calls a new
  `_relativize_paths` before `normalize`, rewriting an absolute `Finding.file`
  under `target` to a repo-root-relative one. A path outside `target` stays
  verbatim so a vendored or out-of-tree hit stays visible instead of being
  rewritten into something that does not resolve.
- Attack-class fan-out as JSON (REQ-17): the dispatch block's `{{ATTACK_CLASS}}`
  value is now a compact JSON array, not a comma-joined string. The old format
  clashed with `investigate.md`'s single-key use of the same token.
  `agents/investigate.md` and `agents/README.md` now state the array shape.
- Every dispatch token is fillable (REQ-08): `DISPATCH_TOKENS` grows from four
  names to seven — `OVERLAY_ROOT`, `HELPERS_DIR`, and `FP_FEEDBACK` join
  `TARGET`, `WORKSPACE`, `SHA`, `ATTACK_CLASS`. `render_dispatch` now writes
  the prior-rejection feedback block to `<ws.kb>/fp-feedback.md` (it is a
  multi-line `<untrusted>` envelope, so it cannot ride the space-joined
  `substitute:` line) and substitutes the file path instead. The file is
  always written, even with no prior rejections, so the token always
  resolves. `agents/critic.md` and `agents/investigate.md` each gain one
  sentence telling the agent to read the file. This closes REQ-32's
  deferred property (c): `test_dispatch_tokens_are_a_single_source` in
  `test_contract_lint.py` now calls `render_dispatch` and asserts its
  `substitute:` line's token set against `DISPATCH_TOKENS`, so it fails if
  the two ever disagree again.
- `test_dispatch_classes.py`'s token-count assertion hardcoded `4`, the old
  `DISPATCH_TOKENS` length. Adding three tokens (REQ-08) broke it. It now
  reads `len(DISPATCH_TOKENS)` so a future token count change cannot make it
  drift again.
- Data integrity (REQ-13, folds in REQ-23): every phase receipt and gate
  receipt now records true finding counts. `run.py` counted
  `findings/F-*.json`, but every real finding id starts `C-` or `<CLASS>-`,
  so every receipt recorded zero findings. `workspace.finding_counts(ws)`
  now returns `findings_in` (every finding file) and `findings_out` (the
  `evidence.SHIPPING_STATUSES` subset); `findings` stays equal to
  `findings_in`. `driver._write_gate` and `artifact_gate.run_artifact_gate`
  add the same two keys to their gate JSON, so a gate receipt records counts,
  not only `passed`.
- Contract layer (REQ-32): `test_contract_lint.py`'s lint let four kinds of
  drift pass undetected — a `PRECONDITION_CAPS` threshold, a `PRECONDITION_CAPS`
  cap, a dropped `RUNTIME_TEST_KEYS` key, and a bogus `FINDING_SHAPES` key.
  Two tests now parse the exact published numbers and key sets, instead of
  only checking that a substring is present, and a new test checks that
  `FINDING_SHAPES` names no key or field the model does not declare. Also
  corrected four stale documentation counts the lint's own gaps had let
  drift: the pytest test count (1623 → 1633), `helpers/README.md`'s
  `_MECHANICAL` list (missing `dependency-catalog`), and the
  `prompt-constants.md` block count in two `CLAUDE.md` files (twelve → sixteen,
  naming the four missing blocks).
- `test_rule_glob.py`'s `fake_run_review` spy accepts the `commit`,
  `workspace_dirty`, `plan`, `token_budget`, `background`, and `tier` keyword
  arguments the real `run_review` now takes; the stale stub raised
  `TypeError` in the full suite after the `--commit`/`--workspace-dirty` review
  scopes landed. Test-only; no runtime change.

### Added

- Data integrity (REQ-13, folds in REQ-23, Task 1 RED): `test_receipt_counts.py`
  gains three failing tests for a phase receipt's finding counts. They fail to
  import: `workspace.finding_counts` does not exist yet.
- Contract layer (REQ-32, Task 5 GREEN): `calibrate.py` exports
  `PRECONDITION_CAPS` and `PRECONDITION_CAP_FLOOR`; `_precondition_cap` now
  reads the ceiling from that table instead of four hardcoded branches.
  `prompt-constants.md`'s `SEVERITY_PRECONDITION` block states the same
  weight-based cap table. `driver.py` exports `DISPATCH_TOKENS`, and
  `render_dispatch` builds its `substitute:` line from that tuple instead of
  a hand-written string, so the class token now sits on the same line as the
  other three. This closes REQ-32 property (b); property (c) is REQ-08's work.
- Contract layer (REQ-32, Task 5 RED): `test_contract_lint.py` gains three
  failing tests for the last open lint property. They check that
  `prompt-constants.md` states the precondition cap table by weight, that
  `_precondition_cap` reads that table from a single constant, and that
  `driver.py` exposes a `DISPATCH_TOKENS` tuple naming `TARGET`, `WORKSPACE`,
  `SHA`, and `ATTACK_CLASS`. All three fail to import: none of
  `PRECONDITION_CAPS`, `PRECONDITION_CAP_FLOOR`, or `DISPATCH_TOKENS` exist yet.
- Contract layer (REQ-10, Task 4 GREEN): `agents/threat-model.md`'s `## Imports`
  section now names `QUALIFIER_PROOF`. The prompt grades severity, so a blanket
  mitigation claim must name the reachable paths checked, not just assert
  safety.
- Contract layer (REQ-10, Task 4 RED): `test_contract_lint.py` gains a failing
  test. It checks `agents/threat-model.md`'s `## Imports` section names
  `QUALIFIER_PROOF`. The prompt grades severity, so it needs the rule, but the
  section today names only `FIELD_OWNERSHIP`, `OUTPUT_WRITE_FALLBACK`, and
  `STE_PROSE`.
- Contract layer (REQ-07, Task 3 GREEN): `agents/validate.md`'s `**Confirmed**`
  verdict now names the Tier-1 receipts (`codeql:`, `semgrep:`, `sca:`,
  `secrets:`) and requires at least one of them. A finding whose only receipts
  are Tier-2 (`ast-grep:`, `structural-index:`, `ripgrep:`, `tree-sitter:`,
  `dependency-catalog:`) routes to `needs-deployment-testing`, not `confirmed`,
  matching `findings_gate.py`'s `confirms_alone` gate. An `llm-claimed:` entry
  is stated to corroborate and never confirm.
- Contract layer (REQ-07, Task 3 RED): `test_contract_lint.py` gains two failing
  tests. One checks `agents/validate.md` names every `evidence.TIER1_RECEIPTS`
  value and the word `Tier-1`. The other checks the prompt's `**Confirmed**`
  verdict section names `Tier-1`, so a Tier-2 receipt never reads as sufficient.
  Both fail: the prompt today tells the agent to record `ast-grep:`/
  `structural-index:`/`ripgrep:` receipts for `confirmed`, all Tier-2, with no
  `Tier-1` string anywhere in the file.
- Contract layer (REQ-02, Task 1 RED): failing tests pin the closed enums for
  `Finding.verification` and `Finding.runtime_disposition`. `test_models.py`
  gains four cases: a prose `verification` value and an unknown
  `runtime_disposition` must raise `ValueError`; a documented value or `null`
  must load. `test_contract_lint.py` (new) asserts `finding.schema.json`'s
  enums match `sec_overlay.evidence`'s constants; it fails to import until
  `VERIFICATION_VALUES` exists.
- Contract layer (REQ-02, Task 1 GREEN): `evidence.VERIFICATION_VALUES` closes
  the `verification` enum to five values — `verified-static`, `static-only`,
  `not-fixed`, `verify-error`, `fact-checked`; `finding.schema.json`'s `verification` and
  `runtime_disposition` enums mirror `evidence.py`'s constants; `Finding.from_dict`
  raises `ValueError` when either field holds a value outside its closed set
  and is not `null`. `fact-checked` is in the enum because `factcheck.py`'s
  F8 stage writes it to real findings; the set is the union of every value
  shipped code writes, not the verify-stage vocabulary alone. The two
  `test_frozen_contract.py` byte-identity pins moved to the new digests in
  this commit — no Go port is reachable from this repository to sync by hand.
- Contract layer (REQ-18, Task 2 GREEN): `models.py` gains `RUNTIME_TEST_KEYS`,
  `OPEN_QUESTION_KEYS`, and `AFFECTED_SITE_KEYS`, naming the exact keys of the
  `runtime_test`, `open_questions`, and `affected_sites` nested `Finding` fields.
  `prompt-constants.md` publishes them in a new `FINDING_SHAPES` block, and
  `agents/investigate.md` imports it alongside `FIELD_OWNERSHIP`. The
  `test_frozen_contract.py` `_MODELS_SHA256` pin moved to the new digest in this
  commit, since `models.py` gained the three constants.
- Contract layer (REQ-18, Task 2 RED): `test_contract_lint.py` gains two failing
  tests. One checks the `FINDING_SHAPES` block in `prompt-constants.md` names
  every key of `models.RUNTIME_TEST_KEYS`, `OPEN_QUESTION_KEYS`, and
  `AFFECTED_SITE_KEYS`. The other checks `agents/investigate.md` references
  `FINDING_SHAPES`. Both fail to import until the three key tuples exist.
- Parity audit (Task 25): `docs/parity/PARITY-AUDIT.md` walks `EXTRACTION.md`
  row by row and gives every item (M/P/S/T3/R/W/G/D/X/V/HR — 87 rows) a final
  disposition with `file:line` evidence, `rejected:<reason>`, or
  `deferred:<reason + where>`. Zero-loss verified: the audit's id set covers
  every EXTRACTION id. Honors SPEC dispositions G18/G19/G20 (rejected) and
  G21/T3g (deferred). Maintainer doc.
- Security slice (REQ-T3e, Task 24 GREEN): `bench/aacr_adapter.py` tags an AACR
  row whose `category` signals security (`security` / `vulnerab`) as
  `source="aacr-security"`, and `bench/corpus.py` registers that source. `tally`
  emits the distinct `aacr-security` `by_source` slice automatically, kept out of
  the real-confirmed headline. Non-security rows stay `source="aacr"`. The
  predicate is dataset-agnostic, honoring M3d's unverified-distribution caveat.
- Security slice (REQ-T3e, Task 24 RED): RED tests in `tests/test_aacr_adapter.py`
  pin that `aacr_entries` tags a security-category row as `source="aacr-security"`
  (a distinct slice `tally` emits in `by_source`, kept out of the real-confirmed
  headline).
- Coverage honesty (REQ-T3d, Task 23 GREEN): `bench/tally.py` gains a
  `coverage_ledgers` argument and a `coverage_honesty` scorecard block —
  `rate` = honest runs / total runs, where a run is unsupported when its ledger
  claimed `completeness == "complete"` while a surface needed follow-up or
  `deferred` / `open_questions` were non-empty — surfaced in `to_dict` and as a
  "Coverage honesty" markdown section. `bench/run.py` reads each workspace's
  `kb/coverage-ledger.json` and passes the map to `tally`. The block is absent
  when no ledgers are supplied.
- Coverage honesty (REQ-T3d, Task 23 RED): RED tests in `tests/test_bench.py`
  pin that `tally(..., coverage_ledgers=...)` reports a `coverage_honesty` block
  (`runs`, `unsupported`, `rate`) flagging any run whose ledger claimed
  `completeness == "complete"` while surfaces need follow-up or `deferred` /
  `open_questions` were non-empty, plus a "Coverage honesty" markdown section;
  omitted when no ledgers are supplied.
- Verified-fix rate (REQ-T3c/T3h, Task 22 GREEN): `bench/tally.py` gains a
  `findings_by_id` argument and a `verified_fix` scorecard block —
  `rate` = (`FindingStatus.FIXED` ∪ `verification == "verified-static"`) over the
  confirmed real true-positives — surfaced in `to_dict` and as a headline
  markdown row. `bench/run.py` builds the id→finding map from `findings_by_repo`
  and passes it to `tally`. The block is absent when no fix data is supplied.
- Verified-fix rate (REQ-T3c/T3h, Task 22 RED): RED tests in
  `tests/test_bench.py` pin that `tally(..., findings_by_id=...)` reports a
  `verified_fix_rate` = (`fixed` ∪ `verified-static`) / confirmed true-positives,
  exposes a `verified_fix` block in the scorecard dict and a headline markdown
  row, and leaves the rate `None` when no fix data is supplied.
- Fast/assured tiers (REQ-T3a, Task 21 GREEN): `run_review` gains a `tier`
  argument (`--tier fast|assured`, default `assured`). The `fast` tier skips the
  plan half — a `--prepare --plan` run returns without writing
  `plan_manifest.json` — while `assured` runs the full chain. The tier is
  recorded in `review_result.json` and its `CoverageManifest`
  (`review_coverage.py` threads `tier` through `__init__`/`to_dict`/`from_dict`).
- Fast/assured tiers (REQ-T3a, Task 21 RED): RED tests in
  `tests/test_review_live.py` pin that `run_review(..., tier="fast")` records the
  tier in `review_result.json` and its coverage manifest, and that a fast-tier
  `--prepare --plan` run skips the plan half (no `plan_manifest.json`) while the
  assured default still emits it over the plan-line threshold.

### Fixed

- Judge severity write-back (REQ-P9): `calibrate.py` now lowers `f.severity`
  to the downgraded score band (tests first in `tests/test_calibrate.py`), so
  reports no longer show the inflated severity a judge already rejected.

### Added

- Rules check + did-you-mean (REQ-S4): `rule_glob.resolve_with_layer` returns
  the matched layer label plus the rule-doc text (falling through to `builtin`),
  a `rules check <path> --root` CLI subcommand prints both, and a
  `_SuggestingParser` appends a `difflib` "Did you mean" line naming the nearest
  valid subcommand for a misspelling. Tests in `tests/test_rules_check.py`.
- Sessions list/show (REQ-S2, Task 19 GREEN): new read-only
  `sec_overlay/sessions.py` renders the sidecar `state.json` plus review
  ledgers — `session_rows`/`render_rows` produce one row per slug (pass, sha,
  finding counts), `resolve_session` resolves `latest` by mtime or a slug, and
  `session_detail`/`render_detail` show stages, a ledger summary, and a
  `--severity`-filtered finding list (X3 scope). Wired as the `sessions
  list|show` CLI subcommand over `repo_memory.memory_root`.
- Sessions list/show (REQ-S2, Task 19 RED): RED tests in `tests/test_sessions.py`
  pin the read-only renderer contract over sidecar `state.json` and review
  ledgers — one row per sidecar slug (pass, sha, finding counts), `latest`
  resolution by mtime, a detail view with stages plus a ledger summary, and a
  `--severity` finding filter (X3 scope).
- GitHub PR review poster (REQ-S1, Task 18 GREEN): new
  `sec_overlay/pr_poster.py`, a stdlib-only (`urllib`) poster — `route_findings`
  splits critical/high (inline comments) from the rest (summary body),
  `build_review_payload` builds a `COMMENT` review, and `post_review` POSTs it to
  the pulls reviews endpoint with bearer auth (injectable transport for tests).
  A composite `action.yml` at the plugin root runs review mode, uploads the
  SARIF to code scanning, and invokes the poster.
- GitHub PR review poster (REQ-S1, Task 18 RED): RED tests in
  `tests/test_pr_poster.py` pin the poster contract — severity routing
  (critical/high inline, medium/low/info summary), a `COMMENT` review payload,
  and a `post_review` call to the pulls reviews endpoint with bearer auth.
- Assurance case (REQ-S3): `skills/sec-overlay/ASSURANCE_CASE.md` documents the
  actors, trust boundaries, threats, and countermeasures behind the harness
  invariants, with each countermeasure cited to a resolving `file:line`. RED
  tests in `tests/test_docs_invariants.py` pin the contract — required sections,
  every citation resolving to an existing line, and STE structural lint clean.
- Background-context ingestion (REQ-P8, Task 16 GREEN): new
  `sec_overlay/background.py` with `load_background`, sanitizing
  developer-supplied context in order — a 1 MB `BACKGROUND_MAX_BYTES` cap
  raising `ValueError`, control-character strip (newline and tab kept),
  envelope-delimiter neutralization, a hard `verify_no_secrets` abort on any
  detected secret (run before `safe_for_prompt` so a maskable token still
  aborts), then `redactor.safe_for_prompt`. `review_agent.render_review_prompt`
  gains a `background` kwarg wrapping the text in a `background-context`
  untrusted envelope; `agents/review-file.md` renders `{{BACKGROUND}}`; the
  `review` CLI gains mutually-exclusive `--background`/`--background-file`
  flags that exit 2 on an oversized or secret-bearing payload.
- Background-context ingestion (REQ-P8, Task 16 RED): RED tests in
  `tests/test_background.py` pin the `load_background` contract — a 1 MB cap
  raising `ValueError`, control-character strip, envelope-delimiter guard, a
  hard `SecretsPresent` abort on any detected secret, and file/text sourcing.
- Consolidated review result artifact (REQ-P7, Task 15 GREEN): new
  `sec_overlay/review_result.py` with `write_review_result`, writing
  `artifacts/review_result.json` via `workspace._atomic_write`. It records
  `status` (the coverage-manifest seal), per-finding records, dropped/declined
  findings, reflection retractions/skips, `budget_exceeded`, the coverage
  manifest, per-phase `tokens`, base/head SHAs, and model/profile/tier.
  `cli.run_review` calls it last on both consume exits (zero-reviewable and
  post-seal). Additive — every prior artifact stays.

- Consolidated review result artifact (REQ-P7, Task 15): failing tests first
  (RED) in `tests/test_review_result.py`. They pin `write_review_result` writing
  `review_result.json` to `ws.artifacts` with the full documented key set on both
  a zero-finding run and a populated run: `status`, per-finding records (`id`,
  `path`, `line`, `severity`, `rule_id`, `profile`, `disposition`), `dropped`,
  `declined`, `retractions`, `skips`, `budget_exceeded`, `coverage_manifest`,
  `tokens`, `base`, `head`, `model`, `profile`, `tier`.

- Per-file plan phase implementation (REQ-P3, Task 14 GREEN): `review_agent.py`
  gains `render_plan_prompt`, `plan_agent_label`, `plan_guidance_from_return`,
  and `PLAN_LINE_THRESHOLD = 100`; `render_review_prompt` gains a keyword-only
  `plan_guidance` filling the new `{{PLAN_GUIDANCE}}` token. New agent prompt
  `agents/review-plan.md`. `cli.run_review` gains `--plan`: `--plan --prepare`
  writes plan prompts for over-threshold units and returns early; a following
  `--prepare` injects each recorded plan return's guidance and fails open
  (missing or invalid return yields empty guidance and a `plan_skips.json`
  entry). Plan guidance is advisory — never a receipt, never a finding.
  Review-mode only, so `bench.run` is unchanged.

- Per-file plan phase (REQ-P3, Task 14): failing tests first (RED) for the
  review prepare plan step. `test_review_agent.py` pins `render_review_prompt`
  injecting a `{{PLAN_GUIDANCE}}` body (empty by default), `render_plan_prompt`
  substituting the plan template tokens, and `plan_guidance_from_return`
  ordering issues by severity and raising on invalid JSON, an unknown severity,
  a missing `issues` key, or an issue without guidance. `test_review_live.py`
  pins `--prepare --plan` writing a plan prompt only for a unit at or over
  `PLAN_LINE_THRESHOLD`, a recorded plan return injecting its guidance into the
  review prompt, and an invalid plan return failing open (review prompt renders
  without guidance, `plan_skips.json` records the skip). Review-mode only, so
  `bench.run` is unchanged.

- Commit and workspace-dirty review scopes (REQ-P5, Task 13): failing tests
  first (RED in 1.96.1) for `diffscope.dirty_file_records` (a real-repo check
  that it lists staged, unstaged, and untracked working-tree changes) and three
  CLI tests — `--commit <sha>` scoping the review to `sha^..sha`, `--commit`
  with `--base` exiting 2, and `--workspace-dirty` listing uncommitted changes.
  `sec-overlay review` now takes `--commit` and `--workspace-dirty` beside
  `--base` (exactly one required; a resumed run reads its scope from the sealed
  manifest); `dirty_file_records` parses `git status --porcelain`,
  `file_diff_line_count`/`binary_paths`/`file_diff_text` accept `head=None` to
  diff against the working tree, and `validate_ref` permits `^` so `sha^`
  resolves. Tests now pass. Review-mode only, so `bench.run` is unchanged.

- Hard token budget (REQ-P4, Task 12): `review_budget.estimate_review_cost`
  projects OCR's plan-loop cost per file (prompt 2000, plan-out 400, 7 rounds,
  round-out 700; empty diff 21300) while `estimate_tokens` stays the raw
  `len // 4` primitive, and a latching `BudgetGate` admits files until the first
  projected breach then refuses the rest. `cli.run_review` gains a
  `--token-budget` flag (default 0 = unlimited): a file over the
  `FILE_BUDGET_FRACTION` (0.8) cap is excluded as `too-large-tokens` before
  review, a file refused by the gate seals `partial` with a `skipped(budget)`
  note at exit 0, `--prepare` surfaces a per-file `token_estimate`, and the
  coverage manifest records `budget_exceeded`. Tests (RED in 1.95.1) now pass.
  This closes the Task-10 deferral: single-file units stay without non-mate
  sibling diffs, now bounded by this budget rather than pending it.

- Rule-doc port (REQ-P2): `BUILTIN_PATH_RULE_MAP` now holds OCR's full
  35-pattern `system_rules.json` set plus the trailing `**/*` catch-all (36
  distinct docs, exact OCR order), and 27 new docs are ported under
  `rules/rule_docs/` — manifests (`pom.xml`, `package.json`, `Cargo.toml`,
  `composer.json`, `build.gradle`), config (`.properties`, `.json`, `.yaml`,
  `.github/**`), templates (FreeMarker, Astro, MyBatis mapper/DAO XML), and the
  remaining languages (C, C++, Protobuf, GraphQL, Prisma, Terraform, Bicep,
  Nix, Haskell, Julia, Nim, ArkTS, gettext `.po`/`.pot`). Each ported doc is
  adapted from OCR's Apache-2.0 sources, carries the
  `Adapted from open-code-review (Apache-2.0)` attribution line, and covers the
  same five defect families in the fixed section order. Tests in
  `tests/test_rule_glob.py` and `tests/test_rule_docs.py` (RED in 1.94.1) now
  pass: representative paths resolve to the right doc including first-match
  order cases (`.github` patterns before plain YAML;
  `package.json`/`Cargo.toml`/`pom.xml` before generic `json`/`xml`).

- Sibling-context review (REQ-P1): the review-file prompt now embeds a file's
  bundle-mate diffs. New module `review_budget.py` holds the shared size
  primitive `estimate_tokens(text) = len(text) // 4`.
  `render_review_prompt(sibling_diffs=..., cap_tokens=...)` renders the new
  `{{SIBLING_DIFFS}}` token largest-first as fenced diffs, replaces any sibling
  over `cap_tokens` (default 2000) with an `omitted (token cap)` marker, and
  annotates each embedded sibling `(diff included below)` in `{{CHANGE_FILES}}`.
  `bundle.group_bundles` gains C/C++ header-impl (`.h/.c`, `.hpp/.cpp`) and
  interface/impl stem (`svc.ts`/`svc.impl.ts`) pairing plus a keyword-only
  `diffs`/`max_unit_tokens` (`MAX_UNIT_TOKENS = 50000`) first-fit split;
  `diffs=None` leaves existing callers unchanged. `cli.run_review`'s prepare
  path passes each file its unit-mates' diffs. Deferred: single-file units
  receive non-mate sibling diffs only under REQ-P4's budget (Task 12); and
  `import_adjacency(graph_json)` grouping (SPEC-optional; review mode must not
  require `kb/graph.json`).

- Live-reflection wiring (REQ-P6): `run_review` now consumes recorded
  review-filter verdicts through `reflection.recorded_verdict_source` instead
  of an always-empty verdict. `reflection_label(path)` names each file's
  recorded return; the source reads a `{"base", "head", "verdict"}` envelope
  and raises `ValueError` on a missing, stale (base/head mismatch), malformed,
  or non-mapping verdict, which the reflection loop catches per file as a
  `ReflectionSkip` (fail-open, never a silent keep-all). A new
  `--prepare-reflection` mode renders one `review-filter` prompt per file with
  kept findings under `runs/reflection_prompts/` and lists them in
  `runs/reflection_plan.json`. Files with zero kept findings skip the verdict
  lookup entirely.

- Live-reflection wiring tests (REQ-P6, RED): failing tests in
  `tests/test_reflection.py` and `tests/test_review_live.py` pin the coming
  recorded-verdict source — `reflection_label(path)`,
  `recorded_verdict_source(ws, *, base, head)`, end-to-end retraction/refusal
  through `run_review`, missing-verdict `ReflectionSkip` (never a silent
  keep-all), and a `--prepare-reflection` prompt-render mode.

- Protocol + reproducibility docs (REQ-R3 + REQ-R1/R4): the scorecard markdown now
  emits a "Scope confound" statement, and `bench/README.md` documents the annotation
  protocol (single-maintainer adjudication, judge-disagreement handling), a
  one-command reproduce, and the scope confound. Tests first in `tests/test_bench.py`
  and `tests/test_docs_invariants.py`.

- Cost/latency columns (REQ-M6): `bench/tally.py` `tally(..., cost=...)` attaches a
  `cost` block (`tokens`, `wall_time_s`, `usd_per_confirmed_tp` = USD estimate /
  real-confirmed TP, `None` when no TP) and `to_markdown` renders a "Cost & latency
  (estimates)" section; per-class FP-rate rows publish in the "By class" table.
  `bench/run.py` captures wall-time and sums per-repo token totals from every
  `workspaces/*/state.json` budget (via `sec_overlay.cost`). Tests first in
  `tests/test_bench.py`.

- Cross-run variance (REQ-M5): `bench/tally.py` `aggregate_scorecards(cards)`
  reports mean/min/max per metric (precision, recall, f1, fp_rate) across repeated
  runs (skipping `None` metrics), and `bench/run.py` gains `--repeats N` — it runs
  the benchmark N times into `run-<n>/` and writes an aggregate
  `scorecard_agg.{json,md}` via `run_repeated`. Tests first in `tests/test_bench.py`.

- External-dataset adapters (REQ-M3): `bench/aacr_adapter.py` `aacr_entries` maps
  AACR review-dataset rows to `source="aacr"` corpus entries (registered in
  `bench/corpus.py` `SOURCES`; excluded from the real-confirmed headline), and
  `bench/ocr_ingest.py` `ocr_findings` parses `ocr review --format json` into
  benchmark-only CONFIRMED findings tagged `llm-claimed:ocr` — never harness
  findings, never receipt-backed. `Scorecard.to_markdown` now appends a
  same-judge caveat block so a cross-tool comparison discloses that both tools
  share one judge. `bench/README.md` records the live AACR schema (2026-08-23)
  with its unverified-distribution caveat. Tests first in
  `tests/test_aacr_adapter.py`.

- Committed seed corpus (REQ-M4): `bench/corpus_seed/` now ships 30 public
  entries — 8 `dogfood.json` (2 `locked` at `fixtures/vulnerable_repo`), 3
  `absence.json`, 4 `negatives.json`, 5 `dep_cves.json`, 10 Juice Shop
  `public_apps.json` — plus the `fixtures/dep_cve_repo` lockfile. Replaces the
  prior local-only, gitignored corpus.

- Detection-grading path (REQ-M4): `bench/adapter.py` `tier1_detected` reads
  any-status findings backed by a Tier-1 receipt, and `bench.run`
  `--grade-mode detection` / `--only-local` grade whether a deterministic scan
  located each locked ground-truth finding. The confirmation gate
  (`reportable`) is untouched — a deterministic-only scan never CONFIRMS. Tests
  first in `tests/test_bench.py`.

- Tests first (REQ-M4): `tests/test_bench.py::test_seed_corpus_has_min_entries`
  locks the seed corpus floor — at least 30 entries with at least 3 `dep-cve`,
  5 `public-app`, 1 negative, and 1 locked entry, all valid.

- Headless skill driver (REQ-M2): `bench/driver.py` + a runnable
  `CCSkillAdapter` — unattended benchmark runs over the corpus.

- Tests first (REQ-M2): `tests/test_bench_driver.py` locks the headless
  driver contract for `CCSkillAdapter`.

- F1 in the bench scorecard (`bench/tally.py`): overall, per-source, and
  headline rows; `None` when undefined (REQ-M1; tests first in
  `tests/test_bench.py`).

- OCR-parity workstream docs: `docs/parity/EXTRACTION.md` (inventory of the
  OCR-vs-sec-overlay analysis, 3 extraction passes), `docs/parity/SPEC.md`
  (requirements + traceability matrix + dispositions), and
  `docs/superpowers/plans/2026-08-23-ocr-parity.md` (implementation plan).

- Recall adversary (`agents/recall-adversary.md`, opus): judges what the recon
  phase left out, using `sec_overlay.phase_gate.recall_claims`,
  `kb/route-census.json`, and dependency-catalog matches.

- Deterministic `recall-gate` phase, wired right after recon: recomputes the
  same census and catalog checks and writes each gap into
  `kb/coverage-ledger.json` through `route_control.record_route_gaps`,
  demoting `completeness` to `partial`.

- Tracked absence rule pack (`helpers/rules/absence/`): first-party semgrep
  rules that flag a dangerous construction only when its safe option is
  absent, for OPA `rego.New`, `cel.NewEnv`, `lua.NewState`, Jinja2
  `Environment`, and `requests` calls without a timeout.

- Recon always adds `rules/absence` to `sast_plan.semgrep.rulesets`, for
  every language, alongside the vendored per-language dirs. `SKILL.md` notes
  the pack; `golden_scan_profile.json` and two `test_contracts.py` guards
  pin the invariant.

- Dependency-sink catalog (`references/dependency-sinks.json`) and its loader,
  naming dependencies whose own code holds the sink.
- `match_manifests()`/`matched_classes()` and a `match --root <dir>` CLI
  subcommand, to check a target repo's manifests against the catalog.
- `reconcile_plan()` takes an optional `target_root` and merges every attack
  class of a matched dependency-sink catalog entry into the agent plan.
- `attack-classes.md`'s `expr-eval-rce` and `ssrf` rows name every server-side
  policy and script engine sink from `dependency-sinks.json`. Recon can select
  the right class for a catalogued dependency with no first-party indicator.
- `agents/classes/expr-eval-rce.md` and `agents/classes/ssti.md`, the two
  class-extension prompts every `dependency-sinks.json` catalog entry now
  routes to. Two `test_docs_invariants.py` guards check that every catalogued
  `cls` has a matching class file and that `expr-eval-rce.md` carries all
  five required sections.
- A `DETECTION_COVERAGE.md` row naming the dependency-internal sink limit: no
  backend reads a dependency's own source, so the catalog routes the class
  but never proves the sink. `recon.md` now reads `dependency-sinks.json` and
  emits `dependency_sinks`; `SKILL.md` documents `reconcile_plan`'s catalog
  merge.
- A test pins `references/DETECTION_COVERAGE.md` to `detection_coverage.py`'s
  renderer, byte for byte. An edit to the renderer with no matching
  regeneration of the tracked file now fails the suite.
- `astgrep.py` gains `build_rule()`/`run_astgrep_rule()`, plus a `run --not
  <pattern>` flag and a `rule --file <path>` subcommand, so the investigate
  agent can run a structural absence check ad hoc. Go needs a hand-written
  rule (`fixtures/absence_repo/rego-absence.yaml`): a bare selector-call
  pattern such as `rego.New($ARGS)` matches nothing there.
- `dependency-catalog` receipt: a Tier-2 evidence source for a finding whose
  sink lives inside a declared dependency's own code. It locates the sink
  named by a `dependency-sinks.json` catalog entry; it never confirms a
  finding alone. `EVIDENCE_VOCABULARY` documents the new receipt form.
- The SSRF class prompt's proof tuple now admits a `dependency-catalog:<id>`
  receipt for element 1 and a `semgrep:sec-overlay.absence.*` receipt for
  element 2. `investigate.md`'s tool-grounding rule names
  `dependency-catalog` as a Tier-2 receipt that never confirms a gate alone.
- `emit_semgrep_rule()` takes a `safe_option` keyword. With it, the codified
  rule is an absence rule: it fires only on a construction missing the named
  safe option. Its id then sits under `sec-overlay.absence.`.
  `corpus_seed/absence.json` pins the rego.Capabilities and jinja2-sandbox
  pair as locked bench positives, plus a negative that must stay silent.
- `route_census.py` and `references/route-frameworks.json`: a route
  inventory derived from source via ripgrep, for Flask, FastAPI, Django
  urls, Go net/http, Go chi/gin/echo, Express, and Spring. Reads code
  instead of recon's own output, so an omitted route can appear as a gap.
- `write_census`/`load_census` persist the census to `kb/route-census.json`.
  `build_route_control_table` now prefers the census over
  `kb/scan-profile.json`, stamping `source`, and `check_census_routes`
  flags a code-registered route the recon profile never names. This closes
  the circularity where the route-to-control check compared recon against
  its own output.
- `build_coverage_ledger` now keys a covered class's surfaces by sink site,
  not by class, so a second sink in the same class no longer inherits
  "covered" from an unrelated confirmed finding.
- A `route-census` deterministic phase, wired into `PHASE_TABLE` ahead of
  `recon`. `_act_route_census` writes `kb/route-census.json` from the
  target's source, so the file exists for the recon gate, `check_census_routes`,
  and the recall adversary before recon ever runs.
- `route_control.check_catalog_classes` flags a dependency-catalog class the
  recon profile's `attack_surface` never named. A dependency such as OPA
  hides its sink inside its own Rego policy, so recon can miss the class
  with no first-party signal.

### Fixed

- `fixtures/dep_sink_repo/go.mod` declares OPA `v1.19.1` instead of `v0.68.0`.

  The old version carries GHSA-6m8w-jc87-6cr7, so the repository dependency
  review gate failed on inert fixture data. The catalog matches on the module
  path alone, so the version choice does not affect any test.

- `go-lua-state-missing-skipopenlibs` no longer fires on a hardened call site.

  gopher-lua takes `Options` by value. The pointer-literal `pattern-not` never
  matched `lua.NewState(lua.Options{SkipOpenLibs: true})`. The negation now
  uses the value form, quoted so the YAML stays valid.

- The three untested absence rules gained a fixture pair and a test each.

  The three are `go-cel-env-missing-declarations`,
  `go-lua-state-missing-skipopenlibs`, and `python-requests-missing-timeout`.
  Each test asserts the vulnerable site by `(file, rule, line)`. Each also
  asserts the hardened site's silence.

- `recall_claims` cites the manifest that declares the package.

  The ref comes from the new `dependency_sinks.manifest_paths()`. The old ref
  `references/dependency-sinks.json` resolves only inside the overlay. The
  recall adversary's drop rule therefore discarded every catalog claim.

- `plugins/sec-overlay/CLAUDE.md`'s CLI-callable module list names
  `dependency_sinks`.

- `agents/README.md`'s recall-adversary row no longer claims that an
  `OMISSION` row reaches the coverage ledger.

  The deterministic `recall-gate` phase records the gaps its own checks
  compute. An adversary-only omission stays manual follow-up work. `SKILL.md`
  already stated that.

- `test_absence_rules.py`'s metadata guard now checks that each rule's own
  block carries a `cls:` line after its `metadata:` line, instead of a raw
  file-wide `cls:` count that a rule with no `metadata.cls` could still pass.
- `run_astgrep_rule()`'s docstring now names only the non-JSON/empty-output
  case its code actually catches, instead of overclaiming coverage of a
  missing `ast-grep` binary, which still raises `FileNotFoundError`.
- `findings_gate.validate_findings` now rejects a `dependency-catalog:<id>`
  receipt whose `<id>` is not a real `dependency-sinks.json` catalog entry.
  Free text after the colon read as a receipt before this check.
- `corpus_seed/absence.json` now sets `repo_url` and `commit` to the empty
  string on each entry. `CorpusEntry` declares both as required fields, so
  `load_corpus` raised `TypeError` and every bench run failed to start.
- `bench/README.md` now states that the documented `bench.run` command exits 1
  when no scanned workspace is supplied. A locked positive counts as regressed,
  so an operator must not gate CI on that exit status.
- The two module-map entries for `route_census.census()` no longer claim an
  empty return on any ripgrep failure. A missing ripgrep binary raises
  `FileNotFoundError`, because preflight owns binary availability.
- `check_recon_routes` now returns no gaps for a census-sourced table. A
  census route carries a method prefix `route_summary` can never contain,
  so it turned every census route into a permanent `needs_follow_up` gap.
  `check_census_routes` already owns that comparison for a census table.
- `sec_overlay/README.md` no longer implies `check_census_routes` still
  flags a route that appears only as a prefix inside a longer profile path.
  A profile field carrying the route path as a prefix suppresses the gap.
- `rethreshold._ledger_disposition` now matches a coverage surface by its
  `cls` field, falling back to bare `id`. Site-keyed surfaces no longer
  break the cross-repo demote and promote paths. The per-site
  `needs_follow_up` surface's `reason`/`next_step` now name the specific
  sink site instead of reusing class-level wording. A new test also pins
  `cls`/`site` on a per-site surface.
- The CLAUDE.md phase-order row for `route-census` now names the deterministic phase the driver dispatches, instead of a CLI invocation that never called `write_census`.
- `preflight.py`'s `TOOLS` list now includes `rg` as a required entry, so a missing ripgrep binary fails preflight instead of the `route-census` phase.
- A test now pins `check_catalog_classes`'s dedupe branch: two catalog entries
  sharing one class produce exactly one gap, not one per entry. A mutation
  test found the branch untested before this guard.
- `SKILL.md` and `CHANGELOG.md` claimed an `OMISSION` row always routes
  through `route_control.record_route_gaps`. No code path called it. A new
  `recall-gate` deterministic phase now runs right after recon and writes
  the ledger, and the docs describe that real path.
- A new test uses `dependency_sinks.load_catalog()`'s real OPA entry to cover
  `check_catalog_classes` inside `recall_claims`. Deleting that loop left the
  suite green before this test existed.
- `sec_overlay/README.md` no longer claims `route_control` imports from
  `phase_gate`. `phase_gate.py`'s three `route_control`/`route_census`/
  `dependency_sinks` imports moved to module level. No cycle exists.
- `CLAUDE.md`'s phase-order block now lists `recall-gate` right after `recon`.
  `_PHASE_DOC_LABELS` gained a matching entry, so the phase-order test now
  enforces the row's position.
- `SKILL.md`'s recall-gate paragraph no longer claims every omission reaches
  the ledger. A deterministic omission still cannot be lost. An
  adversary-only omission needs a reviewer to record it by hand.

## 1.69.15 - 2026-08-22

### Fixed

- `skills/sec-overlay/CLAUDE.md`: the "Phase order (one pass)" list carries a
  numbered `14.2 Selfscore` entry between Report and Red Team, matching
  `PHASE_TABLE`; `test_docs_invariants.py` now enforces the label (DOC-03).
- `skills/sec-overlay/helpers/README.md`: the pipeline diagram carries the
  `selfscore`, `artifact-gate`, and `artifact-review` nodes in `PHASE_TABLE`
  order between report and postflight (DOC-02).
- `skills/sec-overlay/README.md`: CLI-legend audit against `PHASE_TABLE` —
  `findings_gate` gains its driver position right after investigate (the
  13 entry is labeled an idempotent re-run), and the `selfscore` (14.2) and
  `redteam` (14.4) lines gain their phase numbers (DOC-01).

## 1.69.14 - 2026-08-22

### Fixed

- `helpers/tests/test_rule_glob.py`: the CLI-forwarding test now passes
  `--workspace` and asserts the value reaches `run_review`, instead of only
  asserting the call occurs (TEST-01, CodeRabbit nitpick, PR #23).
- `helpers/tests/test_review_live.py`: all three WR-01 guard tests install a
  recording spy over `subprocess.run` and assert an empty call list, proving
  the `--root` guard exits 2 before any git subprocess runs (TEST-02,
  CodeRabbit nitpick, PR #23).
- `helpers/tests/test_cli.py:778`: fixed the pre-existing ruff `I001`
  import-order finding; a full-repo `ruff check` now runs clean (LINT-01).

## 1.69.13 - 2026-08-22

### Fixed

- `helpers/tests/test_docs_invariants.py`: `_STALE_WORKSPACE_CLAIM_PATTERN`
  only matched the "has no ... override" wording, missing "does not support"
  and "lacks (a)" phrasings of the same false claim. Broadened the pattern to
  catch all three, with two new pattern tests pinning both denial and
  corrected wording (CodeRabbit review, PR #29).
- `SKILL.md` and `skills/sec-overlay/README.md`: reworded the `--workspace`
  override explanation to state both branches explicitly (omit it and
  `review` falls back to the per-repo sidecar; supply it and `load_paths`
  uses that value) instead of one blended sentence that read as always
  requiring an explicit flag (CodeRabbit review, PR #29).

## 1.69.12 - 2026-08-22

### Fixed

- `SKILL.md:95`, `skills/sec-overlay/README.md:35-36`, and `helpers/README.md:267`
  (06-06, WR-01): corrected three doc passages that falsely claimed `review` has
  no `--workspace` override. `review` gained the flag in 1.68.10/1.69.0
  (`cli.py:671-676`); these passages were never updated to match.

### Added

- `test_no_live_doc_denies_the_review_workspace_override` in
  `helpers/tests/test_docs_invariants.py` (WR-01): asserts no live doc claims
  `review` lacks a `--workspace` override. Pins its premise against
  `run_review`'s real signature so a future removal of the flag fails the
  guard's premise loudly instead of leaving a now-true claim unchecked.

## 1.69.11 - 2026-08-21

### Added

- `test_claude_md_phase_order_tracks_phase_table` in
  `helpers/tests/test_docs_invariants.py` (T-06-02-06): asserts every phase the
  `CLAUDE.md` "Phase order" block names appears in the same relative order as
  the live `PHASE_TABLE`, so a table reorder now fails the suite instead of
  silently drifting from the maintainer manual. The block is a condensed
  operator view, so omitted rows (`factcheck`, `demote-noise`, `selfscore`)
  are exempt; order of the named rows is enforced.

## 1.69.10 - 2026-08-21

### Added

- Four probes in `helpers/tests/test_review_profiles.py` (D-08, E-12) closing
  the vacuous-subset defect: `apply_profile`'s security-kept ⊆ general-kept
  relation had only ever been exercised on an empty comparison (`∅ ⊆ ∅`),
  which passes without confirming anything. New probes assert the relation at
  size zero (with vacuity checked as a separate assertion from the subset
  relation), size one, at the narrowest-margin `gate=None` boundary finding,
  and under a permuted input order compared by stable finding ID. All four
  reuse the existing `_dual_run_fixture()` unmodified.

## 1.69.9 - 2026-08-21

### Added

- `helpers/tests/test_frozen_contract.py` (D-15, REL-03): a sha256 byte-identity
  guard pinning `models.py`/`evidence.py` against their committed digests (both
  are byte-identical mirrors of a separate Go port and must never be edited
  alone), three `fingerprint()` golden-value tests proving its output depends
  only on `rule_id`/`cls`/`anchor` regardless of every other `Finding` field or
  construction order, and a REL-03 test reading `pyproject.toml` via stdlib
  `tomllib` to assert `[project] dependencies` stays empty.

## 1.69.8 - 2026-08-21

### Fixed

- Correct the false claim that the vendored semgrep ruleset
  (`helpers/rules/semgrep/`) is a tracked git submodule (D-04). No
  `.gitmodules` entry exists anywhere in repo history; `preflight.py`'s real
  remediation is a plain `git clone --depth 1
  https://github.com/semgrep/semgrep-rules helpers/rules/semgrep`. Fixed the
  wording across eight doc surfaces: `plugins/sec-overlay/CLAUDE.md`,
  `skills/sec-overlay/CLAUDE.md` (two spots), `skills/sec-overlay/SKILL.md`,
  `skills/sec-overlay/README.md`, `skills/sec-overlay/helpers/README.md`
  (two spots), and `skills/sec-overlay/helpers/tests/README.md`. Added a
  tree-walking doc guard (`test_no_live_doc_claims_a_git_submodule_that_does_not_exist`)
  that walks every live `.md` file under the plugin (excluding historical
  planning records and the vendored ruleset itself) so a future doc
  repeating the same false claim fails the test suite instead of surviving
  by chance.
- Correct `skills/sec-overlay/helpers/tests/README.md`'s explanation of why
  the cwd-scoping bug survived the test suite (WR-02). The prior text
  claimed the passing tests "inject their own `runner`, which bypasses the
  bug entirely" — they don't inject a `runner=` kwarg at all. They
  `monkeypatch.setattr(subprocess, "run", ...)`, patching the stdlib
  function underneath `run_review`'s `partial(subprocess.run, timeout=...,
  cwd=root)` default; their fake ignores `cwd`, which is why none of them
  caught the bug.

## 1.69.7 - 2026-08-21

### Fixed

- Correct `agents/redteam.md`'s Discriminate section (D-02). It described a
  three-way split with a "neither static-settled nor a live-exploit test"
  category exempted from the runtime plan; `redteam.py`'s `wants_runtime()`
  is a plain two-trigger OR (`runtime_disposition == "needs-runtime"` or
  `status is FindingStatus.NEEDS_DEPLOYMENT_TESTING`) with no such
  opt-out value, and `open_questions` never affects plan membership. Added
  a code-derived doc guard in `test_docs_invariants.py` pinning both
  trigger values from `sec_overlay.evidence`/`sec_overlay.models` with no
  hardcoded copies.

## 1.69.6 - 2026-08-21

### Fixed

- Fix the deps Fix-line package-name split for scoped npm-style identifiers
  (D-04, GREEN phase). `render_finding` now splits `evidence` on the last
  `@` instead of the first, so `@scope/name@version` no longer renders an
  empty backtick pair; falls back to the untouched string when the split
  empties out (a versionless scoped identifier has only the scope `@`).

## 1.69.5 - 2026-08-21

### Fixed

- Add five failing tests pinning the deps Fix-line package-name bug (D-04,
  RED phase): a scoped identifier (`@scope/name@version`) renders an empty
  backtick pair in the `**Fix.**` line because `render_finding`'s deps branch
  splits evidence on the first `@` instead of the last.

## 1.69.4 - 2026-08-21

### Fixed

- Reconcile the maintainer-manual phase order with the wired `PHASE_TABLE`
  (D-01). `redteam` moves after `report`/`selfscore` and before
  `artifact-gate` (numbered `14.4`, was `13.5` positioned before `report`);
  `postflight` is renumbered `15` as the pipeline's final phase (was `C2`).
  Both entries note they now run automatically via `PHASE_TABLE`/
  `DETERMINISTIC_ACTIONS`, with their standalone `python -m` invocations kept
  as the manual re-run path. Applied to `skills/sec-overlay/CLAUDE.md`'s
  phase-order block, `skills/sec-overlay/README.md`'s pipeline diagram,
  worked-example table, and CLI legend, and
  `skills/sec-overlay/helpers/README.md`'s deterministic-pipeline diagram.

## 1.69.3 - 2026-08-21

### Fixed

- Register `postflight` in `DETERMINISTIC_ACTIONS` (D-01, part 2). The new
  `_act_postflight` wraps `postflight.run_postflight(ctx.ws, ctx.sha)`,
  matching the function-local-import cycle-avoidance convention its
  siblings use; no try/except and no `PhaseHalt` — `run_postflight` returns
  a merged-item count, not a verdict, so a low count is not a halt
  condition. `redteam` gets no driver entry — it stays an agent phase, and
  `test_every_deterministic_phase_has_a_registered_action` now derives its
  expected key set from `PHASE_TABLE` so the two structures cannot drift
  again without a failing test.

## 1.69.2 - 2026-08-21

### Fixed

- Fix `redteam`/`postflight` being absent from `PHASE_TABLE`, so
  `run.drive()`/`run.advance()` silently skipped both phases (D-01, part 1).
  `redteam` is a new agent `PhaseSpec` (`agents/redteam.md`, input
  `findings_dir`, output `reports/redteam-plan.md`) placed between
  `selfscore` and `artifact-gate` — `artifact_gate.run_artifact_gate`
  hard-requires `redteam-plan.md` to exist, so redteam must run first, not
  after `artifact-review` as an earlier pattern draft suggested. `postflight`
  is a new deterministic `PhaseSpec` (input `artifact-review`'s gate JSON,
  output `context.prior_context_path`) appended as the table's final row.
  `redteam`'s `kind="agent"` is confirmed against the real dispatch path —
  the skill CLAUDE.md's phase-order list runs `agents/redteam.md` (sonnet)
  then `agents/redteam-adversary.md` (opus), never a bare module call.

## 1.69.1 - 2026-08-21

### Added

- Add failing tests pinning `redteam`/`postflight` into `PHASE_TABLE` and
  `DETERMINISTIC_ACTIONS` (D-01): both phases are documented in the
  maintainer manual but were absent from the mechanical phase table, so
  `run.drive()`/`run.advance()` silently skipped them. `redteam` must sit
  between `selfscore` and `artifact-gate` — `artifact_gate.run_artifact_gate`
  hard-requires `redteam-plan.md` to exist. Implementation lands next.

## 1.69.0 - 2026-08-21

### Added

- Add `--workspace` to `review`, mirroring `audit`'s existing flag (D-03).
  `run_review` gains a keyword-only `workspace` parameter: when supplied it
  resolves via `workspace.load_paths(workspace=...)`; otherwise it falls back
  to the existing per-repo sidecar resolved beneath `--root` via
  `RepoMemory.for_target`. The SCALE-03 resume-identity guard is unaffected
  either way — it checks the resolved workspace's manifest, not how that
  workspace was resolved.

## 1.68.10 - 2026-08-21

### Added

- Add three tests pinning `review`'s new `--workspace` override (D-03): the
  override case, the no-override fallback (regression guard), and a
  two-profile resume-identity check confirming the override does not weaken
  SCALE-03. Implementation lands in 1.69.0.

## 1.68.9 - 2026-08-21

### Fixed

- Fix `review` raising an unhandled filesystem exception (`FileNotFoundError`,
  `NotADirectoryError`, or an `OSError` variant, depending on platform and
  permissions) when `--root` names a path that is missing, empty, or not a
  directory (WR-01). `run_review` now checks `--root` before any workspace or
  git subprocess call and exits 2 with a one-line `error: --root must be an
  existing directory (got ...)` message, matching the existing `_bounded_int`
  exit-2 convention.

## 1.68.8 - 2026-08-21

### Added

- Add three failing tests pinning WR-01's `--root` guard (missing, empty, and
  file-as-root cases) ahead of the fix in 1.68.9.

## 1.68.7 - 2026-08-20

### Fixed

- Fix `review`'s git calls silently scoping to the CLI process's own working
  directory instead of `--root` (05-01 tracer, Phase 5 D-05-01-01): the
  shared production runner (`partial(subprocess.run, ...)`) now binds
  `cwd=root`, since `diffscope.py`'s `git diff`/`rev-parse` calls carry no
  `-C <path>` of their own. Without the binding, invoking `review` from any
  directory other than `--root` produced an empty changed-file set and a
  zero-file sealed coverage manifest with no error — discovered running the
  real pipeline end to end against a live target repo, where every existing
  test mocked the runner and never exercised a real subprocess/cwd mismatch.

## 1.68.6 - 2026-08-20

### Fixed

- Fix a hung `review` unit fetch holding the process open past `--timeout`
  (SCALE-02): `with ThreadPoolExecutor(...) as ex:` blocked on exit until
  every submitted worker finished, even one already reported as timed out,
  and the production runner never bounded the underlying git subprocess.
  The executor now shuts down via `shutdown(wait=False)`, the production
  runner default carries `timeout=--timeout` into every `subprocess.run`
  call so a hung git child is killed, and `_fetch_review_unit_files` stops
  fetching a timed-out unit's remaining members once its own deadline
  passes.

## 1.68.5 - 2026-08-20

### Added

- Add failing tests bounding a hung `review` unit fetch's wall-clock time
  to `--timeout` (SCALE-02 gap closure, RED phase): a unit whose fetch
  sleeps past the declared timeout must not hold `run_review` open, an
  abandoned worker must stop fetching once its own deadline passes, and
  every production `subprocess.run` call must carry a `timeout` equal to
  `--timeout`.

## 1.68.4 - 2026-08-20

### Fixed

- Fix `review --model` having no CLI surface (SCALE-03): `main()` never
  forwarded a model value to `run_review`, leaving the already-wired
  model-identity resume-rejection gate dead code in production. `review`
  now accepts `--model` (default `None`) and forwards it unchanged.

## 1.68.3 - 2026-08-20

### Added

- Add failing tests for a `review --model` argparse surface: forwarding
  to `run_review` and resume rejection via `cli.main` (SCALE-03 gap
  closure, RED phase).

## 1.68.2 - 2026-08-20

### Fixed

- Fix `review_comments.json`'s embedded `coverage_manifest.seal` always
  reading `null` (OUT-01): `run_review` called `write_review_comments`
  before `manifest.seal()` ran on every path except the zero-reviewable
  early return. `seal()` now runs first and its result is written once,
  so the embedded seal matches the on-disk `coverage_manifest.json` for
  both a complete and a partial run.

## 1.68.1 - 2026-08-20

### Added

- Add failing tests asserting `review_comments.json`'s embedded
  `coverage_manifest.seal` matches the on-disk `coverage_manifest.json`
  for both a complete and a partial run (OUT-01 gap closure, RED phase).

## 1.68.0 - 2026-08-20

### Added

- Pin a resumed run's reads to the SHAs the prior run sealed (SCALE-03,
  T-04-12): `review` now sources `base_sha`/`head_sha` from an existing
  `coverage_manifest.json` instead of freshly resolving `--base`/`--head`
  when one is found, so a branch that moved since the prior run cannot
  change what a resumed run reads. Each persisted SHA still round-trips
  through the same ref-resolution path, so a rewritten or collected SHA
  fails the run (exit 2) instead of silently reading a different tree as
  an empty diff.

### Fixed

- Split `test_review_live.py`'s profile-comparison test into two
  independent targets — running it against one target with two different
  `profile` values now trips the resume-identity gate added in 1.67.0.

## 1.67.1 - 2026-08-20

### Added

- Add failing tests for SHA-pinning on resume (SCALE-03, T-04-12): a resumed
  run must read diffs at the head SHA the prior run sealed, not a freshly
  resolved (possibly moved) ref, and an unresolvable persisted SHA must fail
  the run rather than read an empty diff. `run_review` does not yet source
  `base_sha`/`head_sha` from the prior manifest on resume — RED phase of a
  TDD task.

## 1.67.0 - 2026-08-20

### Added

- Add a resume-identity gate (SCALE-03): `CoverageManifest`'s `MANIFEST_VERSION`
  is now 2 and carries `model`/`profile`. `review` rejects (exit 2) a resumed
  run whose `model` or `profile` differs from the prior manifest's, before
  resolving refs or writing anything — the on-disk workspace stays
  byte-identical. A prior manifest with no recorded identity permits any
  current value.

## 1.66.1 - 2026-08-20

### Added

- Add failing tests for a resume-identity gate on `CoverageManifest`
  (SCALE-03): `model`/`profile` will round-trip through `to_dict`/`load`
  under a bumped `MANIFEST_VERSION`, and a resumed run whose model or
  profile differs from the prior manifest's will be rejected before any
  write. `ResumeIdentityError`/`check_resume_identity` are not yet
  implemented — RED phase of a TDD task.

## 1.66.0 - 2026-08-20

### Added

- Add a per-`ReviewUnit` `--timeout`: a unit's git-fetch work is dispatched
  with `ThreadPoolExecutor.submit()` and read back with
  `future.result(timeout=timeout)` in submission order; a unit that misses
  the deadline fails every one of its member files with a fixed timeout
  note, sealing the coverage manifest `"partial"` (exit 3) instead of
  raising. The timeout test covers a three-member locale-sibling unit, so a
  fix that only fails the first member (or the unit as a whole) and leaves
  the rest unfinished cannot pass. Record `--concurrency`'s enforced
  dispatch bound in `SKILL.md` beside the existing review-mode fan-out
  guidance.

## 1.65.0 - 2026-08-20

### Added

- Wrap `run_review`'s two serial per-file git-fetch loops in a bounded
  `ThreadPoolExecutor` (`_bounded_map`, sized to `--max-git-procs`), consumed
  via order-preserving `.map()` so coverage-manifest transitions still apply
  in file order regardless of fetch-completion order. No pool is built for
  zero reviewable files.

## 1.64.0 - 2026-08-20

### Added

- Add three bounded `review` CLI flags: `--concurrency` (default 8, 1-128),
  `--timeout` (default 600 seconds, 1-3600), and `--max-git-procs` (default
  16, 1-128). Each is validated by a shared `_bounded_int` helper before any
  git subprocess runs; an out-of-range value exits 2 naming the flag and its
  range and is never silently clamped.

## 1.63.1 - 2026-08-20

### Added

- Lock the `sarif.to_sarif` `partialFingerprints` contract (OUT-02) with 8
  new tests: message-independence, file/cls/evidence sensitivity, an empty
  finding list producing no fingerprint key anywhere, and a
  decomposed-vs-precomposed Unicode evidence pair producing different
  fingerprints (byte equality, no `unicodedata` normalization pass).
- Add `tests/test_review_comments.py` locking the diff-anchored comment
  contract (OUT-01): the empty-comment-list-still-has-manifest case, the
  exact 5-key comment payload shape, and `comment_from_finding`'s field
  mapping. No implementation change — both modules already satisfied the
  contract from the tracer plan.

## 1.63.0 - 2026-08-20

### Added

- Give `sec_overlay/bundle.py`'s `group_bundles` real grouping semantics:
  impl/test pairs (Python, Go, JS/TS conventions) and locale/config siblings
  in the same directory now share one `ReviewUnit`; every other file still
  falls back to its own single-member unit.
- Widen `review_agent.parse_review_response`'s focus rule with a
  keyword-only `bundle_paths` parameter — a `code_comment` naming any member
  of the reviewing unit becomes a finding attributed to that entry's own
  path, instead of only the single file under review. `None` (the default)
  keeps the prior single-file behavior unchanged.
- Thread each `ReviewUnit`'s membership from `cli.run_review` through
  `review_agent.recorded_return_source`'s new `bundle_paths_by_path`
  parameter, so real bundling is live end to end without changing the
  per-file dispatch loop shape.

## 1.62.0 - 2026-08-20

### Added

- Add `sec_overlay/bundle.py` (`ReviewUnit`, `group_bundles`) and
  `sec_overlay/review_comments.py` (`DiffComment`, `write_review_comments`),
  wired into `run_review`: every review run now writes
  `artifacts/review_comments.json`, a diff-anchored comment per shipped
  finding plus the coverage manifest. This plan ships the degenerate
  one-file-per-unit grouping only; real multi-file grouping is a later
  plan. `sarif.to_sarif` now attaches a message-independent
  `partialFingerprints` entry to every result. Progresses SCALE-01,
  OUT-01, OUT-02.

## 1.61.6 - 2026-08-19

### Fixed

- Fix `review` writing findings and reports at the bare `--root` instead of the
  per-repo memory sidecar `scan` and `audit` already use. `run_review` now
  resolves its workspace through `RepoMemory.for_target`, matching the
  existing convention; a regression test pins it. Closes DIFF-04.

## 1.61.5 - 2026-08-19

### Added

- Add tests for the `_adapt_dict` / `_adapt_optional_dict` rejection paths in
  `sec_overlay/stage_validate.py`. A non-dict stage output now has a test that
  asserts the validator returns an error list instead of raising. Closes the
  Phase 1 Nyquist validation gap.

## 1.61.4 - 2026-08-19

### Fixed

- Fix `ty check` diagnostics in `tests/test_review_tracer.py` and `tests/test_diffscope.py`.
  The fake-response class `R` declared only `returncode` and assigned `stdout` after
  construction, so `ty` could not resolve the attribute. Each `R` class now declares
  `stdout = ""` as a class attribute. Test behavior does not change.

## 1.61.3 - 2026-08-19

### Added

- `test_thread_safety_finding_ships_needs_deployment_testing_end_to_end`: composed proof that a
  thread-safety finding ships `needs-deployment-testing` through the real `run_review` CLI path,
  not only at the `apply_profile` unit level.

## 1.61.2 - 2026-08-19

### Fixed

- `review_findings.apply_profile` now assigns a kept general-defect finding's disposition via
  `findings_gate.disposition_without_receipt` (the D-12 ladder) instead of hardcoding
  `unconfirmed`. A kept thread-safety finding now ships `needs-deployment-testing`; every kept
  static-checkable class (`null-dereference`, `error-swallowing`, `resource-leak`, `injection`)
  and every unclassified kept finding still ships `unconfirmed`.

## 1.61.1 - 2026-08-19

### Fixed

- `cli.run_review`'s reflection loop now selects each reviewable file's findings from
  `review_findings.apply_profile`'s kept output instead of the position gate's pre-profile
  list, and rebinds `review_findings` to exclude every id `reflection.apply_verdict` retracted
  across every file. A retraction previously never removed its finding from the reported
  ledger; it now does, while a finding on a path the reflection loop never visits still
  survives untouched.

## 1.61.0 - 2026-08-18

### Added

- `sec_overlay.diffscope.file_text_at_ref`: reads a path's whole file text at a resolved ref via
  `git show`, mirroring the module's existing injectable-runner convention.

### Changed

- `cli.run_review` now wires a real finding source into the review-mode gate chain: it derives
  each recorded finding's position-gate snippet from the real file text at its claimed line (never
  from the model's own claim), builds `file_text_by_path` per reviewable file, and passes both
  through `review_position_gate` → `review_findings.apply_profile` → `reflection.apply_verdict` →
  the receipt gate, in that order. This makes the position gate's whole-file "relocated" rung
  reachable, so a finding claimed outside every diff hunk is now correctly dropped as
  `outside-diff` instead of declining earlier as `no-snippet`.

## 1.60.0 - 2026-08-19

### Added

- `agents/review-file.md`: the review-mode producer prompt, ported from open-code-review's main
  task prompt (D-02) — role, capabilities, strict-focus rules, and reply limit, adapted to this
  skill's single-shot no-tool dispatch and uppercase token/prompt-constants conventions. Reports
  a `code_comment` per confirmed issue and a closing `task_done`; a comment naming a path other
  than the file under review is discarded by `sec_overlay.review_agent.parse_review_response`,
  never converted, and the reviewer never claims a mechanical tool receipt.
- `SKILL.md`: a **Review mode (diff-scoped)** section documenting the prepare/dispatch/consume
  subagent loop — `cli review --prepare` writes `runs/review_plan.json` and one rendered prompt
  per reviewable file; the main agent dispatches one `review-file` subagent per entry in waves of
  three to four and persists each return with `workspace.record_agent_return`; `cli review`
  consumes the recorded returns through the position gate, profile gate, reflection filter, and
  receipt gate. A file with no recorded or unparseable return contributes no findings and is
  logged to the run's skip ledger rather than aborting the pass.

## 1.59.0 - 2026-08-19

### Added

- `sec_overlay.review_agent`: `render_review_prompt(path, rule_text, diff, changed_files)` renders
  the per-file `agents/review-file.md` prompt; `parse_review_response(text, *, path,
  rule_id_prefix)` converts a `code_comment`/`task_done` tool-call array into `Finding`s. Every
  finding carries `REVIEW_AGENT_CLAIM` (`evidence.as_llm_claim("review-agent")`) as its sole
  evidence source and `FindingStatus.RAW`, both fixed in code rather than trusted from the
  model's response — `evidence.confirms_alone` is false for every agent-authored finding
  (REV-03 elevation-of-privilege backstop). A `code_comment` naming a path other than the one
  under review is discarded and counted, never converted (Strict Focus Rule).

## 1.58.0 - 2026-08-18

### Added

- `sec_overlay.findings_gate`: `STATIC_CHECKABLE_CLASSES`/`RUNTIME_DEPENDENT_CLASSES` partition
  `review_findings.GENERAL_DEFECT_CLASSES`; `disposition_without_receipt(defect_class)` maps a
  general-defect finding with no Tier-1 receipt to `unconfirmed` or `needs-deployment-testing`
  and raises on an unknown class (D-12). `confirms_alone` remains the sole path to `confirmed`/
  `fixed`; no member is added to the frozen `FindingStatus` enum.

## 1.57.0 - 2026-08-18

### Added

- `sec_overlay.report`: `render_reflection_skipped_section`/`REFLECTION_SKIPPED_HEADING` render
  every file whose reflection pass failed open, unconditionally, mirroring the existing
  retractions section. `to_markdown` and `write_report` gain a `reflection_skips` param wiring it
  in — `review_ledger.json` and `report.md` now both carry never-silent retraction AND skip
  sections (D-14/D-15).
- `SKILL.md`: documents the reflection dispatch in the diff-scoped `review` mode — the
  `review-filter` subagent, `validate_verdict`'s parse-before-trust step, and `apply_verdict`'s
  retract-only contract.

## 1.56.0 - 2026-08-18

### Added

- `sec_overlay.reflection`: `render_reflection_prompt` renders the new `agents/review-filter.md`
  prompt per file (`{{PATH}}`/`{{DIFF}}`/`{{COMMENTS}}` only); `validate_verdict` parses and
  validates the LLM's raw JSON tool-call response before any finding sees it, reading only the
  named tool, the retracted id list, and the analysis text. `apply_verdict` now records a refused
  protected-class retraction (`REFUSED_REASON`) alongside applied ones (`RETRACTED_REASON`) rather
  than silently dropping it (D-14).
- `agents/review-filter.md`: the retract-only fact-checking prompt for diff review — a mechanical
  `PROTECTED_SUBJECT_CLASSES` veto backstops the same veto stated in the prompt; the model output
  is never trusted alone (D-16).

## 1.55.2 - 2026-08-18

### Fixed

- `tests/test_review_profiles.py`: renamed the two D-10 dual-run tests to carry `dual_run` in
  their name, matching the plan's `-k dual_run` acceptance criterion.

## 1.55.1 - 2026-08-18

### Fixed

- `tests/test_review_profiles.py`: docstring cited the wrong commit for the committed
  security-profile baseline (`15cb180` instead of `245d9e7`, the commit that actually added
  `review_profiles_security_baseline.json`).

## 1.55.0 - 2026-08-18

### Added

- `sec_overlay.review_findings`: the review-profile gate (REV-01). `apply_profile` reproduces
  the security profile's gate ladder (A-E) byte-for-byte and adds a `general` profile that
  bypasses gates A/B for a finding in one of five general-defect classes (null-dereference,
  thread-safety, resource-leak, error-swallowing, injection) — a strict superset, proven by a
  dual-run regression test against a committed baseline.
- `references/prompt-constants.md`: `GENERAL_PROFILE_EXCLUSION_RULES`, the `general` profile's
  gate wording, alongside the existing `EXCLUSION_RULES`.
- `cli.py review --profile security|general`: wires `apply_profile` into `run_review`'s
  position-gate output.

### Changed

- `report.write_report`/`write_review_ledger` gained a `review_findings` argument; the review
  ledger now carries a `review_findings` key alongside `dropped`/`position_reviews`.

## 1.54.1 - 2026-08-18

### Added

- `tests/test_review_profiles.py`: failing tests for review-profile gating (REV-01) — the
  `sec_overlay.review_findings` module the tests import does not exist yet.
- `tests/fixtures/review_profiles_security_baseline.json`: the committed dual-run baseline
  (D-10) the `security` profile's output must never drift from.

## 1.54.0 - 2026-08-18

### Added

- `rule_docs/go.md`, `java.md`, `php.md`, `rust.md`, `ts_js_tsx_jsx.md`, `kotlin.md`,
  `swift.md`: the seven previously-missing per-language rule docs, each covering the same
  five defect families in `python.md`'s fixed order (null/nil dereference, thread safety,
  injection, resource leaks, swallowed errors) with a "Do not report in the following cases:"
  exclusion block per section, ported from OCR's per-language checklists (D-02) and
  restructured into this plan's fixed five-family contract (RULE-05).

### Changed

- `rule_docs/default.md`: rewritten to the same five-family/exclusion-block structure as the
  other eight docs, replacing its prior generic Correctness/Security/Resource
  Handling/Concurrency/Maintainability sections. Out of the plan's originally scoped task
  list — added because `BUILTIN_PATH_RULE_MAP`'s trailing catch-all routes any unmatched
  path to `default.md`, and `tests/test_rule_docs.py::test_doc_covers_required_families_with_exclusion_blocks`
  is parametrized over every mapped doc, `default.md` included (deviation, Rule 2).

## 1.53.1 - 2026-08-18

### Added

- `rule_glob.py`: `REQUIRED_RULE_SECTIONS`, the five defect families every built-in rule doc
  must cover in `python.md`'s fixed order, and `RULE_SECTION_SYNONYMS`, the accepted per-language
  heading wording for each family — data `tests/test_rule_docs.py` drives its assertions from,
  not scattered test logic (RULE-05).
- `rule_glob.py`: `BUILTIN_PATH_RULE_MAP` extended from one entry to nine, mirroring OCR's
  `system_rules.json` pattern strings and doc filenames (D-02), including a trailing
  `"**/*": "default.md"` catch-all so `default.md` is a reachable map value like every other doc.
- `tests/test_rule_docs.py`: a conformance suite driven entirely from `BUILTIN_PATH_RULE_MAP`,
  `BUILTIN_DEFAULT_RULE`, and the two new constants — no hardcoded doc filename. Currently red:
  seven of the nine mapped docs (go, java, kotlin, php, rust, swift, ts_js_tsx_jsx) do not exist
  on disk yet; plan 03-03 task 2 adds them.

## 1.53.0 - 2026-08-18

### Added

- `rule_glob.py`: `read_rule_file_safe(path, repo_root)`, RULE-03's hard-reject rule-file safety
  gate — resolves symlinks, rejects a resolved extension outside `.md`/`.txt`/`.markdown`, checks
  containment of the resolved path under `repo_root`, and rejects a read over 512 KB
  (`MAX_RULE_FILE_BYTES`) enforced on the read itself, before any UTF-8 decode. Raises the new
  `RuleSafetyError` naming the path and reason, with no fallback to another layer. Diverges from
  OCR's `system_rules.go` on purpose: boundary check runs on the resolved path (closes a
  symlink-escape gap), a violation always hard-raises instead of warn-and-fallthrough, and the
  size cap is TOCTOU-safe (checked on the read, not a separate `stat`).
- `rule_glob.py`: `_entry_rule_path(rule, repo_root)`, joining a layer's relative `rule` field
  before it reaches `read_rule_file_safe`; replaces the deleted Task 1 placeholder reader.
- `cli.py`: catches `RuleSafetyError` around `build_resolution` and the per-file
  `resolve_rule_doc` call in `run_review`, printing the message to stderr and exiting 2.

## 1.52.1 - 2026-08-18

### Added

- `tests/test_rule_glob.py`: 6 failing tests (RED, Phase 3 Plan 2, Task 3) for the
  not-yet-implemented rule-file safety gate (`read_rule_file_safe`, `RuleSafetyError`):
  the 512 KB boundary at 524288/524289 bytes, a symlink escaping the repo root, a
  disallowed extension on the resolved path (direct and via a `.md` symlink to
  `.yaml`), trailing-newline stripping with inner blank lines preserved, byte-based
  sizing on multi-byte UTF-8 text, and exit code 2 with no fallback from `run_review`.

## 1.52.0 - 2026-08-18

### Added

- `rule_glob.py`: `build_file_filter(layers)`, the whole-layer first-non-empty exclude/include
  filter selection (RULE-02) — structurally separate from `match_project_rule_entry`'s per-path
  fallthrough, sharing no loop or helper with it.
- `rule_glob.py`: `build_resolution(rule_path, excludes, repo_root)`, assembling the custom
  (`--rule`), project, and global layers and their file filter, following OCR's rule that the
  custom and global layers resolve a relative `rule` field against their own config directory
  while only the project layer resolves against `repo_root`.
- `cli.py`: `--rule` and `--exclude` (repeatable) on the `review` subparser, threaded into
  `run_review`, which narrows the reviewable set by the resolved filter before the coverage
  manifest loop so an excluded file never enters coverage accounting.

### Changed

- `tests/test_rule_glob.py`: added explicit `is not None` assertions before dereferencing an
  `X | None` call result, so `ty check` narrows the type — no behavior change.

## 1.51.1 - 2026-08-18

### Added

- `tests/test_rule_glob.py`: 9 failing tests (RED, Phase 3 Plan 2, Task 2) for the
  not-yet-implemented whole-layer first-non-empty file filter (`build_file_filter`,
  `build_resolution`) and the `--rule`/`--exclude` flags on the `review` subparser, including
  a case proving the custom/global layers resolve a relative `rule` field against their own
  config directory (unlike the project layer, which resolves against `repo_root`).

### Changed

- `tests/test_rule_glob.py`: removed an unused `subprocess` import left over from Task 1.

## 1.51.0 - 2026-08-18

### Added

- `rule_glob.py`: the RULE-02 per-path four-layer rule resolver — `ProjectRuleEntry`/
  `ProjectRule`/`RuleResolution` dataclasses mirroring OCR's `rule.json` shape (D-06),
  `load_project_rule` (defensive load, absent file returns `None`), `match_project_rule_entry`
  (first-match-wins per path in JSON array order), and RULE-04's `merge_with_system_rule`
  (byte-exact `## System-Specific Rules (Mandatory)` / `## User-Specific Rules (Mandatory)`
  headers). `resolve_rule_doc` now accepts an optional `RuleResolution`, falling back to the
  built-in map alone when omitted.

## 1.50.1 - 2026-08-18

### Added

- `tests/test_rule_glob.py`: 10 failing tests (RED, Phase 3 Plan 2) for the not-yet-implemented
  four-layer rule resolver (`ProjectRuleEntry`/`ProjectRule`/`RuleResolution`, custom > project >
  global > built-in per-path fallthrough) and `merge_with_system_rule`'s header concatenation.

## 1.50.0 - 2026-08-18

### Added

- `rules/rule_docs/README.md`: what the directory is (per-language LLM prompt payloads), which
  file covers which pattern, and the rule that adding a doc means adding its pattern to
  `rule_glob.BUILTIN_PATH_RULE_MAP` in the same commit.

### Changed

- `helpers/pyproject.toml`: recorded the D-01 decision above `requires-python` — the floor
  stays 3.12 because `rule_glob.glob_match` hand-rolls `**`-aware matching instead of the
  3.13-only whole-path matcher.
- `helpers/README.md`: added `rule_glob.py` and `reflection.py` to the diff-scoped review
  module map.

## 1.49.0 - 2026-08-18

### Added

- `rule_glob.py`: brace-expansion (`expand_braces`) plus a stdlib-only `**`-aware segment
  glob matcher (`glob_match`), resolving a changed file's path to its per-language rule doc
  (`resolve_rule_doc`), case-insensitive, first-match-wins, falling back to `default.md`.
- `reflection.py`: a retract-only LLM-verdict filter (`apply_verdict`, `build_payload`) — a
  verdict can only remove a finding the code submitted, never add or rank one;
  `PROTECTED_SUBJECT_CLASSES` is a hardcoded veto no verdict can override.
- `rules/rule_docs/default.md` and `rules/rule_docs/python.md`: built-in rule docs consumed
  by `rule_glob.resolve_rule_doc`.
- `cli.py`: `run_review` gained `--profile` (`security`/`general`, reserved for a later plan),
  resolves each reviewable file's rule doc, and runs kept findings through
  `reflection.apply_verdict`, recording a `ReflectionSkip` and failing open on a per-file error.
- `report.py`: `write_review_ledger`/`write_report` gained keyword-only
  `reflection_retractions`/`reflection_skips`, rendered into the same `review_ledger.json`
  (`reflection_retractions`, `reflection_skipped` keys) — no second artifact file.

## 1.48.7 - 2026-08-18

### Added

- `test_review_tracer.py`: 7 failing tests (RED, Phase 3 Plan 1) for the not-yet-implemented
  `rule_glob` (brace-expand and `**`-aware glob-based rule-doc resolution) and `reflection`
  (retract-only LLM-verdict filter) modules.

## 1.48.6 - 2026-08-17

### Fixed

- `cli.py`: `run_review` now wires `review_position_gate`'s dropped/declined output into
  `report.write_report`, so a review run writes `report.md`'s drop/decline sections and
  `artifacts/review_ledger.json` on every path, including the zero-drop/zero-decline case
  (T-02-15, T-02-18). Previously the gate's return value was discarded and no review-mode
  run ever produced these outputs.

## 1.48.5 - 2026-08-17

### Fixed

- `cli.py`: `run_review`'s docstring no longer claims batching and exit codes 2/3 are future
  work — both were already implemented. Kept the accurate note that finding-source integration
  is still pending (WR-02).

## 1.48.4 - 2026-08-17

### Fixed

- `phase_gate.py`: removed the unused `UNRESOLVED_POSITION_REASON` constant. The gate never
  assigned it — a finding it cannot position goes to `declines`, never `dropped` — so
  `DROP_REASONS` now holds only `outside-diff`, the one reason the gate actually emits (WR-01).

## 1.48.3 - 2026-08-17

### Fixed

- `cli.py`: `run_review` now computes `diff_line_counts` and `binary_paths` and passes them into
  `partition(...)`. The tracer-path call left both at their no-op defaults, so an oversized
  (>5000-line) or binary changed file stayed `reviewable` instead of landing in
  `selection.excluded` with reason `too-large`/`binary` (CR-03).

## 1.48.2 - 2026-08-17

### Fixed

- `diffscope.py`: `resolve_ref_sha` now raises `ValueError` when `git rev-parse --verify` exits
  non-zero. A syntactically valid but nonexistent ref (e.g. `does-not-exist-branch`) previously
  resolved to `""` instead of raising, silently defeating `run_review`'s documented "exit 2 on an
  invalid ref" contract (CR-02).

## 1.48.1 - 2026-08-17

### Fixed

- `phase_gate.py`: `review_position_gate`'s `declines` list now holds the `PositionResult`
  `resolve_position` returned, not the raw `Finding`. `report.write_report(...,
  position_reviews=declines)` requires `PositionResult`-only fields (`claimed_path`,
  `claimed_line`, `snippet`, `reason`) that `Finding` does not have, so composing the two
  functions raised `AttributeError` on the first decline (CR-01).

## 1.48.0 - 2026-08-17

### Added

- `cli.py`: `run_review`'s per-file loop now catches any exception from
  `parse_hunks(file_diff_text(...))`, transitions that file to `failed` with the exception text
  as its note, and continues to the next file instead of aborting the run. The coverage
  manifest's seal now drives the exit code — `complete` (including zero reviewable files)
  returns 0, `partial` prints one "unfinished file" line per non-`done` entry (path, state,
  note) and returns 3. The exit-2 ref-validation path is unchanged.

## 1.47.1 - 2026-08-17

### Added

- `tests/test_cli.py`: failing tests for `run_review` mapping the coverage-manifest seal to an
  exit code — a `complete` seal returns 0, a `partial` seal returns 3 and prints one line per
  unfinished file naming its path, state, and note. RED phase for the next `cli.py` change — no
  production code changed in this release.

## 1.47.0 - 2026-08-17

### Added

- `report.py`: `DROPPED_FINDINGS_HEADING` and `render_dropped_findings_section(dropped)`,
  matching `render_position_review_section`'s heading level, table style, and empty-list
  none-dropped fallback. `to_markdown` gained `dropped` and `position_reviews` arguments and
  now renders both sections unconditionally, right after the findings body. `write_report`
  gained the same two arguments and threads them into both `to_markdown` and
  `write_review_ledger` from one call, so the markdown report and the JSON ledger are built
  from a single source and cannot disagree about what a review-mode run dropped.

## 1.46.1 - 2026-08-17

### Added

- `tests/test_report.py`: failing tests for `render_dropped_findings_section`, `to_markdown`
  wiring the dropped-findings and position-review sections after the findings body, and
  `write_report` writing `review_ledger.json` once from the same `dropped`/`position_reviews`
  arguments it renders into the markdown report. RED phase for the next `report.py` change —
  no production code changed in this release.

## 1.46.0 - 2026-08-17

### Added

- `phase_gate.py`: `review_position_gate` now splits findings three ways — `kept`, `dropped`,
  and `declines` — instead of the earlier `(kept, dropped)` pair. A finding that the
  positioning ladder cannot resolve at all is a decline, kept out of both other lists. Every
  other finding is checked against `diffhunks.hunk_for_line` at its resolved position: inside a
  hunk keeps the finding (moved there if relocated), outside drops it with reason
  `outside-diff`. `DroppedFinding` now carries `path`, `line`, `rule_id`, `reason`; the drop
  reasons are a frozen set, `DROP_REASONS`. The gate never mutates an input finding.

## 1.45.1 - 2026-08-17

### Added

- `tests/test_phase_gate.py`: failing tests for the plan 02-05 shape of
  `review_position_gate` — a three-way kept/dropped/declines split, sorted drop order, and
  hunk-boundary adjacency checks. The implementation change lands in a follow-up commit.

## 1.45.0 - 2026-08-17

### Added

- `report.py`: `render_position_review_section(results)` renders a `## Position review required`
  markdown table, one row per declined finding, with pipe/newline escaping so a snippet cannot
  corrupt the table; `write_review_ledger(ws, *, position_reviews, dropped)` writes
  `artifacts/review_ledger.json` with `position_reviews`/`dropped` keys always present. Neither
  function is wired into `to_markdown`/`write_report` yet — plan 02-05 wires them once the drop
  ledger exists.

## 1.44.0 - 2026-08-17

### Added

- `positioning.py`: `resolve_position` now runs the full four-rung ladder — hunk match in the
  claimed file (`exact`), whole-file match in the claimed file (`relocated`/`whole-file-match`),
  match in exactly one other changed file (`relocated`/`cross-file-match`), else decline
  (`needs-position-review`). Two or more matches at any rung decline instead of picking one.
  `PositionResult` gained a `snippet` field, carried on every result including declines.

### Fixed

- `phase_gate.py`: `review_position_gate` gained an optional `file_text_by_path` parameter to
  match `resolve_position`'s new five-argument signature.

## 1.43.0 - 2026-08-17

### Added

- `review_coverage.py`: `CoverageManifest.seal()` now raises `CoverageTransitionError` (a
  `RuntimeError`) on an empty manifest instead of vacuously returning `complete` — a run must
  never claim coverage it did not perform (T-02-05). `cli.py`'s `run_review` returns 0 before
  calling `seal()` when there is nothing to review, so a zero-file diff still exits cleanly.
- `diffhunks.py`: `Hunk` is now a frozen dataclass with tuple-typed `added`/`deleted`/`context`
  fields, so `parse_hunks` is provably pure. Line splitting moved to `str.splitlines()`, fixing a
  bug where a diff ending in a newline produced a spurious trailing empty context line. New
  `hunk_for_line(hunks, line)` returns the containing `Hunk` or `None`.

## 1.42.0 - 2026-08-17

### Added

- `file_select.py`: `EXCLUSION_REASONS` is now enforced, not just documented — `ExcludedFile`
  raises `ValueError` for any reason outside the closed set. `partition` gained
  `diff_line_counts`, `binary_paths`, and `max_diff_lines` (default 5000, D-11) keyword
  parameters, defaulting to no-op values so existing callers are unaffected. The check order is
  now deleted, then binary, then generated, then not-allowlisted, then too-large (strictly over
  the cap; exactly at the cap stays reviewable). No `--max-diff-lines` CLI flag — a cap override
  is deferred to Phase 4.

## 1.41.0 - 2026-08-17

### Added

- `file_select.py`: full allowlist and default-exclude globs ported from open-code-review.
  `ALLOWED_EXTENSIONS` is now the complete 86-extension set from
  `supported_file_types.json`; `DEFAULT_EXCLUDE_GLOBS` is a new 40-pattern tuple, brace-expanded
  from `default_exclude_patterns.json`, driving a new `_is_generated(path)` check. `partition`
  normalizes a git-quoted non-ASCII path and lowercases the extension before matching, and
  checks deleted status, then generated globs, then the allowlist, in that order.

## 1.40.0 - 2026-08-17

### Added

- `diffscope.py`: full ref-validation and `changed_file_records` behavior. The allowlist pattern
  now permits `~` so `HEAD~1`-style ancestor refs validate; `changed_file_records` parses the
  full `--name-status` vocabulary and carries `old_path` for renames and copies; two new
  functions, `file_diff_line_count` and `binary_paths`, give `file_select.partition` its
  size-cap and binary inputs (landing in the next release). The `review` CLI branch now catches
  a `ValueError` from ref resolution and exits `2` with one actionable stderr line naming the
  ref, without laundering any other `ValueError` into the same exit code.

## 1.39.0 - 2026-08-17

### Added

- New `sec-overlay review --base <ref> --head <ref> --root <path>` CLI verb: a diff-scoped,
  position-verified review pass. Resolves both refs to SHAs before any other git call, selects
  changed files (`file_select.partition`), parses their hunks (`diffhunks.parse_hunks`),
  confirms or declines each finding's claimed position against the diff without fuzzy matching
  (`positioning.resolve_position`), gates findings on that decision
  (`phase_gate.review_position_gate`), and tracks per-file coverage to a terminal seal
  (`review_coverage.CoverageManifest`, persisted to `artifacts/coverage_manifest.json`). Exits 0
  only when the manifest seals `complete`. Wires exactly one changed file through every layer
  (the tracer path) — batching, exit codes 2/3, the full extension allowlist, and the diff-line
  size cap arrive in a later plan. No new runtime dependency; `coverage.py`, `models.py`, and
  `evidence.py` are unchanged.

## 1.38.0 - 2026-08-17

### Added

- `Workspace` gained an `artifacts` property (`root/artifacts`) for review-mode run state — the
  coverage manifest and review ledger the upcoming `review` CLI mode writes. Never routed through
  `reports_dir`. `ensure()` creates it.

## 1.37.11 - 2026-08-17

### Fixed

- `tests/fixtures/graph_target/app/{db,api}.py` reference `cursor`/`app` names that only exist
  at runtime through the fixture's structural-scan contract (`sec_overlay.graph` parses these
  files without importing them). `ty` flagged both as unresolved references. Added a stub
  binding for each (`cursor: Any = None`, `app: Any = None`) placed to preserve every line
  number `test_graph.py` pins (`app/db.py:1:run_query`, `app/api.py:4:handler`,
  `app/api.py:10:get_widget`). No behavior change — these files are never executed.

## 1.37.10 - 2026-08-17

### Fixed

- `sec_overlay/stage_validate.py`'s `_VALIDATORS` dict held three differently-typed validator
  signatures (`dict`-only, `dict | None`, and `object`), which `ty` flagged as a union-callable
  mismatch at the `fn(obj)` call site. Added `_adapt_dict`/`_adapt_optional_dict` factories that
  isinstance-check the stage payload before delegating, unifying every entry to
  `Callable[[object], list[str]]`. This also closes a real gap: a non-dict subagent output to
  most stages previously crashed with `AttributeError` instead of returning a validation error
  (only `_validate_runtime_test` guarded against this before). No behavior change for
  well-formed dict input.

## 1.37.9 - 2026-08-17

### Fixed

- `test_patch_status.py`'s fake-runner helper monkey-patched a `calls` list onto a plain
  function object, which `ty` cannot type (function objects have no declared attribute
  namespace). Replaced with a small `_Runner` class holding `calls` as a real instance
  attribute and a `__call__` method standing in for the function; fixes the remaining
  `unresolved-attribute` VAL-02 row. No behavior change.

## 1.37.8 - 2026-08-17

### Fixed

- `test_rule_matcher.py`, `test_bucket_b.py`, and `test_calibrate.py` add an explicit
  `is not None` assertion before dereferencing a call result typed `X | None`
  (`AsvsCatalog.get`, `emit_semgrep_rule`, `Finding.risk_score`) — each call is known to return
  a non-`None` value at that point in the test, but `ty` cannot infer that without the guard.
  Fixes 3 VAL-02 ledger rows (`unresolved-attribute` / `not-subscriptable` / `unsupported-operator`);
  no behavior change.

## 1.37.7 - 2026-08-17

### Fixed

- `test_bench.py`'s `CorpusEntry` builder and `test_profile.py`'s `ScanProfile` roundtrip test
  now build the base object with explicit fields and layer overrides with `dataclasses.replace`,
  instead of a `dict()` + `.update(kw)` + `Cls(**d)` / `Cls(**base, notes=...)` splat — the same
  `ty` per-field argument-checking bypass fixed for `Finding` builders in 1.37.6. Clears the
  remaining VAL-02 `invalid-argument-type` rows for both files; no behavior change.

## 1.37.6 - 2026-08-17

### Fixed

- `test_citations.py`, `test_factcheck_baseline_envelope.py`, and `test_report.py`'s `Finding`
  test-builders now use `dataclasses.replace(base, **kw)` over per-test overrides instead of
  `dict()` + `.update(kw)` + `Finding(**d)` — `**d`'s concrete inferred dict type bypassed `ty`'s
  per-field argument checking, which `replace`'s `**changes: Any` typing restores; fixes the
  bulk of the VAL-02 `invalid-argument-type` ledger rows; no behavior change.

## 1.37.5 - 2026-08-17

### Fixed

- `test_postflight.py` replaces a single-element list-slice with `next(...)`, and
  `test_structural_index.py` replaces a `"\n".join([...])` with adjacent string literals —
  fixes the two remaining VAL-02 ruff findings (`RUF015`, `FLY002`); no behavior change.

## 1.37.4 - 2026-08-17

### Fixed

- `test_prefilter.py` and `test_wiring.py`'s `Exclusions([], [], [])` fixture calls now pass
  `Exclusions(set(), [], set())`, matching the dataclass's `set[str]`-typed `rule_ids`/`classes`
  fields — fixes 16 `invalid-argument-type` diagnostics (VAL-02 ty ledger row); no runtime
  behavior change.

## 1.37.3 - 2026-08-17

### Fixed

- `workspace.py`'s `Workspace` gains a hand-written `__init__` (replacing the dataclass
  `__post_init__`) so the `str | Path` constructor argument type-checks under `ty` — fixes
  three `invalid-argument-type` diagnostics in `test_workspace.py` without widening the
  stored `Path`-typed fields (VAL-02 ty ledger row).

## 1.37.2 - 2026-08-16

### Fixed

- Persist the fence baseline so resume invocations catch agent-phase tree writes.
- Add `run.advance` to fence, receipt, and record each agent phase.
- Pin the pass SHA on resume instead of re-reading HEAD.
- Correct `audit.md` resume steps and correlation output paths.

## 1.37.1 - 2026-08-16

### Fixed

- Sort import block in test_run.py to clear ruff I001.

## 1.37.0 - 2026-08-16

### Added

- Add /sec-overlay:audit command.

## 1.36.1 - 2026-08-16

### Fixed

- Fix red-team gate path collision (O-65): the adversary writes redteam-adversary.json. Added test to verify old path absent.

## 1.36.0 - 2026-08-16

### Added

- Add single-repo drive loop with per-phase fence and receipt.

## 1.35.0 - 2026-08-16

### Added

- Add manifest synthesis for correlation.

## 1.34.0 - 2026-08-16

### Added

- Add scan-profile role inference.

## 1.33.0 - 2026-08-16

### Added

- Add run.env token writer.

## 1.32.0 - 2026-08-16

### Added

- Add per-phase receipt writer.

## 1.31.1 - 2026-08-16

### Fixed

- Remove unused `pathlib.Path` import from `helpers/tests/test_run.py` (ruff F401).

## 1.31.0 - 2026-08-16

### Added

- Add run.py driver working-tree fence.

## 1.30.3 - 2026-08-16

### Changed

- Name the CVSS v4.0 score invocation in `agents/threat-model.md` step 5 —
  `sec_overlay.cvss.cvss40_base('<vector>')` run from `helpers/` — so the
  agent has a way to obtain the score it is told never to hand-compute.
  Note the same invocation in `agents/README.md`'s threat-model row.
- Name STRIDE in the skill `CLAUDE.md` §2 phase table and `README.md`'s
  worked-example table, restoring a term dropped from an earlier pass.

## 1.30.2 - 2026-08-16

### Changed

- Restore the phase-adversary annotation on the Threat model row of the
  skill `CLAUDE.md` §2 phase table (dropped in the 1.30.1 compression pass);
  note in the skill `README.md` that each of `arch-gate` / `tm-gate` is
  preceded by the opus phase-adversary review, not only the deterministic
  check.

## 1.30.1 - 2026-08-16

### Changed

- Document the `architecture/` and `threat-model/` artifact trees and the
  `arch-gate` / `tm-gate` deterministic phases across the skill `CLAUDE.md`,
  `SKILL.md`, both READMEs, and the plugin `CLAUDE.md`'s CLI-callable module
  list (`diagram_gate`, `ste_lint`). No behavior change.

## 1.30.0 - 2026-08-16

### Changed

- Re-point every remaining consumer prompt (`investigate.md`, `critic.md`,
  `validate.md`, `context-ingest.md`, `phase-adversary.md`, `postflight.md`)
  from the retired `kb/architecture.md` / `kb/entities/` / `kb/THREAT_MODEL.md`
  paths to `architecture/arc42.md` and `threat-model/threat-model.md`.
  `phase-adversary.md` gains an ownership-boundary checklist bullet: an
  architecture claim naming threats/mitigations, or a threat-model claim
  restating structure/stack, is a defect.
- Remove the now-dead `kb.py::entities_dir` helper (no remaining callers).

## 1.29.0 - 2026-08-16

### Added

- Wire `arch-gate` and `tm-gate` deterministic phase rows into `PHASE_TABLE`,
  right after `architecture` and `threat_model`. Each gate runs the diagram
  gate, the ASD-STE100 prose linter, and (for `tm-gate`) the arc42/threat-model
  duplication check, writing `kb/gates/arch-gate.json` / `kb/gates/tm-gate.json`
  and halting the run on any error. `tm-gate` requires `threat-model/dfd.mmd` to
  exist; `arch-gate` does not require the threat-model tree at all.

## 1.28.0 - 2026-08-16

### Changed

- `agents/threat-model.md` rebuilt on the DFD/STRIDE contract: it now derives
  `threat-model/dfd.mmd` from `architecture/container-diagram.mmd` (SHA-headered),
  `threat-model/attack-sequences/sequence-<scenario>.mmd`, and
  `threat-model/threat-model.md` — a methodology record, a CVSS v4.0 findings table, and
  a prioritized hunt list — replacing the old single-file `kb/THREAT_MODEL.md` output.

## 1.27.0 - 2026-08-16

### Changed

- `agents/architecture.md` rebuilt on the C4/arc42 contract: it now writes
  `architecture/context-diagram.mmd`, `architecture/container-diagram.mmd`,
  `architecture/component-diagram-<name>.mmd` and
  `architecture/runtime-view/sequence-<scenario>.mmd` (only where warranted), and
  `architecture/arc42.md` — replacing the old single-file `kb/architecture.md` +
  `kb/entities/<component>.md` output.

## 1.26.0 - 2026-08-16

### Added

- `kb.py` gains path helpers for the new `architecture/` and `threat-model/` workspace trees
  (`arch_dir`/`arc42_path`/`container_diagram_path`, `threat_dir`/`threat_model_path`/`dfd_path`),
  replacing the old single-file `kb/architecture.md` and `kb/THREAT_MODEL.md` paths.
  `Workspace.ensure()` now creates `architecture/runtime-view/` and
  `threat-model/attack-sequences/` alongside the existing KB directories.

## 1.25.0 - 2026-08-16

### Added

- `references/architecture-standards.md` fixes the C4 + arc42 contract for the architecture
  phase: which diagrams to produce, the arc42 section table, and the ownership boundary
  against the threat-model phase.
- `references/threat-model-standards.md` fixes the DFD + STRIDE contract for the
  threat-model phase: signal-based methodology augmentation (PASTA/LINDDUN), how `dfd.mmd`
  derives from `container-diagram.mmd`, and the findings-table column contract.
- `references/mermaid-caps.md` is the single source of truth for per-diagram-kind element
  caps, mirrored in `sec_overlay.diagram_gate.CAPS`/`SEQ_CAPS` and kept in sync by
  `tests/test_references_caps.py`.
- `prompt-constants.md` gained an `STE_PROSE` block: human-facing prose (arc42.md,
  threat-model.md, findings-table free text) now follows ASD-STE100's checkable core.

## 1.24.1 - 2026-08-16

### Fixed

- `mermaid_index.py`'s flowchart edge scan matched only the first `-->` on a line, dropping every
  hop after the first in a chained edge (`a --> b --> c`) and false-flagging the middle node as an
  orphan; the scan now restarts each search at the matched destination.
- `mermaid_index.py`'s sequence-diagram regexes rejected hyphenated participant/message ids
  (`auth-api`), silently recording a truncated id and undercounting messages; the id class now
  allows `-` and the source-id match is non-greedy so it stops before the arrow.
- `diagram_gate.py`'s `run_diagram_gate` treated a missing `dfd.mmd` as always-optional; it now
  takes a keyword-only `require_threat_model` flag (CLI: `--require-threat-model`) that turns a
  missing threat-model diagram into a gate error.
- `diagram_gate.py` gained a node-label word-count check (spec's "node labels: name only" rule):
  a bracket label over 4 words is now an error, matching the existing edge-label check.

## 1.24.0 - 2026-08-16

### Added

- `sec_overlay/artifact_gate.py` gains `check_duplication(arc42_text, tm_text)`: flags a
  threat-model heading that restates an `architecture/arc42.md` heading, and flags a
  structure heading (e.g. "Building Block View", "Deployment View") appearing in the
  threat-model doc at all. `run_artifact_gate` calls it only when both
  `architecture/arc42.md` and `threat-model/threat-model.md` exist; older workspaces and
  the existing tests are unaffected.

## 1.23.1 - 2026-08-16

### Fixed

- `sec_overlay/ste_lint.py`'s `_prose_blocks` no longer silently drops every line after an
  unterminated code fence — an unclosed ` ``` ` now yields an `"unbalanced code fence"` error
  instead of a false-clean result.
- `sec_overlay/ste_lint.py`'s sentence splitter no longer fractures a paragraph or sentence at
  an abbreviation (`e.g.`, `i.e.`, `etc.`, `vs.`, `cf.`, `approx.`, `viz.`, `al.`) — it now
  splits only at sentence-ending punctuation followed by a capitalized word and folds an
  abbreviation-preceded split back onto its clause, so an abbreviation-heavy paragraph no
  longer produces a false "over 6 sentences" error and a genuinely over-length sentence
  containing an abbreviation is still flagged.

## 1.23.0 - 2026-08-16

### Added

- `sec_overlay/ste_lint.py`: a deterministic linter for the checkable structural subset of
  ASD-STE100 — sentence >25 words, semicolon in prose, and paragraph >6 sentences are errors;
  a 4+ word capitalized run mid-sentence and a sentence repeating " then " are warnings. Fenced
  code, mermaid blocks, headings, table separator rows, inline code spans, and URLs are exempt;
  table free-text cells are linted. `lint_prose(text)` is the entry point; the CLI
  (`python -m sec_overlay.ste_lint <files...> [--require-frontmatter]`) exits 1 on any error.

## 1.22.1 - 2026-08-16

### Fixed

- `sec_overlay/diagram_gate.py`'s `_provenance` no longer crashes with `FileNotFoundError` when
  the derived-from source file doesn't exist — a missing `container-diagram.mmd`, or an attack
  sequence whose header names an unknown parent — it now returns a `"derived-from source ... not
  found"` error string.
- `sec_overlay/diagram_gate.py`'s `check_diagram` no longer crashes with an uncaught `ValueError`
  when the source diagram (for element/participant-diff checks) is unparseable — it now returns a
  `"source ... unparseable: ..."` error string.
- `sec_overlay/mermaid_index.py`'s `_INLINE_LABEL_SKIP` only spanned single-char bracket pairs and
  missed multi-char forms like `q{{Queue}}`, dropping the edge entirely and false-flagging the
  source node as an orphan-detail node — widened to one bracket-class alternation covering all
  Mermaid node shapes.

## 1.22.0 - 2026-08-16

### Added

- `sec_overlay/diagram_gate.py`: deterministic hard gate over generated Mermaid diagrams —
  per-type node/participant/message caps (`CAPS`, `SEQ_CAPS`), ≤4-word edge labels, DFD
  trust-boundary-subgraph requirement, derivation provenance (`%% derived-from: <file>
  sha256:<hash>`, rejecting a stale hash or a new element/participant absent from the source),
  legend-required styling, and orphan-detail nodes (a node that only ever receives and isn't a
  store/actor) scoped to `container`/`component`/`dfd` diagrams only. `run_diagram_gate(arch_dir,
  tm_dir)` walks a full architecture/threat-model tree. CLI-callable
  (`python -m sec_overlay.diagram_gate --architecture DIR --threat-model DIR`).

### Fixed

- `sec_overlay/mermaid_index.py`'s edge regexes no longer drop an edge whose source node carries
  an inline bracket label on the same line (`web[Web] --> api[API]`) — previously produced zero
  edges for that shape.
- `sec_overlay/mermaid_index.py`'s C4 parser now also adds `Person(...)` and `*_Ext(...)` element
  ids to `store_ids`, marking them orphan-exempt alongside `ContainerDb`/`SystemDb`/`*Queue`.

## 1.21.1 - 2026-08-16

### Fixed

- `sec_overlay/mermaid_index.py`'s flowchart edge scan no longer misreads a mid-arrow label
  (`a -- some label --> b`) as a phantom source node — `_FLOW_EDGE_MID` now runs first, so the
  real node ids and the label are captured instead of silently dropped.

## 1.21.0 - 2026-08-16

### Added

- `sec_overlay/mermaid_index.py`: `index_mermaid(text)` line-oriented structure extractor for
  Mermaid flowchart, sequence, and C4 diagrams — nodes, edges, subgraph membership, sequence
  participants/message count, data-store ids, and style detection, feeding the upcoming diagram
  gate.

## 1.20.2 - 2026-08-16

### Fixed

- `sec_overlay/cvss.py`'s `_parse` no longer silently drops score-affecting Threat (`E`) or
  Environmental (`CR`/`IR`/`AR`/`M*`) metrics — a vector carrying one with a value other than `X`
  (Not Defined) now raises `ValueError` instead of returning the unchanged base score; NVD-shaped
  `.../E:X/CR:X/IR:X/AR:X` suffixes still parse and score identically to the bare base vector.
- `sec_overlay/calibrate.py`'s `_derived_score` now records a `calibrate:cvss-unparseable` history
  event (with the offending vector) before falling back to the heuristic score on any unparseable
  `cvss_vector`, so a pre-migration CVSS 3.1 vector leaves an audit trail instead of a silent
  fallback.
- `references/finding-template.md`'s §5 metric-justification list updated from the CVSS 3.1 metrics
  (`AV, AC, PR, UI, S, C, I, A`) to all 11 CVSS v4.0 base metrics (`AV, AC, AT, PR, UI, VC, VI, VA,
  SC, SI, SA`).

## 1.20.1 - 2026-08-16

### Fixed

- Migrated the last `CVSS:3.1` fixture vectors in `test_report.py`, `test_models.py`,
  `test_citations.py`, and `test_factcheck_baseline_envelope.py` to `CVSS:4.0` vectors of
  equivalent meaning, so the repo has zero v3.1 vectors outside `sec_overlay/cvss.py`'s
  rejection-path test and its own error message.

## 1.20.0 - 2026-08-16

### Changed

- `agents/validate.md`'s confirmed-finding contract and `agents/investigate.md`'s example
  finding now specify a CVSS v4.0 vector (`CVSS:4.0/AV:_/AC:_/AT:_/PR:_/UI:_/VC:_/VI:_/VA:_/
  SC:_/SI:_/SA:_`) instead of v3.1, matching the v4.0-only parser (`sec_overlay/cvss.py`).
  `references/prompt-constants.md`'s `SEVERITY_GUIDANCE` block, `references/finding-template.md`,
  and `references/README.md` updated to the same legal v4.0 base-metric values so every prompt
  that imports the shared block proposes a vector the engine accepts.

## 1.19.0 - 2026-08-16

### Changed

- Re-point `sec_overlay/calibrate.py` from the removed `cvss31_base` to `cvss40_base`
  (`sec_overlay/cvss.py`'s CVSS v4.0 engine); `risk_score`/`priority` derivation shape is
  unchanged. `Finding.cvss_vector`'s docstring in `models.py` now says "CVSS v4.0". Migrated
  `test_calibrate.py`'s CVSS fixtures to v4.0 vectors, with expectations recomputed from the
  real scoring engine.

## 1.18.1 - 2026-08-16

### Fixed

- Wrap `tests/test_cvss.py`'s `sec_overlay.cvss` import across multiple lines to clear a ruff
  `I001` warning introduced by the CVSS v4.0 scoring-engine rewrite.

## 1.18.0 - 2026-08-16

### Changed

- Rewrite the scoring engine (`sec_overlay/cvss.py`) from CVSS 3.1 to CVSS v4.0: `cvss40_base`
  computes the base score via a MacroVector/interpolation port of FIRST's official calculator
  (`cvss_score.js`, BSD-2-Clause) against `cvss4_data.py`'s tables, base metrics only (no
  Threat/Environmental/Supplemental support). `offensive_priority` keeps its 3.1 branch order
  verbatim. A `CVSS:3.x` vector now raises `ValueError` naming the required 4.0 migration.

## 1.17.0 - 2026-08-16

### Added

- Vendor CVSS v4.0 MacroVector lookup and interpolation tables (`sec_overlay/cvss4_data.py`) from
  FIRST's official calculator (BSD-2-Clause), for a future v4.0 scoring engine.

## 1.16.2 - 2026-08-15

### Fixed

- Rewrite the `_full` test helper in `test_report.py` as a dict literal to clear a ruff `C408`
  warning introduced by the report-split work.

## 1.16.1 - 2026-08-15

### Changed

- Document the `artifact-gate` → `artifact-review` phases (Tasks 14–16) in the operating manual:
  `skills/sec-overlay/CLAUDE.md` §2 phase order and §4 workspace artifacts, `CLAUDE.md`'s
  CLI-callable module list (`artifact_gate`), and `skills/sec-overlay/README.md`'s pipeline map.

## 1.16.0 - 2026-08-15

### Added

- `PHASE_TABLE` (`phases.py`) gains two phases after `selfscore`: `artifact-gate` (deterministic,
  runs `run_artifact_gate`) then `artifact-review` (agent, `agents/artifact-review.md`). The driver
  registers `_act_artifact_gate`, which raises `PhaseHalt` when the gate reports any error, wiring
  Task 14's `artifact_gate.py` and Task 15's prompt into a normal run for the first time.

## 1.15.0 - 2026-08-15

### Added

- New `agents/artifact-review.md` (§4.8): the opus adversary that runs after the deterministic
  `artifact_gate` passes, checking that `report.md`, `report.sarif`, and `redteam-plan.md` tell
  the truth about what the run found — claim-to-evidence against each finding's tool receipt,
  impact honesty, and red-team coverage. Reasoning alone may demote severity, force a re-render
  via `render_stale`, or add an `open_questions` entry, but never delete or reject a tool-receipt-
  backed finding. Writes `kb/gates/artifact-review.json`.

## 1.14.0 - 2026-08-15

### Added

- New `artifact_gate.py` module (§4.8): `run_artifact_gate(ws)` is a deterministic gate over a
  finished run's own output artifacts, checking `report.md` for stale constant sections and
  over-long triage cells, every shipping finding for a detail file and a red-team directive, every
  triage-table ID for a resolving finding, and `CONTEXT.md`'s mermaid diagram for the ≤10-node
  style cap (ISSUE-022). Writes `kb/gates/artifact-gate.json` and runs before the opus
  artifact-review adversary.

## 1.13.1 - 2026-08-15

### Fixed

- `validate.md` now requires a `confirmed` finding to carry a real, derived `cvss_vector` and a
  non-empty `preconditions` list, routing to `needs-deployment-testing` otherwise; `trace.md` now
  records `preconditions` on a statically-confirmed reachability verdict — calibrate scores off
  these fields verbatim, so a missing/guessed vector no longer produces a flat, wrong score
  (ISSUE-008). Prompt-only fix; the calibrate scorer is unchanged.

## 1.13.0 - 2026-08-15

### Added

- `build_self_score` gained `critic_viable`, `critic_rejected`, and `critic_reject_rate` (0.0 with
  no critic events), counted from `critic:viable`/`critic:rejected` history events across all
  findings (ISSUE-043) — measurement only, nothing gates on the rate.

## 1.12.3 - 2026-08-15

### Fixed

- `validate_stage` now raises `ValueError` for a stage with no registered validator instead of
  silently passing — a silent pass masked mis-named stages (ISSUE-034).
- `run_prefilter` gained a `strict: bool = True` parameter: a planned SAST backend left in
  `skipped_reasons` or `failed` now raises `RuntimeError` via the new `_raise_on_incomplete_backends`
  helper instead of returning a silent partial result. Pass `strict=False` only for a deliberately
  partial run. A `"disabled"` skip reason is excluded from the raise — a profile turning a backend
  off on purpose is a planning decision, not a coverage hole.

## 1.12.1 - 2026-08-15

### Fixed

- `context-ingest` now has a real check on `docs_read`: `cited_source_docs` collects
  every `source_doc` an item or its history cites, and the `context` stage-validator
  rejects a citation to a doc absent from `provenance.docs_read` — `docs_read` can no
  longer be a placeholder count.

## 1.12.0 - 2026-08-15

### Added

- Time each deterministic driver phase (`run_deterministic_phase`) and record it into
  `state.budget["timings"]`; the report's economics section renders a "Wall-clock by
  phase" list when timings are present (ISSUE-014).

## 1.11.0 - 2026-08-15

### Added

- Per-phase wall-clock timing accounting: `cost.record_timing` and
  `cost.aggregate_timings_by_phase` sum recorded seconds by phase (ISSUE-014).

## 1.10.0 - 2026-08-15

### Added

- Split `report.md`: full per-finding bodies now write to `findings/<ID>.md`, and the
  Markdown report renders a slim, risk-ordered **Detail** link list instead of inlining
  every finding's full body (`write_finding_details`, ISSUE-009).

## 1.9.5 - 2026-08-15

### Fixed

- A `needs_follow_up` coverage-ledger surface now carries a non-empty `reason` and
  `next_step`; `validate_coverage_ledger` rejects one missing either, and `render_markdown`
  renders both columns.

## 1.9.4 - 2026-08-15

### Fixed

- Prefilter candidate ids are now class-prefixed and numbered per class
  (`C-SQLI-0001`, `C-XSS-0001`, ...) instead of one global `C-0001..` sequence, so ids carry
  the attack class and never collide across rulesets (ISSUE-013).

## 1.9.3 - 2026-08-15

### Fixed

- The triage table's `what` column now trims a long title to a word boundary with a trailing
  `…` instead of cutting mid-word at a fixed 80-character slice (ISSUE-011).

## 1.9.2 - 2026-08-15

### Fixed

- The report's bottom-line `Confirmed:` line now renders counts in words (e.g. `"1 critical, 1
  high, 2 medium, 1 low"`) instead of an ambiguous digit ratio (`"1/1/2/1"`) (ISSUE-010).

## 1.9.1 - 2026-08-15

### Fixed

- `render_finding`'s §4 Impact now renders the finding's real `impact` text instead of a
  boilerplate sentence. Deleted the constant §6 Confirmed Attack Scenario and §8 Testing
  sections — both always emitted the same fixed prose regardless of the finding, misleadingly
  labelled `full` tier (ISSUE-052).

## 1.9.0 - 2026-08-15

### Added

- `Finding.impact: str = ""` — the concrete consequence of exploitation, rendered as the
  report's Impact section. `findings_gate.validate_findings` now rejects a `SHIPPING_STATUSES`
  finding (`confirmed`/`fixed`/`needs-deployment-testing`) whose `impact` is blank; non-shipping
  findings may stay blank. `references/finding.schema.json` gained the matching `impact` property
  (not in `required`).

## 1.8.3 - 2026-08-15

### Fixed

- `route_control.py`'s control and entrypoint coverage-gap matching is word-bounded (alphanumeric-
  neighbor guard), not substring, so a token that is part of a longer word (`auth` inside
  `authorization`) is no longer treated as covered and the gap is no longer suppressed.

## 1.8.2 - 2026-08-15

### Added

- Regression pins in `test_wiring.py` for four already-wired items: `reconcile_plan(` and
  `unrouted_candidate_classes(`/`unrouted_triage_dispatch(` in `driver.py`, `render_fp_feedback`
  keying on `fingerprint`, and `run_deterministic_phase` halting on a missing output artifact
  (ISSUE-017, ISSUE-020, ISSUE-031, ISSUE-033).
- `test_feedback_survives_workspace_rename` in `test_fp_feedback.py`: pins that the fingerprint-
  keyed false-positive feedback body is identical across a workspace rename (ISSUE-033).

## 1.8.1 - 2026-08-15

### Fixed

- `render_plan` now renders `discriminate`'s `"unrunnable"` bucket as its own plan section
  (`## Unrunnable preconditions (payload not traceable)`), and folds its `open_questions` into
  "Questions to ask"; `write_plan`'s returned summary carries an `"unrunnable"` count. Previously
  these above-bar needs-runtime findings vanished from `redteam-plan.md` and the summary entirely
  once `payload_runnable` routed them out of `needs_runtime` (ISSUE-056).

## 1.8.0 - 2026-08-15

### Added

- `sec_overlay.redteam.payload_runnable(f)` gates red-team payloads on reachability: a needs-
  runtime finding above the confidence bar now reaches the manual test plan only if it carries a
  non-empty `dataflow` trace or a `reachability` dict with `reachable is True`; otherwise it
  routes to a new `discriminate()` `"unrunnable"` bucket instead of a live directive (ISSUE-056).
  `agents/redteam.md` now requires the producer to trace each payload source→sink through the
  target's own input validation before shipping it as a live test.

## 1.7.3 - 2026-08-15

### Added

- `test_every_codeql_finding_carries_receipt` regression test in `sec_overlay.codeql` to pin that
  every parsed CodeQL finding carries a `codeql:<rule_id>` evidence source at parse time. Confirms
  the receipt mechanism is working (ISSUE-004).

## 1.7.2 - 2026-08-15

### Fixed

- `dedupe_findings()` now collapses two active findings sharing `(file, line, cls)` even when
  both have empty `dataflow` and differ only in message wording (ISSUE-042).
- `correlate/edges.py`'s `_RECURRENCE_STATUSES` is now `evidence.SHIPPING_STATUSES` instead of a
  separate literal, so the shipping-status set is defined once (ISSUE-005).

## 1.7.1 - 2026-08-15

### Fixed

- `run_semgrep()` excludes `.sec-overlay`, `.git`, `.venv`, and `node_modules` directories from scans via `--no-git-ignore` flag. Prevents audit sidecar findings on the harness's own output (ISSUE-032).

## 1.7.0 - 2026-08-15

### Added

- `sec_overlay.class_ext`: `class_extension_status()` checks which investigate/patch extension
  files exist; absent classes are logged as gaps so coverage is never silent. Uses an alias map
  (e.g., sqli/cmdi/xss → injection.md) to count coarse files (ISSUE-037, ISSUE-049).

## 1.6.0 - 2026-08-15

### Added

- `recon.md`, `architecture.md`, and `threat-model.md` each gained one additive instruction so
  their output matches `sec_overlay.route_control`'s checks: recon emits a `route_summary`
  field, architecture names every control by key, and threat-model keeps every entrypoint
  listed before its hunt-list prioritization (ISSUE-027, ISSUE-029, ISSUE-036).

## 1.5.0 - 2026-08-15

### Added

- `sec_overlay.route_control`: derives one route-to-control table from `kb/scan-profile.json`
  and checks recon, architecture, and threat-model output against it. A missing route, control,
  or entrypoint is logged as a `needs_follow_up` gap (`reason` + `next_step`), never dropped;
  `record_route_gaps` appends gaps into `kb/coverage-ledger.json` (ISSUE-027, ISSUE-029,
  ISSUE-036).

## 1.4.0 - 2026-08-15

### Added

- `validate_citations()` in `sec_overlay.findings_gate` to reject any shipping finding whose
  `file:line` citation does not resolve against the target source, reusing
  `phase_gate.resolve_ref`; wired into the driver's findings-gate phase alongside
  `validate_findings` (ISSUE-018, ISSUE-019, ISSUE-023). Control findings from
  `context.control_findings` inherit the check since they flow through the same gate.

## 1.3.0 - 2026-08-15

### Added

- `doc_coverage()` in `sec_overlay.context` to compute read/discovered ratio with low-coverage warnings (ISSUE-016).
- `load()` now accepts optional `repo_root` and `scan_scope` parameters to populate `provenance["docs_discovered"]` — wiring is handled by downstream caller (driver/orchestration).

## 1.2.1 - 2026-08-15

### Added

- `EVIDENCE_VOCABULARY` block in `references/prompt-constants.md`: the closed set of receipt
  tiers, shipping statuses, and `runtime_disposition` values, pasted into every agent prompt like
  the other twelve blocks. A drift test in `test_docs_invariants.py` binds the block's listed
  values to `sec_overlay.evidence`'s `TIER1_RECEIPTS`/`TIER2_RECEIPTS`/`SHIPPING_STATUSES`/
  `RUNTIME_DISPOSITIONS` constants so the two cannot drift apart.

## 1.2.0 - 2026-08-15

### Added

- `sec_overlay.prompts.render_prompt(template, subs)` substitutes `{{KEY}}` tokens and raises
  `ValueError` naming every unfilled `{{TOKEN}}` — closes the class of bug where a hand-substituted
  agent prompt shipped a literal `{{ATTACK_CLASS}}` to a model. `skills/sec-overlay/CLAUDE.md` §2
  now instructs the orchestrator to render every agent dispatch prompt through it.

## 1.1.0 - 2026-08-15

### Added

- Recon gate: `phase_gate.attack_surface_gate` rejects an `attack_surface` key whose evidence
  refs are absent, unresolved, or resolve only to comment lines — a comment is a claim about
  code, not proof it executes (ISSUE-026).

## 1.0.4 - 2026-08-15

### Fixed

- `scan-profile.schema.json` gains `attack_surface_evidence` (required) and `subsystems`
  (optional), matching the two `ScanProfile` fields recon already writes.

## 1.0.3 - 2026-08-15

### Fixed

- `phase_gate._parse_ref` now anchors a citation with a leading-match regex instead of
  `rsplit(":", 1)`, so a trailing human hint after the line or range (`foo.py:42 in the
  handler`) is stripped instead of failing the ref to resolve (ISSUE-024/028).

## 1.0.2 - 2026-08-15

### Fixed

- `redteam._above_bar` is now coverage-first: a critical/high/medium finding above the risk
  floor earns a manual test directive regardless of receipt strength — a missing tool
  receipt no longer withholds the test that would settle it. The dead
  `redteam:prime-manual-test` history branch (no producer wrote that event) is removed.

## 1.0.1 - 2026-08-15

### Fixed

- `selfscore.build_self_score` gained a `shipping` count over the full `evidence.SHIPPING_STATUSES`
  set (`confirmed`/`fixed`/`needs-deployment-testing`), alongside the existing narrower `reported`
  count. `factcheck.md` now targets ONE shipping-status finding rather than narrowly `confirmed`.

## 1.0.0 - 2026-08-15

### Changed

- **Breaking:** the findings gate now requires a Tier-1 tool receipt (codeql/semgrep/sca/
  secrets) for any `confirmed`/`fixed` finding. A Tier-2-only receipt (ripgrep/ast-grep/
  structural-index/tree-sitter) — previously enough to confirm a finding on
  SAST-unsupported languages — now fails the gate and must route to
  `needs-deployment-testing` instead. The gate also stamps `Finding.receipt_tier` and
  rejects any `runtime_disposition` value outside the shared enum. `_act_findings_gate`
  now raises `PhaseHalt` when the gate reports errors, instead of validating silently.

### BREAKING CHANGE

Any pipeline consumer treating `confirmed`/`fixed` as ground truth for a ripgrep-only
finding must re-triage it as `needs-deployment-testing` — a manual test directive, not
an automatic confirmation.

## 0.12.0 - 2026-08-15

### Added

- `Finding` gains a derived `receipt_tier: int | None` field, round-tripped by `to_dict`/
  `from_dict` and declared in `finding.schema.json` (optional, not required). Task 3 stamps
  the value; this task only adds it to the shared vocabulary.

## 0.11.0 - 2026-08-15

### Added

- `evidence.py` exports a shared receipt-tier and status vocabulary: `TIER1_RECEIPTS`/
  `TIER2_RECEIPTS` (partitioning `_MECHANICAL` into confirms-alone vs locates-only sources),
  `SHIPPING_STATUSES`, `RUNTIME_DISPOSITIONS`, and the `receipt_tier()`/`confirms_alone()`
  predicates, giving later modules one source of truth for whether a source can confirm a finding
  alone.

## 0.10.1 - 2026-08-15

### Fixed

- The `audit` CLI no longer calls `begin_pass` on every invocation (C1). It was wiping
  `state.stages` and bumping `pass_number` on each re-invocation, livelocking the six
  `findings_dir`-in/out agent phases (investigate, critic, judge, validate, trace, patch) that
  rely on the orchestrator's manual `record_stage` between calls. Pass lifecycle is now owned
  solely by the campaign supervisor, matching the `scan` path.
- `run_audit`'s investigate/patch branch now raises `PhaseHalt` instead of crashing with
  `FileNotFoundError`/`JSONDecodeError` when `kb/scan-profile.json` is absent or malformed.

## 0.10.0 - 2026-08-15

### Added

- `run_audit` passes the reconciled attack-class set to the `patch` phase's dispatch, matching `investigate` (ISSUE-050). A multi-class run's patch dispatch previously fell through to the classless `render_dispatch(phase, ctx)` call and carried no `{{ATTACK_CLASS}}` line at all.

### Fixed

- Corrected the `begin_pass` signature and increment condition in `SKILL.md` and `CLAUDE.md` (ISSUE-002): `begin_pass(ws: Workspace, sha: str | None) -> CampaignState`, incrementing the pass counter only after a prior pass recorded a stage.

## 0.9.0 - 2026-08-15

### Added

- Wire `redactor.safe_for_prompt` and `factcheck.apply_verdict` into the driver (ISSUE-047, ISSUE-051). `render_dispatch` now passes its composed block through `safe_for_prompt` before returning, so no agent dispatch can carry a high-confidence secret. A new deterministic `factcheck` phase between `trace` and `calibrate` applies verdicts from an optional `kb/verdicts.json`, no-oping silently until Plan B's fact-check agent writes one.

## 0.8.0 - 2026-08-15

### Added

- `verify_findings` now routes a `static-only` re-verify to `needs-deployment-testing` instead of leaving the finding `confirmed` (ISSUE-053) — a finding `verify` cannot dynamically confirm no longer implies a dynamic check passed. `verified-static` still promotes to `fixed`; `not-fixed`/`verify-error` are unchanged.

## 0.7.0 - 2026-08-15

### Added

- Add `sec_overlay.driver.unrouted_triage_dispatch`: a general-triage dispatch block naming any candidate class `agents_to_spawn` doesn't route (e.g. `security-other`), with its candidate count, or `None` when every class is routed.
- Widen `render_dispatch` with an optional `classes=` kwarg, emitting a `{{ATTACK_CLASS}}` line for the investigate phase's reconciled attack-class list.
- `run_audit`'s `investigate`-phase dispatch now reconciles `agents_to_spawn` via `partition.reconcile_plan` (recon-omitted classes) and appends `unrouted_triage_dispatch`'s block after the investigate dispatch when a class remains unrouted.

### Fixed

- `render_dispatch` now raises `ValueError` when called on a deterministic phase (`prompt is None`) instead of printing `agents/None.md`.

## 0.6.0 - 2026-08-15

### Added

- Add `sec_overlay.driver.run_audit`: the resumable table-walker that runs deterministic phases in place, auto-advances agent phases only on a distinct (non-shared) output, and returns the next dispatch or `"AUDIT COMPLETE"`.
- Register `DETERMINISTIC_ACTIONS` for `prefilter`, `findings-gate`, `dedupe`, `calibrate`, `verify`, `demote-noise`, `report`, and `selfscore`.
- Add the `audit` CLI subcommand (`python -m sec_overlay.cli audit --target <T> --config <rules>`).

## 0.5.0 - 2026-08-15

### Added

- Add `sec_overlay.driver.render_dispatch`: a deterministic, side-effect-free printer that names an agent phase's `agents/<prompt>` file and the `{{TARGET}}`/`{{WORKSPACE}}`/`{{SHA}}` substitutions the orchestrator must apply.

## 0.4.0 - 2026-08-15

### Added

- Add `sec_overlay.driver`: `run_deterministic_phase` gates a `PhaseSpec` on inputs/outputs, runs its registered `DETERMINISTIC_ACTIONS` entry, and records the stage — raising `PhaseHalt` when an input or output artifact is missing.

## 0.3.0 - 2026-08-15

### Added

- Add `sec_overlay.phases`: a frozen, ordered `PhaseSpec` table (`PHASE_TABLE`) and pure sequencer helpers (`missing_inputs`, `outputs_present`, `next_actionable_phase`) for the audit driver.

## 0.2.1 - 2026-08-14

### Changed

- Split the plugin documentation by audience: maintainer manual at the plugin root, trimmed skill CLAUDE.md focused on running the harness, and a SKILL.md pointer to it.
- Fix the README quick-start command to `cd` into `skills/sec-overlay/helpers` (the README sits at the plugin root, not inside `helpers`), and note the `${CLAUDE_PLUGIN_ROOT}` path for an installed plugin.

## 0.2.0 - 2026-08-12

### Changed

- Default SARIF output to suppressed-full and populate driver.rules.

### Added

- Add systemic finding clustering, per-run self-score, and run-economics report section.
- Add external-boundary disposition: risk cap, ingested-package scope check, lead bucket.

## 0.1.0 - 2026-08-11

### Added

- Initial release: agentic security-audit harness (SAST prefilter, multi-agent gate ladder, SARIF + Markdown reports).
