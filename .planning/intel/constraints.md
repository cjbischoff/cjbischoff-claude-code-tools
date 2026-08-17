# Constraints (from SPEC-classified docs)

30 SPEC-classified documents. Paths are relative to the repository root.
Entries appear in date order. Where later specs supersede earlier ones on the same
scope, the resolution is recorded in `.planning/INGEST-CONFLICTS.md` (INFO bucket);
both entries are preserved here for provenance.

Recurring hard invariants (stated verbatim across many specs below):
stdlib-only core (no new runtime dependency in `pyproject.toml`); frozen JSON contract
(`helpers/sec_overlay/models.py` and `helpers/sec_overlay/evidence.py` must not change —
byte-mirrored by a parallel Go port); `fingerprint()` identity unchanged; line length 100;
absolute imports; TDD failing-test-first; stage explicit paths only, never `git add -A`.

## Analysis Artifacts + Shared Evidence Substrate (design)
- source: plugins/sec-overlay/skills/sec-overlay/docs/plans/2026-08-02-artifact-substrate-design.md
- type: schema
- content: Status "Approved design (pre-implementation)". Defines a shared evidence
  substrate (`kb/graph.json`) with structural_index and reachability queries, plus gated
  human deliverables: C4 security-design doc, threat model
  (Application/Deployment/Build), attack-surface analysis, attack tree, and a
  draft/refine/reconcile artifact lifecycle with phase gates and adversarial review.
  Section 9 lists open questions — not fully settled. NOTE: its artifact layout
  (kb/architecture.md, kb/THREAT_MODEL.md) is superseded outright by the 2026-08-16
  architecture/threat-model standards design (ruling R3).

## Cluster C — Phase-Adversary Gate Wiring
- source: plugins/sec-overlay/skills/sec-overlay/docs/plans/2026-08-02-clusterC-gate-wiring.md
- type: api-contract
- content: `GateDecision` carries claim `text` + `refs`; `build_gate_record` adds a
  `claims` map (`id -> {text, refs}`); extractors `claims_from_profile` /
  `claims_from_context` produce `{id, text, refs}` claim lists. Backward compatible:
  existing callers of `build_gate_record`/`run_phase_checks` keep working.

## Cluster D — needs-runtime Status Flow
- source: plugins/sec-overlay/skills/sec-overlay/docs/plans/2026-08-02-clusterD-runtime-flow.md
- type: api-contract
- content: `Finding.runtime_dependent: bool` marker; deterministic
  `campaign.promote_runtime_dependent(ws)` promotes marked findings to
  `needs-deployment-testing`. Promotion is non-destructive and recall-safe: it affects
  only findings explicitly marked `runtime_dependent`.

## Cluster E — Coverage Accounting
- source: plugins/sec-overlay/skills/sec-overlay/docs/plans/2026-08-02-clusterE-coverage.md
- type: schema
- content: `coverage.py` computes per-language `{files, tier}` deterministically from
  `profile.languages` + `backends_run` + `profile.sast_plan`; persisted to
  `kb/coverage.json`; report renders a "Coverage & limitations" section. Invariant:
  `partition.must_investigate(profile)` — investigate runs even at 0 candidates.

## Evidence Substrate (kb/graph.json) Implementation Plan
- source: plugins/sec-overlay/skills/sec-overlay/docs/plans/2026-08-02-evidence-substrate-plan.md
- type: schema
- content: Versioned `kb/graph.json` data contract with two tiers: Tier-1 (LLM-free,
  pre-recon; positive corroboration and navigation only) and Tier-2 (post-prefilter
  CodeQL/semgrep taint merge). Query API: `reaches`, `attacker_controls`, `no_path`,
  `is_unresolvable`. Honesty gate (Decision 1 = B): the `structural-index:no-path`
  receipt is mintable ONLY when Tier-2 taint coverage exists for the sink's language;
  Tier-1 alone can never assert no-path.

