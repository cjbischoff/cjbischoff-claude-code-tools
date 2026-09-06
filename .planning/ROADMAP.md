# Roadmap: cjbischoff-claude-code-tools

## Milestones

- ✅ **v5.0 Hybrid Diff-Review Architecture** — Phases 1-6 + 04.1 (shipped 2026-08-22)
- ✅ **v5.1 Tech-Debt Cleanup** — Phases 7-8 (shipped 2026-08-22)
- ✅ **v5.2 sec-overlay Defect Remediation** — Phases 9-15 (shipped 2026-09-05)
- **v5.3 sec-overlay Harness Coverage — Missed RCE** — Phases 16-19 (active)

## Phases

<details>
<summary>✅ v5.0 Hybrid Diff-Review Architecture (Phases 1-6 + 04.1) — SHIPPED 2026-08-22</summary>

- [x] Phase 1: Baseline Health Verification (3/3 plans) — completed 2026-08-17
- [x] Phase 2: Diff Pipeline & Positioning (5/5 plans) — completed 2026-08-19
- [x] Phase 3: Rule Matching & Review Modes (7/7 plans) — completed 2026-08-19
- [x] Phase 4: Scale, Resume & Diff Output (4/4 plans) — completed 2026-08-20
- [x] Phase 04.1: Close gap: DIFF-04 — review sidecar workspace isolation (1/1 plan, INSERTED) — completed 2026-08-19
- [x] Phase 5: End-to-End Verification (Audit & Review) (4/4 plans) — completed 2026-08-21
- [x] Phase 6: Remediation and Governed Release (6/6 plans) — completed 2026-08-22

Full phase details: `.planning/milestones/v5.0-ROADMAP.md`

</details>

<details>
<summary>✅ v5.1 Tech-Debt Cleanup (Phases 7-8) — SHIPPED 2026-08-22</summary>

