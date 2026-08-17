# Context (from DOC-classified docs)

19 DOC-classified documents: dogfooding observation logs and historical implementation
plans. These are execution records / work plans, not standing contracts. Most implement
a SPEC recorded in `constraints.md` (parent spec noted per entry). Paths are relative
to the repository root.

## Dogfooding observation logs

- Runtime-issues log, 2026-08-03 run
  - source: plugins/sec-overlay/skills/sec-overlay/docs/dogfooding/runtime-issues_20260803.md
  - 27 numbered issues with severity, evidence, fixes, and results of three audit runs
    across the sec-overlay pipeline (graph build, context-ingest, recon, phase gates,
    prefilter/clsmap, investigate, dedupe, validate/report, redteam, verify,
    crypto_policy). Proposed fixes were triage candidates, not accepted decisions.
- Run observations, AEM 4-repo campaign, 2026-08-07
  - source: plugins/sec-overlay/skills/sec-overlay/docs/dogfooding/2026-08-07-run-observations.md
  - Live log of correctness bugs, doc drift, efficiency issues, and wins observed while
    dogfooding audit campaigns on four repos. Evidence base for Spec A
    (process-review-hardening) and Spec B (cross-repo correlation).

## Implementation plans — 2026-08-02 signal-over-noise clusters
Parent spec: docs/gsd/2026-08-02-signal-over-noise-fixes.md (constraints.md).

- Cluster A — Prioritization & Risk Correctness
  - source: plugins/sec-overlay/skills/sec-overlay/docs/plans/2026-08-02-clusterA-prioritization.md
  - Fixes risk_score severity inversion via difficulty-weighted precondition caps,
    severity floors, and a disposition-aware red-team action bar. Carries SPEC-like
    invariants: risk_score int in [1,10]; stdlib-only.
- Cluster B — SAST Routing & Noise
  - source: plugins/sec-overlay/skills/sec-overlay/docs/plans/2026-08-02-clusterB-sast-routing.md
  - Adds FindingStatus.INFORMATIONAL, NOISE_CLASSES demotion (partition.demote_noise),
    and partition.reconcile_plan for SAST candidate routing.
- Cluster F / T7 — Calibrate crash on malformed CVSS
  - source: plugins/sec-overlay/skills/sec-overlay/docs/plans/2026-08-02-clusterF-T7-calibrate-crash.md
  - Malformed CVSS vectors fall back to heuristic scoring instead of crashing batch
    calibration (O-029). Written against the CVSS 3.1 engine (cvss31_base) — that
    engine is superseded by the 2026-08-16 CVSS v4.0 migration (see conflicts INFO).
- Cluster G — Report / Plan / Wiring Polish
  - source: plugins/sec-overlay/skills/sec-overlay/docs/plans/2026-08-02-clusterG-polish.md
  - Links redteam-plan in reports, adds a LEAD carrier for non-Finding leads, reconciles
    SKILL/CLAUDE doc ordering.

## Implementation plans — feature ports and adoption

- Codex-Security Feature Port plan
  - source: plugins/sec-overlay/skills/sec-overlay/docs/plans/2026-08-03-codex-feature-port-plan.md
  - Ports six signal/recall mechanisms per the 2026-08-03 design spec without touching
    the frozen Go contract.
- aghast/OpenAnt Adoption plan
  - source: plugins/sec-overlay/skills/sec-overlay/docs/plans/2026-08-04-aghast-openant-adoption-plan.md
  - Implements ADR-2026-08-04 (decisions.md): finding.schema.json validation,
    entry-point detection, custom check bundles, anti-hallucination guard.
- Port sec-harness -> sec-overlay plugin plan
  - source: docs/superpowers/plans/2026-08-11-port-sec-overlay.md
  - Executes the 2026-08-11 port design: identifier rename, SKILL.md path anchors,
    pytest/ruff/ty verification, plugin.json and marketplace.json manifests.
- KB Doc/Diagram Redesign Port plan
  - source: docs/superpowers/plans/2026-08-11-kb-doc-diagram-redesign.md
  - Ports upstream sec-harness KB doc/diagram redesign features (DIAGRAM_STYLE,
    FIELD_OWNERSHIP, QUALIFIER_PROOF prompt blocks; Finding.open_questions; gate and
    verify guards; deployment_config context kind) per the 2026-08-11 kb-redesign
    design.