## GSD — signal-over-noise correctness fixes
- source: plugins/sec-overlay/skills/sec-overlay/docs/gsd/2026-08-02-signal-over-noise-fixes.md
- type: nfr
- content: Status "design (approved direction)" with a close-out noting all clusters
  landed. Guiding principle (load-bearing NFR): "the harness must never mislead a
  security engineer about what is most important or what was covered" — a confirmed
  critical ranks critical, a clean scan states its coverage denominator, a runtime-only
  finding reaches the test plan. Umbrella for fix clusters A-G.

## Codex-security feature port (design spec)
- source: plugins/sec-overlay/skills/sec-overlay/docs/plans/2026-08-03-codex-feature-port-design.md
- type: api-contract
- content: Status "Approved for planning". Six additive mechanisms ported natively from
  @openai/codex-security: fingerprints, FP feedback loop, discovery saturation,
  validation guidance, coverage ledger, cost tracking. All additive — no existing
  behavior removed; frozen JSON contract untouched.

## Instrumented dogfooding run (design spec)
- source: plugins/sec-overlay/skills/sec-overlay/docs/dogfooding/2026-08-03-dogfooding-run-design.md
- type: protocol
- content: Status "Approved (via clarifying-question round)". Execution contract for an
  instrumented dogfooding pass over three target repos: real audit artifacts per repo
  (threat model, findings JSON, SARIF, report, redteam plan) plus a runtime-issues
  report with per-phase watch checklist, issue taxonomy, and fix gates. Historical —
  run completed (see runtime-issues_20260803.md in context.md).

## QA Batched-Fixes Implementation Plan
- source: plugins/sec-overlay/skills/sec-overlay/docs/superpowers/plans/2026-08-03-qa-batched-fixes.md
- type: api-contract
- content: Closes 22 batched QA issues from the 3-run dogfood. Binding constraints:
  Go-safe absolute (never edit models.py/evidence.py, no enum/whitelist changes);
  `fingerprint()` identity (`rule_id|cls|enclosing-symbol`) mirrored by Go — dedupe fixes
  use grouping keys inside dedupe.py only; agent-prompt hard rules preserved verbatim
  (model-family diversity, tool-receipt safety contract, count-invariant verdict tables,
  OUTPUT_WRITE_FALLBACK import lines).

