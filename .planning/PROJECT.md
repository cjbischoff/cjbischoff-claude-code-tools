# cjbischoff-claude-code-tools

## What This Is

A Claude Code plugin marketplace that distributes Christopher Bischoff's personal plugins.
It ships one plugin today: sec-overlay, an agentic security-audit harness with skills,
agents, and commands. The repo enforces its own governance: branch-per-change,
Conventional Commits, prek hooks, README/CHANGELOG routing, and automatic semver bumps.

## Core Value

The marketplace never ships an unverified claim: every plugin passes validation, every
release follows governance, and every confirmed sec-overlay finding is receipt-backed.

## Current State

**Shipped:** v5.1 Tech-Debt Cleanup (2026-08-22). Previous: v5.0 Hybrid
Diff-Review Architecture (2026-08-22).

v5.1 cleared all six acknowledged Phase 06 tech-debt items (two test-assertion
gaps, one lint error, three doc gaps) and closed the open ingest question — the
project now has zero deferred items and zero open blockers. sec-overlay is at
1.69.15.

sec-overlay now has a `review` verb with `security` and `general` profiles. The diff
pipeline covers diff acquisition, file selection, a sealed coverage manifest, hunk
positioning, per-language rule resolution, a retract-only reflection filter, bounded
concurrency, identity-checked resume, and diff-anchored SARIF output. Both the audit
and the review pipeline are verified end to end on real targets with receipts. The
core stays stdlib-only and the frozen JSON contract is unchanged.

**v5.1 stats:** 2 phases (direct execution), 19 files changed, +495/−186 lines,
2026-08-22, PRs #32 and #33.

**v5.0 stats:** 7 phases, 30 plans, 116 tasks, 212 files changed,
+38,296/−294 lines, 2026-08-17 through 2026-08-22.

## Next Milestone Goals

### v5.2: sec-overlay Defect Remediation (completed 2026-09-05)

Fix or disposition all 26 defects (D1-D26) identified in the 2026-09-01 sec-overlay
audit run on `ufe`. All 7 phases shipped. See `.planning/reports/2026-09-01-sec-overlay-audit-defects.md`.

### v5.3: sec-overlay Harness Coverage — Missed RCE

Fix the 9 harness defects (D-1 through D-9) that caused the sec-overlay audit to miss
an authenticated RCE in Tanium Comply. The defect report is at
`.planning/reports/2026-09-02-sec-overlay-missed-rce-coverage-defect-report.md`.

**Defects (ordered by priority per the report):**
1. D-3 — No npm entries in dependency-sink catalog (low, data)
2. D-1 — CWE-94/CWE-95 absent from class map; `injection` class unroutable (low, data)
3. D-2 — `security_only` silently deletes `unknown`-class semgrep findings (low, logic)
4. D-4 — No `dependency-catalog` receipt kind; prompt contradicts gate (medium)
5. D-5 — No mandatory class floor; coverage ledger is a closed loop (medium)
6. D-6 — Route census blind to OpenAPI; test-file noise (medium)
7. D-9 — Proof lane off by default, class-blind to ssti/injection (medium)
8. D-7 — No cross-repo data-channel edge in correlation (high)
9. D-8 — Out-of-scope caller => rejection instead of open obligation (medium)

**Cheapest combination that surfaces the finding:** D-3 + D-1 + D-2 + D-4
**Cheapest that surfaces the class:** D-7 + D-8

**Quality gates per phase:** `/gsd:code-review` after implementation; `/gsd:verify-work` per phase

