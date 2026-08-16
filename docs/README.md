# docs/

Design specs and planning documents for this marketplace.

**Naming convention:** specs live under `docs/superpowers/specs/` as
`YYYY-MM-DD-<topic>-design.md`.

**Writers:** Claude Code sessions in this workspace, on a branch, with user review
before merge.

## Contents

| Path | Purpose |
|------|---------|
| `superpowers/specs/2026-08-11-port-sec-overlay-design.md` | Design for porting the sec-harness skill into the sec-overlay plugin |
| `superpowers/plans/2026-08-11-port-sec-overlay.md` | Task-by-task implementation plan for the sec-overlay port |
| `superpowers/specs/2026-08-11-sec-overlay-doc-overhaul-design.md` | Design for the sec-overlay documentation overhaul (Go-prose removal, README/CLAUDE.md rewrite, per-folder READMEs, folder-README hook) |
| `superpowers/plans/2026-08-11-sec-overlay-doc-overhaul.md` | Six-commit implementation plan for the sec-overlay documentation overhaul |
| `superpowers/specs/2026-08-12-sec-overlay-review-improvements-design.md` | Design for four sec-overlay improvements from the lumedeodorant review: token accounting/self-score, systemic finding clustering, external-boundary disposition, SARIF completeness |
| `superpowers/plans/2026-08-12-sec-overlay-review-improvements.md` | Task-by-task TDD implementation plan for the four sec-overlay improvements (build order I3, I1, I2, I4) |
| `superpowers/specs/2026-08-14-marketplace-doc-structure-design.md` | Design for the marketplace documentation split: root CLAUDE.md for governance and scaffolding, per-plugin CLAUDE.md/README/CHANGELOG, plugin template, hook routing |
| `superpowers/plans/2026-08-14-marketplace-doc-structure.md` | Four-commit implementation plan for the marketplace documentation split (sec-overlay split, root rewrite, template, hook routing + test) |
| `superpowers/specs/2026-08-15-sec-overlay-defect-remediation-design.md` | Design to correct 57 defects from the agent-gateway sec-overlay run: an `audit` driver, shared ref/schema and status/receipt vocabularies, a coverage table, finding-accuracy fixes, a split risk-sorted report, phase telemetry, and a new artifact-review phase |
| `superpowers/plans/2026-08-15-sec-overlay-audit-driver.md` | Plan A of the defect-remediation spec (theme T1): TDD tasks for the deterministic `audit` phase-driver — phase table, loud-halt runner, agent-dispatch printer, wiring the six unwired modules, findings-gate placement, unrouted-class triage, and verify-honesty routing |
| `superpowers/plans/2026-08-15-sec-overlay-coverage-accuracy.md` | Plan C of the defect-remediation spec (themes T4/T5): TDD tasks for a derived route-to-control coverage table with logged gaps, doc-coverage provenance, resolver-backed finding citations, prefilter sidecar exclusion, same-line dedupe, class-extension alias-map gap logging, and red-team payload reachability |
| `superpowers/plans/2026-08-15-sec-overlay-report-telemetry-artifact-review.md` | Plan D of the defect-remediation spec (themes T6/T7 plus artifact-review): TDD tasks for a split risk-ordered report with real impact text and counts-in-words, per-finding detail files, phase telemetry via campaign-state timings, context doc-citation cross-checks, backend-completeness strictness, self-score critic metrics, and a new adversarial artifact-review phase with a deterministic artifact gate |
| `superpowers/specs/2026-08-16-architecture-threat-model-standards-source.md` | User-authored standards spec (input): C4/arc42 architecture docs, DFD/STRIDE threat models, Mermaid caps, CVSS v4.0, ASD-STE100 prose rules |
| `superpowers/specs/2026-08-16-architecture-threat-model-standards-design.md` | Design implementing the standards spec inside sec-overlay: rebuilt architecture/threat-model phases, derived DFD + attack sequences, CVSS v4.0 migration, diagram gate, STE linter |
| `superpowers/plans/2026-08-16-sec-overlay-cvss4-migration.md` | Plan 1 of the standards rebuild: CVSS v4.0 engine (vendored FIRST lookup data, MacroVector scoring), calibrate/prompt/fixture migration off 3.1 |
| `superpowers/plans/2026-08-16-sec-overlay-diagram-ste-enforcement.md` | Plan 2: deterministic enforcement — mermaid structure indexer, diagram gate (caps, labels, provenance, freshness), STE structural linter, arc42/threat-model duplication check |
| `superpowers/plans/2026-08-16-sec-overlay-arch-tm-rebuild.md` | Plan 3: rebuilt architecture/threat-model prompts (C4/arc42, derived DFD/STRIDE), new reference files + STE_PROSE block, gate phase wiring, 16-consumer rewiring, operating docs |
| `templates/plugin/` | New-plugin skeleton: `plugin.json`, README, CLAUDE.md, CHANGELOG, and a sample `SKILL.md`, each carrying `{{PLACEHOLDER}}` markers. The `CHANGELOG.md` skeleton's initial entry is imperative ("Add {{summary}}."); the `README.md` skeleton's install fence is tagged `text` |