## Cross-repo correlation — feature design (seed)
- source: plugins/sec-overlay/skills/sec-overlay/docs/plans/2026-08-07-cross-repo-correlation-design.md
- type: schema
- content: Status "design". Seed design for cross-repo correlation: correlation
  workspace, cross-repo edge model `{type, from, to, evidence, confidence}`,
  contract-consistency checks, monorepo dedupe, correlation report, cross-repo SARIF.
  SUPERSEDED/EXPANDED by Spec B (2026-08-08-cross-repo-correlation-spec.md, declared in
  that doc's header).

## Process Review & Pipeline Hardening (Spec A)
- source: plugins/sec-overlay/skills/sec-overlay/docs/plans/2026-08-07-process-review-hardening-design.md
- type: nfr
- content: Status "design (approved for spec write; awaiting user review)". Single-repo
  pipeline success criteria: (1) correct on monorepo sub-service scans — no path-base
  failures; (2) honest scoring — every finding is source-confirmed with a mechanical
  receipt or needs-deployment-testing with a real risk_score; (3) strict gates —
  schema-type and evidence-whitelist violations FAIL, never warn-and-pass; (4) complete
  coverage — a scan cannot present as clean while an attack-surface class has no finding
  and no logged coverage hole. Parent of the three Spec A plans below.

## Reporting Completeness + Methodology Knobs (Spec A Plan 3)
- source: plugins/sec-overlay/skills/sec-overlay/docs/superpowers/plans/2026-08-07-reporting-and-methodology.md
- type: schema
- content: `coverage_ledger.build_coverage_ledger(ws)` derives surfaces from
  attack_surface x finding status, writes `kb/coverage-ledger.json`; `write_report` adds
  NDT findings to findings.json; `ScanProfile` gains a validated `scan_options` dict
  (adversary_depth, model_tier_map, wave sizing, token budget). Invariants: "gaps
  logged, never silently dropped"; `adversary_depth` never bypasses the tool-receipt
  confirmation bar; model-family diversity is a hard invariant, not a knob.

## ScanScope Spine + Path/Identity (Spec A Plan 1)
- source: plugins/sec-overlay/skills/sec-overlay/docs/superpowers/plans/2026-08-07-scanscope-and-path-identity.md
- type: schema
- content: `sec_overlay/scanscope.py` resolves canonical `repo_root` (git top-level) +
  `scan_scope`, persisted as `kb/scan-scope.json` (NOT on frozen CampaignState).
  `repo_slug`, `discover_context_files`, `claims_from_markdown` become scope-aware.
  Token contract: `{{REPO_ROOT}}`/`{{SCAN_SCOPE}}`; citations are repo-root-relative.

## Correlation Core (Spec B B-Plan 1)
- source: plugins/sec-overlay/skills/sec-overlay/docs/superpowers/plans/2026-08-08-correlation-core.md
- type: api-contract
- content: Stdlib-only `sec_overlay.correlate` package: product manifest
  (Member/Manifest), CorrelationWorkspace, read-only ingest of N per-repo sidecars,
  member key `<slug>#<scan_scope>`, two deterministic joins (shared-dependency roll-up,
  same-class recurrence) written to `edges.json` via a `correlate` CLI. Immutability
  invariant: the correlation layer opens NO member-repo file for write; member sidecars
  are byte-identical before and after a run (test-asserted). Deterministic only — no
  LLM, no network, no member-source access in B-Plan 1.

## Spec B — Multi-Repo Holistic Correlation
- source: plugins/sec-overlay/skills/sec-overlay/docs/plans/2026-08-08-cross-repo-correlation-spec.md
- type: api-contract
- content: Status "design (approved; awaiting user review before writing-plans)".
  Header declares "Supersedes/expands: docs/plans/2026-08-07-cross-repo-correlation-design.md".
  Read-only correlation layer over N per-repo scans: edge graph (edges.json),
  re-thresholding engine (verdicts.json), cross-repo adversary gate, combined artifacts
  (ARCHITECTURE.md, THREAT_MODEL.md, REDTEAM.md, FINDINGS.md), cross-repo SARIF.
  Depends on Spec A Plans 1 and 3. Out of scope: re-scanning members, write-back,
  models.py/evidence.py changes.

## Report Readability — Design Spec
- source: plugins/sec-overlay/skills/sec-overlay/docs/superpowers/specs/2026-08-08-report-readability-design.md
- type: api-contract
- content: Status "design (approved; awaiting user review before writing-plans)".
  Presentation-layer only: report.md gains a triage layer (headline counts must not
  count confirmed-only while NDT leads exist), finding-template gains NDT-view and
  dep-view routes, redteam-plan serializer replaces raw Python repr with markdown.
  NOTE: the 2026-08-15 defect-remediation design later reworks report rendering (report
  split + per-finding detail); recency resolution recorded in the conflicts report.

## Re-thresholding Engine + Cross-Repo Edges (Spec B B-Plan 2)
- source: plugins/sec-overlay/skills/sec-overlay/docs/superpowers/plans/2026-08-08-rethreshold-engine.md
- type: protocol
- content: `rethreshold` is a pure function over (ingested findings, edges, per-member
  coverage-ledgers) -> CorrelationVerdict[]. Promotion discipline (load-bearing): a
  verdict reaches correlated_status="confirmed" ONLY when the resolving edge is a
  deterministic join AND the resolving member supplies a mechanical signal the barrier
  is absent; an llm-join edge may demote/weaken, never promote. Base status is always
  preserved beside the correlated status. Sources immutable (read-only, test-asserted).

## Port sec-harness into the sec-overlay plugin (design)
- source: docs/superpowers/specs/2026-08-11-port-sec-overlay-design.md
- type: protocol
- content: Status "approved (design), pending spec review". Port rules: rename
  `sec-harness`/`sec_harness` -> `sec-overlay`/`sec_overlay` throughout; plugin path
  adaptation via CLAUDE_PLUGIN_ROOT; semgrep submodule handling; verification gates
  (pytest, ruff, ty, `claude plugin validate`). Historical — the port shipped (the
  plugin exists at plugins/sec-overlay/).

## sec-overlay Documentation Overhaul — Design
- source: docs/superpowers/specs/2026-08-11-sec-overlay-doc-overhaul-design.md
- type: nfr
- content: Status "Approved (design); pending spec review before plan". Doc standards:
  remove stale Go-rewrite prose, root marketplace README on a fixed template, skill
  CLAUDE.md focused on repo mechanics, per-folder READMEs, pre-commit hook
  README-freshness check. Non-goals: no Python behavior change, no edits to archival
  planning docs, no plugin version bump.

## Incorporate sec-harness KB doc/diagram redesign (design)
- source: docs/superpowers/specs/2026-08-11-sec-overlay-kb-redesign-design.md
- type: protocol
- content: Status "Approved for implementation". Port the upstream 19-commit "KB
  doc/diagram redesign" series for feature parity, across six commits. Hard rule:
  preserve the local-only `render_util` / `expected_signal`-object divergence — do not
  overwrite it. NOTE: cross_refs in the classification are truncated
  ("2026-08-09-...") — an upstream-referenced spec is not in this ingest set (see
  conflicts report WARNING).

## sec-overlay improvements from the lumedeodorant review (design)
- source: docs/superpowers/specs/2026-08-12-sec-overlay-review-improvements-design.md
- type: api-contract
- content: Status "Approved for implementation". Four improvements in build order I3 ->
  I1 -> I2 -> I4: per-stage token accounting + run self-score (cost.py), systemic
  finding clustering (dedupe/cluster), external-boundary confidence disposition
  (calibrate.py), SARIF completeness with rule metadata and suppressed leads.

## sec-overlay Review-Improvements Implementation Plan
- source: docs/superpowers/plans/2026-08-12-sec-overlay-review-improvements.md
- type: api-contract
- content: Implements the 2026-08-12 design. Contract constraints: new deterministic
  passes are no-LLM modules with their own CLI following the dedupe.py/calibrate.py
  shape; Finding contract changes are additive and nullable only (like duplicate_of);
  absolute imports; <=100-line functions; <=8 cyclomatic complexity.

## Marketplace documentation structure — design
- source: docs/superpowers/specs/2026-08-14-marketplace-doc-structure-design.md
- type: protocol
- content: Status "approved by user (interview 2026-08-14)". Doc-structure contract:
  root CLAUDE.md governs marketplace development; each plugin carries its own maintainer
  CLAUDE.md, user README.md, and CHANGELOG.md; no governance rule stated in more than
  one place. Verified fact: a plugin-root CLAUDE.md never auto-loads for installers —
  plugins contribute context through skills, agents, and hooks only.

## sec-overlay audit driver (Plan A)
- source: docs/superpowers/plans/2026-08-15-sec-overlay-audit-driver.md
- type: api-contract
- content: Deterministic `sec_overlay.cli audit` phase-driver: frozen phase table
  (phases.py) declaring per-phase kind, input/output artifacts, and prompt file; a
  stdlib sequencer (driver.py) that gates advancement on artifact preconditions, halts
  loudly on missing output, prints the next agent dispatch, and is resumable. The driver
  never calls a model; it replaces the SKILL.md prose ladder as the authority on
  within-run sequencing. Plan A of four under the defect-remediation spec (theme T1).

## sec-overlay defect remediation — design
- source: docs/superpowers/specs/2026-08-15-sec-overlay-defect-remediation-design.md
- type: nfr
- content: Status "Draft for user review". Corrects 57 audited defects (ISSUE-001..057
  from the agent-gateway run) across seven themes plus a new artifact-review phase.
  Outcome bar: complete coverage with accurate findings (a finding a human acts on is
  dataflow-proven or marked for live test — never confirmed on a syntactic match alone);
  artifacts an engineer can act on, reviewed by a final independent agent before the run
  ends. Parent spec of the T-theme plans (audit-driver, shared-vocab, coverage-accuracy,
  report-telemetry).

## sec-overlay shared vocabularies (T2 + T3)
- source: docs/superpowers/plans/2026-08-15-sec-overlay-shared-vocab.md
- type: schema
- content: One shared reference parser and one shared status/receipt vocabulary for
  every gate, filter, red-team bar, and self-score. Receipt tiers derived from evidence;
  the receipt gate revokes tier-2-only confirmation (a Tier-2-only finding must not
  reach `confirmed` — security-fix TDD order). Deterministic gate proves a reference
  resolves; meaning stays the opus adversary's job. Load-bearing prompt strings
  preserved verbatim ({{FP_FEEDBACK}}, proof-tuple/anti-collapse strings).

## Architecture Documentation + Threat Model Standards — Design Spec
- source: docs/superpowers/specs/2026-08-16-architecture-threat-model-standards-design.md
- type: protocol
- content: Implements the source standards spec inside sec-overlay. Binding interview
  rulings: R1 extend sec-overlay (rebuild existing architecture/threat_model phases);
  R2 migrate the whole harness to CVSS v4.0 — one version everywhere, no mixing;
  R3 replace artifact layout outright — `<workspace>/architecture/` and
  `<workspace>/threat-model/` replace kb/architecture.md, kb/entities/*.md, and
  kb/THREAT_MODEL.md, no shims, all consumers re-pointed; R4 agent transforms, gate
  proves (deterministic checker proves element-set derivation, caps, subgraph
  structure). Architecture emits C4 + arc42; threat model emits DFD derived from the
  container diagram, attack sequences derived from runtime sequences, STRIDE findings
  scored CVSS v4.0. Latest authority on these phases.

## Standards Spec: Architecture Documentation + Threat Model Artifacts (source)
- source: docs/superpowers/specs/2026-08-16-architecture-threat-model-standards-source.md
- type: protocol
- content: User-authored standards. Resolved format decisions: Mermaid for all diagram
  types in both artifacts (no draw.io/Structurizr/PlantUML); CVSS v4.0 for the threat
  model findings table, version pinned — do not mix v3.1 and v4.0; no OWASP Threat
  Dragon; Mermaid caps hard-enforced — exceeding a node/edge cap is a generation
  failure, not a warning. Defines notation, structure, ownership boundaries, ADR
  (Nygard) format, STRIDE/PASTA/LINDDUN selection, ASD-STE100 prose standard, and the
  /architecture and /threat-model file structure.

## Diagram + STE Enforcement (Plan 2 of 3)
- source: docs/superpowers/plans/2026-08-16-sec-overlay-diagram-ste-enforcement.md
- type: api-contract
- content: Three stdlib enforcement modules: mermaid_index.py (line-oriented structure
  extraction), diagram_gate.py (caps, labels, provenance, freshness; CLI-callable),
  ste_lint.py (checkable-subset ASD-STE100 rules); artifact_gate.py gains the
  arc42/threat-model duplication check. Hard caps from the source standard: context
  <=10 nodes; container <=15; component <=10; sequence <=6 participants and <=15
  messages; DFD <=12 elements; edge/message labels <=4 words. Derivation header format
  (exact): `%% derived-from: <source-filename> sha256:<64-hex>`.

## Design — a driven invocation path for sec-overlay
- source: docs/superpowers/specs/2026-08-16-sec-overlay-invocation-design.md
- type: api-contract
- content: Status "Design only. Approved 2026-08-16. No plugin file changes until an
  implementation plan is approved." Scope choices: A1 one command (/sec-overlay:audit);
  B1 thin driver module (helpers/sec_overlay/run.py: write_env, receipt, fence);
  C1 receipts + working-tree fence + O-65 redteam-adversary path fix only; D1 inferred
  roles shown at the confirm step. Also gives the existing `sec_overlay.correlate` CLI a
  documented caller and multi-repo CWD output artifacts. Latest authority on invocation;
  layers over the 2026-08-15 audit driver (Plan A).
