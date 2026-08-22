# Phase 5: End-to-End Verification (Audit & Review) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-20
**Phase:** 5-End-to-End Verification (Audit & Review)
**Areas discussed:** Audit target selection, Review diff selection, Evidence capture & artifacts, Defect disposition boundary

---

## Audit target selection

| Option | Description | Selected |
|--------|-------------|----------|
| This marketplace repo | Audit cjbischoff-claude-code-tools itself; zero setup, dogfooding | |
| Another local repo | User names a working repo; more realistic surface | ✓ |
| Cloned OSS target | Clone a public repo with known CVEs; shareable evidence | |

**User's choice:** Another local repo — `/Users/christopher/Documents/Development/_hy/mando`
**Notes:** Follow-ups locked: pin to `main` HEAD at run start (record the SHA in receipts); audit the full repo with default excludes for the full AUD-05 coverage denominator.

---

## Review diff selection

| Option | Description | Selected |
|--------|-------------|----------|
| Real historical diff in mando | Same target as the audit; real hunks; opportunistic detection | ✓ |
| Seeded diff with known defects | Deterministic detection proof; synthetic | |
| Both | Real receipt plus seeded proof; more run time | |

**User's choice:** Real historical diff in mando
**Notes:** The planner picks the concrete diff by criteria (merged PR or range, ~5–30 allowlisted TS/TSX files, mixed app/functions, within size caps); the executor resolves the SHA range at run time. Both profiles run on the identical range to evidence the Phase 3 D-10 superset contract.

---

## Evidence capture & artifacts

| Option | Description | Selected |
|--------|-------------|----------|
| Sanitized receipts only | Commit commands, exit codes, seal states, counts, SHAs; no mando internals | ✓ |
| Full artifacts committed | Copy reports and manifests into the phase dir | |
| Redacted artifacts | Copy with manual scrubbing | |

**User's choice:** Sanitized receipts only
**Notes:** The verifier reads mando's `.sec-overlay` sidecar live; receipts cite what to check and where. Sidecar artifacts are retained until the v5.0 milestone ships.

---

## Defect disposition boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Fix run-blockers only | Fix crashes/hangs/gate false-halts in phase; ledger the rest | ✓ |
| Fix nothing, log everything | Halt on any defect; Phase 6 fixes, then re-run | |
| Fix anything small | Executor judgment | |

**User's choice:** Fix run-blockers only
**Notes:** The ledger is `05-DEFECTS.md` in the phase dir (defect, severity, repro command, disposition). A success-criterion failure on real output is a ledger entry plus an honest `gaps_found` verification — never a hidden re-run.

## Claude's Discretion

- Concrete diff selection within the locked criteria.
- Receipt document structure, following the Phase 1 evidence format.

## Deferred Ideas

- Handing audit findings to the mando team (triage, issue filing) — outside this milestone.
- Seeded-defect detection benchmark diff — possible fixture-based regression suite in a later milestone.