## Implementation plans — Spec A (process review hardening)
Parent spec: docs/plans/2026-08-07-process-review-hardening-design.md (constraints.md).

- Scoring + Gate Strictness (Plan 2 of 3)
  - source: plugins/sec-overlay/skills/sec-overlay/docs/superpowers/plans/2026-08-07-scoring-and-gate-strictness.md
  - Scores needs-deployment-testing findings, judge-verdict downgrades (judge lowers
    only), deps promotion with reachability, prompt/orchestration guards. Encodes
    invariants: deterministic scoring; frozen models.py/evidence.py contract.

## Implementation plans — report readability

- Report Readability plan
  - source: plugins/sec-overlay/skills/sec-overlay/docs/superpowers/plans/2026-08-08-report-readability.md
  - Implements the 2026-08-08 report-readability design: triage table, NDT view, dep
    view, markdown redteam serializer. Invariants noted: epistemic honesty, determinism.

## Implementation plans — docs and governance

- sec-overlay Documentation Overhaul plan
  - source: docs/superpowers/plans/2026-08-11-sec-overlay-doc-overhaul.md
  - Six tasks: remove stale Go-rewrite prose, fix test counts, add per-folder READMEs,
    generalize the pre-commit README hook. Includes a "Deviations from the approved
    spec" section.
- Marketplace Documentation Structure plan
  - source: docs/superpowers/plans/2026-08-14-marketplace-doc-structure.md
  - Splits marketplace-level vs plugin-level documentation, adds the plugin template
    skeleton, routes prek hook changelog checks. Implements the 2026-08-14 design.

## Implementation plans — defect remediation (2026-08-15 T-themes)
Parent spec: docs/superpowers/specs/2026-08-15-sec-overlay-defect-remediation-design.md.

- Coverage + Accuracy (T4/T5)
  - source: docs/superpowers/plans/2026-08-15-sec-overlay-coverage-accuracy.md
  - Closes 18 issues: route-to-control table (route_control.py), findings_gate citation
    check, class-extension alias map, semgrep prefilter sidecar exclusion, same-line
    dedupe, CodeQL receipt regression, red-team payload reachability, regression pins.
    Contains recorded user "Rulings" as execution constraints.
- Report / Telemetry / Artifact-Review
  - source: docs/superpowers/plans/2026-08-15-sec-overlay-report-telemetry-artifact-review.md
  - Report split with per-finding detail files, per-phase timing/token telemetry
    (cost.py), new artifact_gate phase and artifact-review agent prompt, Finding.impact,
    prefilter candidate ids, coverage ledger, stage validators.

## Implementation plans — architecture/threat-model rebuild (2026-08-16)
Parent specs: architecture-threat-model-standards design + source (constraints.md).

- CVSS v4.0 Migration (Plan 1 of 3)
  - source: docs/superpowers/plans/2026-08-16-sec-overlay-cvss4-migration.md
  - Replaces the CVSS 3.1 scoring engine with a CVSS v4.0 MacroVector engine (cvss.py,
    cvss4_data.py with vendored FIRST lookup data, calibrate.py). Stdlib-only,
    Python 3.13.
- Architecture/Threat-Model Phase Rebuild (Plan 3 of 3)
  - source: docs/superpowers/plans/2026-08-16-sec-overlay-arch-tm-rebuild.md
  - Rebuilds architecture and threat_model phases on C4/arc42 and DFD/STRIDE, wires the
    diagram gate and STE linter, re-points consumers, adds reference files
    (architecture-standards, threat-model-standards, mermaid-caps) and agent prompts.

## Implementation plans — invocation (2026-08-16)
Parent spec: docs/superpowers/specs/2026-08-16-sec-overlay-invocation-design.md.

- Driven Invocation plan
  - source: docs/superpowers/plans/2026-08-16-sec-overlay-invocation.md
  - /sec-overlay:audit command, run.py drive loop, per-phase receipts, working-tree
    fence, run.env token writer, role inference, correlation manifest synthesis,
    O-65 redteam gate path fix. (Classification cross_refs include a self-reference —
    recorded as INFO in the conflicts report.)
