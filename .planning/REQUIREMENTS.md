# Requirements: cjbischoff-claude-code-tools

**Defined:** 2026-08-16
**Core Value:** The marketplace never ships an unverified claim: every plugin passes
validation, every release follows governance, and every confirmed sec-overlay finding
is receipt-backed.

Note: the 50-doc ingest contained no PRD. These requirements derive from the
user-supplied success metrics and the standing invariants in `.planning/intel/`.

## v1 Requirements

### Validation (VAL)

- [ ] **VAL-01**: `claude plugin validate .` passes for the marketplace manifest and
  every registered plugin
- [ ] **VAL-02**: sec-overlay quality gates pass — pytest green, ruff and ty clean,
  zero warnings
- [ ] **VAL-03**: prek hooks are installed and `prek run` passes repo-wide

### Audit Integrity (AUD)

- [ ] **AUD-01**: A full `/sec-overlay:audit` run completes end to end on a real
  target repo, with per-phase receipts written and the working-tree fence intact
- [ ] **AUD-02**: Every finding with status `confirmed` cites a mechanical tool
  receipt; Tier-2-only or syntactic-match evidence never reaches `confirmed`
- [ ] **AUD-03**: Runtime-dependent findings land in `needs-deployment-testing` with a
  real risk score, visible in report headline counts
- [ ] **AUD-04**: Architecture and threat-model artifacts pass the deterministic gates
  (Mermaid caps, derivation headers, STE lint) and score with CVSS v4.0 only
- [ ] **AUD-05**: The audit report states its coverage denominator; every
  attack-surface class without a finding has a logged coverage-ledger entry

### Release Governance (REL)

- [ ] **REL-01**: Every defect observed in the verification run is fixed or given a
  written disposition, with models.py/evidence.py and `fingerprint()` identity
  unchanged, asserted by tests
- [ ] **REL-02**: Every fix ships through governance — branch, Conventional Commit,
  semver bump plus CHANGELOG entry in the same commit, PR merged only after
  CodeRabbit's walkthrough comment

## v2 Requirements

Deferred to a future milestone. Tracked but not in the current roadmap.

### Growth (GROW)

- **GROW-01**: A second plugin is onboarded from `docs/templates/plugin/` and passes
  the same validation and governance bar
- **GROW-02**: `claude plugin validate .` runs as an automated gate (prek hook or CI)
  instead of a manual step

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Anthropic SDK / direct API dependency | Rejected by ADR-2026-08-04; stdlib-only core |
| External multi-repo check registry | Deferred by ADR-2026-08-04; in-repo bundles only |
| Correlation write-back or member re-scanning | Spec B pins the correlation layer read-only |
| Edits to models.py / evidence.py | Frozen JSON contract, byte-mirrored by a Go port |
| Mixing CVSS v3.1 and v4.0 | Ruling R2 pins v4.0 harness-wide, no mixing |
| Re-implementing delivered baseline features | All 50 ingested docs are delivered work |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| VAL-01 | Phase 1 | Pending |
| VAL-02 | Phase 1 | Pending |
| VAL-03 | Phase 1 | Pending |
| AUD-01 | Phase 2 | Pending |
| AUD-02 | Phase 2 | Pending |
| AUD-03 | Phase 2 | Pending |
| AUD-04 | Phase 2 | Pending |
| AUD-05 | Phase 2 | Pending |
| REL-01 | Phase 3 | Pending |
| REL-02 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 10 total
- Mapped to phases: 10
- Unmapped: 0 ✓

---
*Requirements defined: 2026-08-16*
*Last updated: 2026-08-16 after initial definition*
