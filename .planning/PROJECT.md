# cjbischoff-claude-code-tools

## What This Is

A Claude Code plugin marketplace that distributes Christopher Bischoff's personal plugins.
It ships one plugin today: sec-overlay, an agentic security-audit harness with skills,
agents, and commands. The repo enforces its own governance: branch-per-change,
Conventional Commits, prek hooks, README/CHANGELOG routing, and automatic semver bumps.

## Core Value

The marketplace never ships an unverified claim: every plugin passes validation, every
release follows governance, and every confirmed sec-overlay finding is receipt-backed.

## Requirements

### Validated

Delivered baseline from 50 ingested planning docs (2026-08-02 through 2026-08-16).
All items below shipped before this project started.

- ✓ Signal-over-noise correctness fixes (clusters A-G) — 2026-08-02
- ✓ Evidence substrate (kb/graph.json, Tier-1/Tier-2, honesty gate) — 2026-08-02
- ✓ Codex-security feature port (fingerprints, FP loop, coverage ledger, cost) — 2026-08-03
- ✓ aghast/OpenAnt native capabilities (check bundles, schema gate, guards) — 2026-08-04
- ✓ Spec A pipeline hardening (scanscope, scoring strictness, methodology) — 2026-08-07
- ✓ Spec B cross-repo correlation (read-only layer, rethreshold engine) — 2026-08-08
- ✓ Port to plugins/sec-overlay/ with plugin.json and marketplace.json — 2026-08-11
- ✓ Marketplace doc structure (root CLAUDE.md governs; per-plugin doc trio) — 2026-08-14
- ✓ Defect remediation, 57 issues across T-themes (driver, vocab, coverage) — 2026-08-15
- ✓ CVSS v4.0 migration, architecture/threat-model rebuild, diagram/STE gates — 2026-08-16
- ✓ Driven invocation (/sec-overlay:audit, run.py, receipts, fence) — 2026-08-16

### Active

- [ ] `claude plugin validate .` passes for the marketplace and every plugin (VAL-01)
- [ ] sec-overlay quality gates green: pytest, ruff, ty, zero warnings (VAL-02)
- [ ] prek hooks installed and passing repo-wide (VAL-03)
- [ ] Full driven audit run completes on a real target with receipts (AUD-01)
- [ ] Confirmed findings are receipt-backed; Tier-2-only never confirms (AUD-02)
- [ ] Runtime-dependent findings scored and visible, never hidden (AUD-03)
- [ ] Architecture/threat-model artifacts pass gates; CVSS v4.0 only (AUD-04)
- [ ] Report states coverage denominator; gaps logged, never dropped (AUD-05)
- [ ] Run defects fixed or dispositioned; frozen contract unchanged (REL-01)
- [ ] Fixes ship through full governance with CodeRabbit review (REL-02)

### Out of Scope

- Anthropic SDK / direct API dependency — rejected by ADR-2026-08-04; stdlib-only core
- External multi-repo check registry — deferred by ADR-2026-08-04; in-repo bundles only
- OpenAnt LLM-enhanced dataset and attacker-simulation stages — rejected by ADR-2026-08-04
- Changes to Task-tool subagent dispatch — rejected by ADR-2026-08-04
- Correlation write-back or member re-scanning — Spec B pins the layer read-only
- Edits to models.py / evidence.py — frozen JSON contract, byte-mirrored by a Go port
- Mixing CVSS v3.1 and v4.0 — ruling R2 pins v4.0 harness-wide, no mixing
- New plugins this milestone — growth is v2; verify the existing baseline first

## Context

- Source of record: `.planning/intel/` (SYNTHESIS.md entry point) from a 50-doc ingest.
  All ingested docs are historical, completed sec-overlay design work — delivered
  baseline, not open work.
- Repo governance lives in the root CLAUDE.md: branch-per-change, Conventional Commits,
  prek hooks, changelog routing, automatic version bumps, CodeRabbit review wait.
- Target runtime: Claude Code plugin runtime; skills, agents, and commands distributed
  via the marketplace manifest at `.claude-plugin/marketplace.json`.
- Open ingest question: the 2026-08-11 kb-redesign design references a 2026-08-09 spec
  absent from the ingest set (see `.planning/INGEST-CONFLICTS.md` WARNING). Resolve by
  locating the spec or affirming the design doc as authority.
- Existing dogfooding evidence (2026-08-03 and 2026-08-07 runs) predates the audit
  driver, CVSS v4.0, and the architecture/threat-model rebuild. The current pipeline
  has no end-to-end verification run yet.

## Constraints

- **Tech stack**: stdlib-only Python core — no new runtime dependency in pyproject.toml
- **Contract**: models.py and evidence.py frozen; `fingerprint()` identity unchanged —
  byte-mirrored by a parallel Go port
- **Evidence**: tool-receipt confirmation bar never bypassed; Tier-2-only evidence
  never reaches confirmed status
- **Correlation**: read-only over member repos; sidecars byte-identical after a run
- **Standards**: CVSS v4.0 pinned; Mermaid caps hard-enforced (exceeding a cap is a
  generation failure); ASD-STE100 prose in gated artifacts
- **Code quality**: line length 100; absolute imports; functions ≤100 lines,
  complexity ≤8; TDD failing-test-first
- **Governance**: no direct commits to main; explicit path staging only (never
  `git add -A`); semver bump plus CHANGELOG in the same commit as shipping-file changes

## Key Decisions

<decisions>

| Decision | Rationale | Status |
|----------|-----------|--------|
| ADR-2026-08-04: adopt aghast/OpenAnt capabilities natively; reject SDK dependency | stdlib-only core preserved; capabilities re-implemented in-repo | Proposed — not locked ("approved (design), pending implementation plan") |
| CVSS v4.0 harness-wide, no mixing (ruling R2) | one scoring version everywhere; user interview ruling 2026-08-16 | ✓ Delivered |
| Artifact layout replaced outright: workspace architecture/ and threat-model/ (ruling R3) | no shims; all consumers re-pointed | ✓ Delivered |
| Invocation scope A1/B1/C1/D1: one command, thin driver, receipts + fence, inferred roles | latest authority on how a run is invoked and driven | ✓ Delivered |
| Marketplace doc structure: root CLAUDE.md governs; per-plugin doc trio | plugin CLAUDE.md never auto-loads for installers | ✓ Delivered |

No decision is ADR-locked. ADR-2026-08-04 is the only ADR and remains proposed.

</decisions>

---
*Last updated: 2026-08-16 after ingest-driven project initialization*