- [x] Phase 7: Test & Lint Debt Cleanup (direct execution, PR #32) — completed 2026-08-22
- [x] Phase 8: Documentation Accuracy & Ingest Closure (direct execution, PR #33) — completed 2026-08-22

Full phase details: `.planning/milestones/v5.1-ROADMAP.md`

</details>

<details open>
<summary>🔜 v5.2 sec-overlay Defect Remediation (Phases 9-15) — ACTIVE</summary>

- [x] **Phase 9: CodeQL Guard & Driver Surface**
  Requirements: CODEQL-01, DRIVER-01 (D2, D5)
  Goal: Fix the unanchored substring match in `codeql.py` that false-positively flags benign CodeQL configs, and structured error rendering for backend failures.
  Success criteria:
  1. `**/jest.setup.*` in `paths-ignore` is TRUSTED; `setup:` key is UNTRUSTED — both directions pass ✓
  2. Backend failure surfaces as bordered operator message, not raw traceback ✓
  3. Offending config line printed in untrusted-config messages ✓
  Completed 2026-09-05 | Commits: 2d1bd12, 92230fd

- [x] **Phase 10: Prompt-Contract Consistency**
  Requirements: CONTRACT-01, CONTRACT-02 (D1, D9, D11, D12, D23)
  Goal: Fix four instances of agent prompts naming outputs the Python contract doesn't model. Add consistency test binding prompt-named outputs to schema/dataclass.
  Success criteria:
  1. `dependency_sinks` field exists on `ScanProfile` dataclass and schema ✓
  2. `validate_profile` reports unknown keys as validation errors ✓
  3. Consistency test catches future prompt-contract drift (model after `test_references_caps.py`) ✓
  4. `logic-chain` added to canonical class list ✓
  5. `attacker`, `privilege`, `exact_request`, `exfil_channels` declared on `Finding` ✓
  6. `impact` added to producer prompts ✓
  Completed 2026-09-05 | Commit: 8e3c064

- [x] **Phase 11: Report Renderer Overhaul**
  Requirements: REPORT-01 through REPORT-07 (D14-D19, D24)
  Goal: Fix the seven report renderer defects that collectively make `report.md` the audit's least trustworthy artifact.
  Success criteria:
  1. `patch_diff` rendered for finding with one; `FIXED` status renders correctly ✓
  2. Non-shipping routes (test/mock/fixture) filtered from census output ✓
  3. Coverage table joins against shipping findings by `cls` ✓
  4. All paths repo-relative; SARIF consistency matched ✓
  5. Limitations section renders coverage caveats including CodeQL absence ✓
  6. Triage `Status` shows finding `status` not `runtime_disposition` ✓
  7. Messages truncated on word boundary, not mid-token ✓
  Completed 2026-09-05 | Commit: 709d03b

- [x] **Phase 12: Semgrep Rules & Model Independence**
  Requirements: SEMGREP-01, MODEL-01 (D3, D21)
  Goal: Ship or hard-gate vendored semgrep rules; express model-family diversity relatively.
  Success criteria:
  1. Missing semgrep rules cause hard failure (driver refuses to run past), not printed suggestion
  Completed 2026-09-05 — _vendor_cmd() uses absolute path; trace.md and artifact-review.md
  use relative model-family expressions (D21)

- [x] **Phase 13: Orphaned Agents & Driver Integrity**
  Requirements: DRIVER-02, DRIVER-03, REVIEW-01 (D22, D26, D20)
  Goal: Wire orphaned prompts, fix silent self-complete, add renderer_defect verdict.
  Success criteria:
  1. Skipped phases (prove/selfscore) print message instead of silent advance ✓
  2. renderer_defect verdict added to artifact-review.md output contract ✓
  3. Unwired agent prompts documented in phases.py with wiring instructions ✓
  Completed 2026-09-05

- [x] **Phase 14: Methodology & Trust Standards**
  Requirements: GITHIST-01, SEVERITY-01, TRUST-01 (D4, D13, D25)
  Goal: Fix githist precision, severity precondition methodology, TOOL_TRUST absence.
  Success criteria:
  1. _SECURITY_GREP keywords anchored with \b ✓
  2. Precondition count uses minimum conjunctive set across routes ✓
  3. TOOL_TRUST has explicit absence clause ✓
  Completed 2026-09-05

- [x] **Phase 15: Friction & Hygiene**
  Requirements: HYGIENE-01 through HYGIENE-04 (D6-D8, D10)
  Goal: Fix low-severity friction defects.
  Success criteria:
  1. advance() prints one-line confirmation with receipt path ✓
  2. restamp_derived helper ships in diagram_gate.py ✓
  Completed 2026-09-05

</details>

<details open>
<summary>🔜 v5.3 sec-overlay Harness Coverage — Missed RCE (Phases 16-19) — ACTIVE</summary>

- [ ] **Phase 16: Dependency-Sink Catalog & CWE Mapping**
  Requirements: CATALOG-01, CWE-01, CWE-02 (D-3, D-1, D-2)
  Goal: Fix the three data/logic defects that block the finding at the earliest stage —
  no npm entries in the dependency-sink catalog, CWE-94/95 unmapped in the class map,
  and `security_only` silently deleting `unknown`-class semgrep hits.
  Success criteria:
  1. npm template/eval packages catalogued in dependency-sinks.json; `reconcile_plan` routes
     classes from `package.json:127` alone
  2. CWE-94/95 resolve to routable class; `detect-eval-with-expression` semgrep result
     appears in `agents_to_spawn`
  3. `security_only` does not drop CWE-declaring semgrep hits; dropped findings recorded
     per-id in a drop ledger

- [ ] **Phase 17: Receipt Kind & Class Floor**
  Requirements: RECEIPT-01, FLOOR-01 (D-4, D-5)
  Goal: Fix the two medium-severity contract defects — add `dependency-catalog` receipt
  kind so dependency-internal sinks can reach confirmed, and implement a mandatory class
  floor so the coverage ledger captures missing classes.
  Success criteria:
  1. `dependency-catalog` receipt in `_MECHANICAL`; prompt-constants and gate agree
  2. JS/TS mandatory class floor enforced; floor class neither investigated nor excluded
     forces `completeness: partial` and names the class in the ledger

- [ ] **Phase 18: Route Census & Proof Lane**
  Requirements: CENSUS-01, PROVE-01 (D-6, D-9)
  Goal: Fix OpenAPI-blind route census and add ssti/injection to the proof lane's
  oracle-able classes.
  Success criteria:
  1. Census over comply contains `POST /v1/vulnerability-sources` bound to OpenAPI handler;
     zero test-path entries; zero path-shape validation rejects
  2. `prove.AUTO_CONFIRMABLE` includes `ssti` and `injection`; with `prove_findings: true`,
     a `dot.template` fixture is promoted, not rejected `class-not-oracle-able`

- [ ] **Phase 19: Correlation & Cross-Member Obligations**
  Requirements: EDGE-01, OBLIGATION-01 (D-7, D-8)
  Goal: Fix the two high-cost defects — add data-channel edge kind to correlation and
  cross-member obligation state so a producer/consumer pair across repos is representable.
  Success criteria:
  1. Manifest-declared data-channel emits cross-member verdict with `evidence_chain`
     naming both sites
  2. `caller-out-of-scope` blocker is non-fatal; cross-member obligation persists as
     open obligation, not rejection

</details>

## Progress

Milestone v5.3 active — Phase 16 not started.

---

*Next: `/gsd:discuss-phase 16` or `/gsd:autonomous`*
