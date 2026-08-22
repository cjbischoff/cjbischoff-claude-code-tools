# Requirements: cjbischoff-claude-code-tools — Milestone v5.1 Tech-Debt Cleanup

**Defined:** 2026-08-22
**Core Value:** The marketplace never ships an unverified claim: every plugin passes
validation, every release follows governance, and every confirmed sec-overlay finding
is receipt-backed.

## v5.1 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### Test Debt (TEST)

- [x] **TEST-01**: `test_rule_glob.py:231` asserts `--workspace` forwarding
  (CodeRabbit nitpick, PR #23) — closed 2026-08-22, PR #32
- [x] **TEST-02**: WR-01 tests prove the guard runs before git
  (`test_review_live.py:403-432`, CodeRabbit nitpick, PR #23) — closed 2026-08-22, PR #32

### Lint Debt (LINT)

- [x] **LINT-01**: The pre-existing ruff `I001` in
  `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_cli.py:778` is fixed
  and ruff runs clean — closed 2026-08-22, PR #32

### Doc Debt (DOC)

- [ ] **DOC-01**: `skills/sec-overlay/README.md` CLI-legend block is audited for
  pre-existing misorderings and corrected
- [ ] **DOC-02**: `skills/sec-overlay/helpers/README.md` pipeline diagram carries
  the `selfscore`, `artifact-gate`, and `artifact-review` nodes
- [ ] **DOC-03**: `skills/sec-overlay/CLAUDE.md` "Phase order (one pass)" list
  carries a numbered `selfscore` entry

### Ingest (ING)

- [ ] **ING-01**: The 2026-08-09 spec referenced by the 2026-08-11 kb-redesign
  design is located, or the design doc is affirmed as authority; the
  `.planning/INGEST-CONFLICTS.md` WARNING is closed with the decision recorded

## v2 Requirements

Deferred to a future milestone. Tracked but not in current roadmap.

### Growth (GROW)

- **GROW-01**: A second plugin is onboarded from `docs/templates/plugin/` and passes
  the same validation and governance bar (deferred again 2026-08-22 — no candidate
  plugin named)
- **GROW-02**: `claude plugin validate .` runs as an automated gate (prek hook or CI)
  instead of a manual step (deferred again 2026-08-22)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Second plugin onboarding (GROW-01) | No candidate plugin named; deferred to v2 |
| Automated plugin-validate gate (GROW-02) | Deferred with GROW-01; manual validate stays |
| Anthropic SDK / direct API dependency | Rejected by ADR-2026-08-04; stdlib-only core |
| Edits to models.py / evidence.py | Frozen JSON contract, byte-mirrored by a Go port |
| New sec-overlay features | Cleanup-only milestone; feature work waits for the next milestone |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| TEST-01 | Phase 7 | Complete |
| TEST-02 | Phase 7 | Complete |
| LINT-01 | Phase 7 | Complete |
| DOC-01 | Phase 8 | Pending |
| DOC-02 | Phase 8 | Pending |
| DOC-03 | Phase 8 | Pending |
| ING-01 | Phase 8 | Pending |

**Coverage:**
- v5.1 requirements: 7 total
- Mapped to phases: 7
- Unmapped: 0 ✓

---
*Requirements defined: 2026-08-22*
*Last updated: 2026-08-22 after roadmap creation (Phases 7-8)*
