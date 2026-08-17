# Roadmap: cjbischoff-claude-code-tools

## Overview

The 50-doc ingest delivered a complete sec-overlay baseline through 2026-08-16, but no
end-to-end run of the current pipeline exists — the dogfooding evidence predates the
audit driver, CVSS v4.0, and the architecture/threat-model rebuild. This milestone
proves the delivered baseline: verify marketplace health and quality gates, drive a
full receipt-backed audit on a real target, then remediate what the run surfaces and
ship every fix through the repo's own governance without contract regressions.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Baseline Health Verification** - Prove the delivered marketplace and plugin baseline is healthy: validation, tests, hooks
- [ ] **Phase 2: Receipt-Backed Audit Verification** - Drive a full /sec-overlay:audit run on a real target and verify honest, receipt-backed output
- [ ] **Phase 3: Remediation and Governed Release** - Fix what the run surfaced and ship through governance with the frozen contract intact

## Phase Details

### Phase 1: Baseline Health Verification
**Goal**: The maintainer can trust the delivered baseline — marketplace validation, quality gates, and governance hooks all pass today
**Depends on**: Nothing (first phase)
**Requirements**: VAL-01, VAL-02, VAL-03
**Success Criteria** (what must be TRUE):
  1. `claude plugin validate .` exits clean for the marketplace manifest and the sec-overlay plugin
  2. sec-overlay's pytest suite passes, and ruff and ty report zero errors and zero warnings
  3. prek hooks are installed and `prek run` passes across the repo
**Plans**: TBD

### Phase 2: Receipt-Backed Audit Verification
**Goal**: A current-pipeline audit run on a real target proves the harness produces verified, receipt-backed findings that never mislead the engineer reading them
**Depends on**: Phase 1
**Requirements**: AUD-01, AUD-02, AUD-03, AUD-04, AUD-05
**Success Criteria** (what must be TRUE):
  1. `/sec-overlay:audit` drives a run start to finish on a real target repo; per-phase receipts exist in the run workspace and the working-tree fence holds
  2. Every finding with status `confirmed` cites a mechanical tool receipt; no Tier-2-only or syntactic-match finding is confirmed
  3. Runtime-dependent findings appear as `needs-deployment-testing` with real risk scores, and headline counts do not hide them
  4. The architecture/ and threat-model/ artifacts pass the diagram gate and STE lint, with every score CVSS v4.0
  5. The report states its coverage denominator, and every attack-surface class without a finding has a logged coverage-ledger entry
**Plans**: TBD

### Phase 3: Remediation and Governed Release
**Goal**: Defects the verification run surfaced are fixed and shipped through the repo's own governance, with zero frozen-contract regressions
**Depends on**: Phase 2
**Requirements**: REL-01, REL-02
**Success Criteria** (what must be TRUE):
  1. Every defect logged during the Phase 2 run has a merged fix or a written disposition
  2. models.py, evidence.py, and `fingerprint()` identity are unchanged after fixes, asserted by the test suite
  3. Each fix landed on a branch with a Conventional Commit, semver bump, and CHANGELOG entry in the same commit
  4. Each PR merged only after CodeRabbit's walkthrough comment posted
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Baseline Health Verification | 0/TBD | Not started | - |
| 2. Receipt-Backed Audit Verification | 0/TBD | Not started | - |
| 3. Remediation and Governed Release | 0/TBD | Not started | - |
