# Changelog

This file follows the [Common Changelog](https://common-changelog.org) format.

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
