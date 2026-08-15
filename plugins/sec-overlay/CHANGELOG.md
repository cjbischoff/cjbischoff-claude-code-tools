# Changelog

This file follows the [Common Changelog](https://common-changelog.org) format.

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
