---
phase: 05
slug: end-to-end-verification-audit-review
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-08-21
---

# Phase 05 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| target work repo → this marketplace repo | Third-party employer source crosses into a repository whose history is permanent | Sanitized receipts: commands, exit codes, counts, SHAs only |
| this repo's tooling → target work repo tree | The review and audit pipelines write a sidecar into a repository we do not own | Sidecar files under `.sec-overlay` only; tracked tree untouched |
| upstream semgrep ruleset → this repo's working tree | Several thousand third-party files land inside a tracked directory | Vendored clone, gitignored, never staged |
| shipped pipelines → recorded evidence | Real pipeline output crosses into a claim of correctness | Receipt figures, gate verdicts, coverage counts |
| this phase's receipts → the downstream verification report | Citations cross into the record that closes the phase | Receipt references and evidence maps |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-05-01 | Information Disclosure | receipt and ledger authoring (Plan 01) | high | mitigate | D-07 sanitization pass, automated `rg` gate, blocking human review before first commit — evidence: 05-01-SUMMARY.md sign-off record | closed |
| T-05-02 | Tampering | `review` run against the target tree | high | mitigate | `git status --porcelain --untracked-files=no` empty before and after — evidence: 05-01-review-security-receipt.md | closed |
| T-05-03 | Repudiation | superset comparison (Plan 01) | high | mitigate | Subset comparison recorded with 0 violations; both receipts quote the identical SHA pair — evidence: 05-01-review-general-receipt.md | closed |
| T-05-04 | Information Disclosure | repro commands inside 05-DEFECTS.md | medium | mitigate | Task 3 human checkpoint inspected repro commands before commit — evidence: 05-01-SUMMARY.md checkpoint record | closed |
| T-05-05 | Spoofing | SHA pair drift between the two profile runs | medium | mitigate | Task 2 read SHAs back from the Task 1 receipt; both receipts quote identical values — evidence: both 05-01 receipts | closed |
| T-05-06 | Denial of Service | shipped `--timeout` and `--concurrency` defaults on a real diff | low | accept | Phase 4 proved bounded-run and timeout behaviour; a hang is a run-blocker under D-10 — see Accepted Risks Log | closed |
| T-05-07 | Information Disclosure | receipt and ledger authoring (Plan 02) | high | mitigate | D-07 sanitization pass; `rg` gate reported 0 non-sidecar target-repo paths — evidence: 05-02-SUMMARY.md | closed |
| T-05-08 | Tampering | the audit run against the target tree | high | mitigate | Working-tree fence held; porcelain empty after run; `fence()` ran before each deterministic stage — evidence: 05-02-SUMMARY.md and 05-02-audit-run-receipt.md | closed |
| T-05-09 | Tampering | the vendored semgrep clone inside a tracked directory | high | mitigate | Root `.gitignore` entry `plugins/sec-overlay/skills/sec-overlay/helpers/rules/semgrep/` (.gitignore:28); explicit-path staging only | closed |
| T-05-10 | Repudiation | stage-completeness claim (Plan 02) | high | mitigate | Receipt compares against `PHASE_TABLE` length computed at run time; 24/24 stages recorded in state.json — evidence: 05-02-SUMMARY.md | closed |
| T-05-11 | Repudiation | a mid-pipeline halt | medium | mitigate | D-12 restart prohibition in force; run completed 24/24 with no halt, so the recorded-halt path was not exercised — evidence: 05-02-audit-run-receipt.md | closed |
| T-05-12 | Elevation of Privilege | a run-blocker fix landing without governance | medium | mitigate | The one run-blocker fix (cwd-scoping bug in `run_review`) landed on a branch with a Conventional Commit and governance files — evidence: 05-01-SUMMARY.md commit records | closed |
| T-05-13 | Denial of Service | a long agent-driven pipeline hanging | low | accept | A hang is a visible run-blocker under D-10; Phase 6 owns durability work — see Accepted Risks Log | closed |
| T-05-14 | Information Disclosure | finding readback (Plan 03) | high | mitigate | Only identifiers, statuses, evidence source names, and counts left the sidecar — evidence: 05-03-finding-integrity-receipt.md | closed |
| T-05-15 | Information Disclosure | receipt and ledger authoring (Plan 03) | high | mitigate | D-07 sanitization gate clean, 0 non-permitted target-repo path occurrences — evidence: 05-03-SUMMARY.md | closed |
| T-05-16 | Repudiation | a vacuous pass on an empty bucket | high | mitigate | Receipt states bucket contents explicitly and records vacuous satisfaction where applicable — evidence: 05-03-finding-integrity-receipt.md | closed |
| T-05-17 | Spoofing | a hand-rolled tier check disagreeing with the pipeline | medium | mitigate | Verification imported `evidence.confirms_alone` directly; no re-implemented tier set — evidence: 05-03-SUMMARY.md | closed |
| T-05-18 | Tampering | report headline counts disagreeing with per-finding data | medium | mitigate | Report figure compared against the count computed from `findings/<ID>.json`; headline match confirmed — evidence: 05-03-finding-integrity-receipt.md | closed |
| T-05-19 | Repudiation | re-running the audit to clear a violation | high | mitigate | D-12 prohibition held; violations recorded as `deferred` ledger rows, no re-run — evidence: 05-DEFECTS.md | closed |
| T-05-20 | Tampering | sidecar artifacts modified or pruned during readback | medium | mitigate | D-09 retention prohibition; all readback commands read-only — evidence: 05-03-SUMMARY.md | closed |
| T-05-21 | Information Disclosure | architecture and threat-model artifact readback (Plan 04) | high | mitigate | Only counts, booleans, file names, and exit codes left the sidecar — evidence: 05-04-artifact-coverage-receipt.md | closed |
| T-05-22 | Information Disclosure | receipt and ledger authoring (Plan 04) | high | mitigate | Two `rg` gates over every Phase 5 file; raw count 9 traced to documented planner self-references, refined count 0, both reported — evidence: 05-04-artifact-coverage-receipt.md sanitization section | closed |
| T-05-23 | Repudiation | an absent gate artifact read as a pass | high | mitigate | Task 1 verification prints `MISSING` explicitly for absent gate artifacts — evidence: 05-04-artifact-coverage-receipt.md | closed |
| T-05-24 | Tampering | a CVSS v3.1 vector reaching an artifact without passing through scoring | high | mitigate | Scan corrected a vacuous glob and found 10 real vectors, all `CVSS:4.0/`, 0 non-v4 — evidence: 05-04-SUMMARY.md and receipt | closed |
| T-05-25 | Repudiation | a `complete` coverage ledger hiding surfaces awaiting follow-up | high | mitigate | `completeness` and `needs_follow_up` read together; shipped `validate_coverage_ledger()` was the acceptance authority — evidence: 05-04-artifact-coverage-receipt.md | closed |
| T-05-26 | Spoofing | a narrowed audit producing a flattering denominator | medium | mitigate | Denominator cross-checked against the Plan 02 receipt's no-narrowing statement per D-03 — evidence: 05-04-artifact-coverage-receipt.md | closed |
| T-05-27 | Spoofing | a hand-rolled ledger walk disagreeing with the pipeline | medium | mitigate | Verification imported `coverage_ledger.validate_coverage_ledger` directly; no parallel implementation — evidence: 05-04-SUMMARY.md | closed |
| T-05-28 | Tampering | sidecar artifacts modified or pruned during readback | medium | mitigate | D-09 retention prohibition; all readback commands read-only — evidence: 05-04-SUMMARY.md | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-05-01 | T-05-06 | Phase 4 proved bounded-run and timeout behaviour for the review CLI. A hang on a real diff surfaces as a run-blocker under D-10 and is caught by the exit-code check. Severity low, below the block threshold. | plan-time disposition (05-01-PLAN.md) | 2026-08-21 |
| AR-05-02 | T-05-13 | A long agent-driven pipeline hang is visible as a stage that never records and is a run-blocker under D-10. Durability work is Phase 6 scope. Severity low, below the block threshold. | plan-time disposition (05-02-PLAN.md) | 2026-08-21 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-21 | 28 | 28 | 0 | gsd-secure-phase (orchestrator, L1 grep-depth) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-21