**Non-goals:** No new runtime dependencies. Frozen JSON contract unchanged.
GROW-01/GROW-02 remain deferred to v2.

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
- ✓ Bundling, bounded concurrency/timeouts, identity-checked SHA-pinned resume, and diff-anchored output with content-only SARIF fingerprints (REV-06; SCALE-01/02/03, OUT-01/02) — Validated in Phase 4: Scale, Resume & Diff Output, 2026-08-20
- ✓ Full driven audit run completed on a real target with receipts; working-tree fence held (AUD-01) — Validated in Phase 5: End-to-End Verification, 2026-08-21
- ✓ Confirmed findings receipt-backed; Tier-2-only never confirms (AUD-02) — Validated in Phase 5, 2026-08-21
- ✓ Runtime-dependent findings scored and visible in headline counts (AUD-03) — Validated in Phase 5, 2026-08-21
- ✓ Architecture/threat-model artifacts pass deterministic gates; CVSS v4.0 only (AUD-04) — Validated in Phase 5, 2026-08-21
- ✓ Report states its 515-file coverage denominator; zero-finding classes ledgered (AUD-05) — Validated in Phase 5, 2026-08-21
- ✓ Both-profile review run completed E2E on a real diff, manifest sealed, lines positioning-confirmed (AUD-06) — Validated in Phase 5, 2026-08-21; profile-superset contract passed vacuously (0 findings), substantive re-check deferred to Phase 6 (E-12)

- ✓ Run defects fixed or dispositioned; frozen contract unchanged (REL-01) — Validated in Phase 6: Remediation and Governed Release, 2026-08-22; every Phase 5 defect row carries a terminal disposition
- ✓ Fixes ship through full governance with CodeRabbit review (REL-02) — Validated in Phase 6, 2026-08-22; PRs merged after CodeRabbit review
- ✓ Substantive profile-superset re-check (E-12): security-kept ⊆ general-kept proven non-vacuously on a real 14-file dispatch — Validated in Phase 6, 2026-08-22
- ✓ `--workspace` forwarding asserted in the CLI test (TEST-01) — v5.1, PR #32
- ✓ WR-01 tests prove the guard runs before any git call (TEST-02) — v5.1, PR #32
- ✓ ruff `I001` fixed; full-repo ruff clean (LINT-01) — v5.1, PR #32
- ✓ CLI-legend audited against `PHASE_TABLE` (DOC-01) — v5.1, PR #33
- ✓ Pipeline diagram carries `selfscore`/`artifact-gate`/`artifact-review` (DOC-02) — v5.1, PR #33
- ✓ Phase order carries a numbered `14.2 Selfscore` entry, test-enforced (DOC-03) — v5.1, PR #33
- ✓ Ingest WARNING closed: kb-redesign design doc affirmed as authority (ING-01) — v5.1, PR #33

### Active

None — next milestone not yet defined. Candidates: GROW-01, GROW-02 (see Next
Milestone Goals).

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
- Ingest question resolved (2026-08-22, ING-01): the 2026-08-11 kb-redesign design doc
  is affirmed as authority — the 2026-08-09 reference is the upstream repo's internal
  spec, explicitly out of scope in the design doc itself. See
  `.planning/INGEST-CONFLICTS.md` (WARNING closed).
- End-to-end verification now exists: Phase 5 ran a full driven audit (515-file
  coverage denominator) and a both-profile review on real targets, receipt-backed
  (AUD-01 through AUD-06, 2026-08-21).
- Zero known tech debt: all six Phase 06 items cleared in v5.1 (PRs #32, #33).

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
| Phase 5 UAT sign-off: WR-01/WR-02 ride Phase 6's REL-01 sweep; vacuous AUD-06 superset pass accepted with E-12 tracking the substantive re-check | scope-boundary calls recorded in 05-UAT.md and 05-DEFECTS.md, 2026-08-21 | ✓ Good — E-12 re-check passed non-vacuously in Phase 6 |
| D-01 fix: `redteam` and `postflight` added to the 22-entry `PHASE_TABLE` so `run.drive()` reaches both phases | documented pipeline steps were silently skipped by the mechanical table | ✓ Good |
| Review workspace resolves through `RepoMemory.for_target` sidecar (DIFF-04) | review artifacts leaked at bare `--root`; audit/scan already used the sidecar | ✓ Good |
| ING-01: 2026-08-11 kb-redesign design doc affirmed as authority | the 2026-08-09 reference is the upstream repo's internal spec, listed in the design doc's own Out-of-scope; no such file ever existed in this repo | ✓ Good |
| v5.1 phases ran as user-directed direct execution (no plans/SUMMARY.md) | tiny cleanup milestone; work verified by tests, lint, and merged PRs instead of GSD artifacts | ✓ Good — recorded as override_closeout |

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
*Last updated: 2026-08-22 after v5.1 milestone*
