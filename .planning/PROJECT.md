# cjbischoff-claude-code-tools

## What This Is

A Claude Code plugin marketplace that distributes Christopher Bischoff's personal plugins.
It ships one plugin today: sec-overlay, an agentic security-audit harness with skills,
agents, and commands. The repo enforces its own governance: branch-per-change,
Conventional Commits, prek hooks, README/CHANGELOG routing, and automatic semver bumps.

## Core Value

The marketplace never ships an unverified claim: every plugin passes validation, every
release follows governance, and every confirmed sec-overlay finding is receipt-backed.

## Current Milestone: v5.0 Hybrid Diff-Review Architecture

**Goal:** Extend sec-overlay with diff-scoped review (security and general-defect
profiles) that absorbs open-code-review capabilities, then prove the full pipeline
end to end and ship through governance.

**Target features:**
- Baseline health verification: plugin validate, pytest/ruff/ty, prek hooks (from v4.0)
- `review` verb with `--profile security|general` in `sec_overlay.cli`
- Diff pipeline: `diffscope.py` extension, `file_select.py`, per-file coverage manifest
- Hunk parser + deterministic positioning + position-vs-hunk gate in `phase_gate.py`
- Glob rule matcher, 4-layer rule resolution, rule-file safety, per-language rule docs
  (NPE, thread-safety, XSS, SQL injection)
- Reflection filter: retract-only, fail-open, composed under the receipt gate
- Semantic file bundling (sec-overlay addition beyond OCR) with concurrency limits
- Diff-anchored output payload and per-file resume manifest
- End-to-end verification run (audit and review) on a real target, receipt-backed
- Remediation and governed release with CodeRabbit review

**Spec source:** `/Users/christopher/Workspace/review_open-code-review/spec_sec-overlay-improvement_20260816_0920.md`

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
- ✓ Baseline health verified: plugin validate, ruff/ty green, prek hooks (VAL-01/02/03) — Validated in Phase 1: Baseline Health Verification, 2026-08-17 (pytest carries a recorded maintainer override for two environmental failures)
- ✓ Coverage manifest blocks a `complete` seal while any file is pending (REV-02) — Validated in Phase 2: Diff Pipeline & Positioning, 2026-08-18
- ✓ Positioning confirms or declines every finding location; no guesses (REV-03) — Validated in Phase 2: Diff Pipeline & Positioning, 2026-08-18
- ✓ `review` verb reviews a diff in `security` and `general` profiles (REV-01) — Validated in Phase 3: Rule Matching & Review Modes, 2026-08-19
- ✓ Glob rule matching selects per-language rule docs with safe rule-file reads (REV-04) — Validated in Phase 3: Rule Matching & Review Modes, 2026-08-19
- ✓ Reflection filter retracts only, fails open, never confirms (REV-05) — Validated in Phase 3: Rule Matching & Review Modes, 2026-08-19
- ✓ Review workspace isolated to the `<target>/.sec-overlay/<slug>/` sidecar; nothing written to the reviewed repo's tracked tree (DIFF-04) — Validated in Phase 04.1: Close gap: review sidecar workspace isolation, 2026-08-19

### Active

- [ ] Full driven audit run completes on a real target with receipts (AUD-01)
- [ ] Confirmed findings are receipt-backed; Tier-2-only never confirms (AUD-02)
- [ ] Runtime-dependent findings scored and visible, never hidden (AUD-03)
- [ ] Architecture/threat-model artifacts pass gates; CVSS v4.0 only (AUD-04)
- [ ] Report states coverage denominator; gaps logged, never dropped (AUD-05)
- [ ] Run defects fixed or dispositioned; frozen contract unchanged (REL-01)
- [ ] Fixes ship through full governance with CodeRabbit review (REL-02)
- [ ] Bundling and concurrency bound sub-agent context on large changesets (REV-06)

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

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-08-19 after completing Phase 04.1 (Close gap: DIFF-04 — review sidecar workspace isolation) of milestone v5.0*
