# Changelog

This file follows the [Common Changelog](https://common-changelog.org) format:

- One `## <version> - <YYYY-MM-DD>` section per release, newest first.
- Entries are grouped under `### Changed`, `### Added`, `### Removed`, `### Fixed` — in that order.
- Each entry is one sentence in the imperative mood, describing the change from the user's point of view.
- Every commit that changes a tracked file adds an entry here in the same commit.

## Unreleased

### Added

- Populate SARIF `driver.rules` from the finding set, de-duplicated by `rule_id`, with `cls` as the rule name and ASVS/CodeGuard ids as properties.
- Instruct the trace agent to set `reachability.blocker = "external-boundary"` when a sink resolves into a dependency outside the ingested set, and instruct the validate agent to never promote such a finding to `confirmed`.
- Add the design spec for four sec-overlay improvements from the lumedeodorant review: per-stage token accounting with a run self-score, systemic finding clustering, an external-boundary confidence disposition, and SARIF completeness.
- Add the task-by-task TDD implementation plan for the four sec-overlay improvements (build order I3, I1, I2, I4).
- Add a "Run economics" report section (token totals by phase and model, plus a USD estimate) backed by `cost.aggregate_by_model`.
- Add `cluster_id` and `affected_sites` fields to `Finding` and the finding schema.
- Add `sec_overlay.cluster`, a deterministic pass that groups ≥3 same-class, same-sink `raw` findings into one systemic cluster before the critic/gate ladder.
- Add `sec_overlay.selfscore`, a per-run finding-status score persisted to `state.budget`.
- Document token proxy fallback and self-score call in the sec-overlay SKILL orchestration (cost recording when harness token reporting is ambiguous; per-run self-score persisted to state for next-run calibration).
- Add `report.collapse_clusters`, which reduces each systemic cluster to one representative finding (un-clustered findings pass through unchanged) applied to both the confirmed and needs-runtime report buckets.
- Add an "Affected sites" table to the needs-runtime finding view, listing every member of a collapsed cluster.
- Add `sec_overlay.scope`, an ingested-package boundary check (`is_external_package`) reading `kb/scan-scope.json`, so a sink resolving into an un-ingested dependency can be flagged without inventing a boundary when no manifest exists.
- Cap calibrated `risk_score` at 3 and set `completeness_tier` to `external-unverifiable` for findings whose `reachability.blocker` is `external-boundary`, so they can never present as a confirmed medium.
- Render findings stamped `completeness_tier == "external-unverifiable"` in their own report section, "Leads — pending external-dependency verification", separate from the source-provable needs-runtime bucket.

## 0.1.0 - 2026-08-11

### Changed

- Rewrite the root README to the marketplace template (Installation, Plugins, Development, Governance, License) and collapse the per-task Status log.
- Refocus the sec-overlay skill CLAUDE.md on repo mechanics: real git/governance section, the correct 2 env-only failure count, and the prek folder-README hook.
- Extend the pre-commit hook to require a folder's README.md whenever files in that folder change, with a Bash invocation test.

### Added

- Scaffold the plugin marketplace manifest and the sec-overlay plugin (v0.1.0) with a placeholder skill script.
- Add commit governance: Conventional Commits check, main-branch block, and forced README/CHANGELOG updates via prek hooks.
- Add the design spec for porting the sec-harness skill into the sec-overlay plugin.
- Add the implementation plan for the sec-overlay port and extend the rename scope to the HARNESS_ROOT and SEC_HARNESS_HOME tokens.
- Add the design spec for incorporating upstream's KB doc/diagram redesign into the sec-overlay plugin.
- Add the design spec for the sec-overlay documentation overhaul.
- Add the implementation plan for the KB doc/diagram redesign port.
- Add the implementation plan for the sec-overlay documentation overhaul.
- Import the sec-harness skill source tree into the sec-overlay plugin (semgrep submodule excluded).
- Rename the ported identifiers to sec-overlay: the `sec_overlay` Python package, the `sec-overlay` distribution name, and the `SEC_OVERLAY_HOME` and `OVERLAY_ROOT` tokens.
- Point the SKILL.md run instructions at `${CLAUDE_PLUGIN_ROOT}` and document the semgrep ruleset as a prerequisite (the semgrep-rules submodule is not shipped).
- Verify the rename preserved behavior: 552 tests pass; the two failures are environment-only (gitignored bench corpus, excluded semgrep submodule), not rename regressions.
- Update sec-overlay manifest descriptions to the agentic security-audit harness.
- Add the DIAGRAM_STYLE, FIELD_OWNERSHIP, and QUALIFIER_PROOF prompt-constants blocks.
- Add the `open_questions` field to `Finding` and the finding schema.
- Flag comment-only `file:line` citations in the phase gate as a scrutiny note.
- Add the `deployment_config` context kind, `deployed_in` tag, and `Context.diagram` slot rendered into `CONTEXT.md`.
- Render a Questions-to-ask section in the red-team plan and wire the diagram/field-ownership/qualifier guidance and deployment-config lens into the agent prompts.
- Add per-folder READMEs for agents/classes, references/asvs, references/codeguard, references/hunting, helpers/sec_overlay, and helpers/tests.

### Removed

- Remove stale Go-rewrite prose from the four live sec-overlay docs.

### Fixed

- Prevent the report renderer from crashing when a red-team agent writes `runtime_test.expected_signal` as a bare string; the report and red-team renderers now share one tolerant helper and the finding schema validates the `runtime_test` inner shape.
- Reject placeholder-version deps bumps and stop `verify_findings` from overriding a `validate-fix` not-fixed verdict.
- Document the `open_questions` field in the `finding.schema.json` reference table and correct the sec-overlay `CLAUDE.md` prompt-constants block counts (§6 and §8) from six and nine to twelve.
- Correct the sec-overlay README and helpers/README test counts to 575 tests / 2 env-only failures and verify the diagrams and worked example against the current pipeline.
- Clean up the hook test's temporary repos with an EXIT trap so no `mktemp` directories are left behind.
- Rename the sec-overlay overview architecture diagram's subgraph id from `HARNESS` to `OVERLAY` (rendered label unchanged).
