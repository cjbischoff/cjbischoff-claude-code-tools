# Synthesis Summary

Ingest of 50 classified planning documents (mode: new, precedence ADR > SPEC > PRD >
DOC). All documents concern the sec-overlay plugin and this marketplace repo; the bulk
are historical, completed design/plan pairs for sec-overlay (2026-08-02 through
2026-08-16).

## Doc counts by type

- ADR: 1
- SPEC: 30
- PRD: 0
- DOC: 19
- UNKNOWN: 0

## Decisions

- Locked: 0
- Proposed: 1 — ADR-2026-08-04 (adopt aghast/OpenAnt capabilities natively; Anthropic
  SDK and external check registry explicitly rejected). See `decisions.md`.

## Requirements

- 0 extracted (no PRD in the set). `requirements.md` records the absence.

## Constraints

- 30 SPEC entries in `constraints.md`. Type breakdown: api-contract 12, schema 7,
  protocol 7, nfr 4.
- Recurring hard invariants: stdlib-only core; frozen models.py/evidence.py JSON
  contract (Go-mirrored); fingerprint() identity; receipt-backed confirmation
  (tool-receipt bar never bypassed); read-only correlation layer; Mermaid caps and
  CVSS v4.0 pin (latest standards).
- Latest authorities by area: architecture/threat-model phases + CVSS v4.0 —
  2026-08-16 standards design/source; invocation — 2026-08-16 invocation design;
  pipeline correctness — 2026-08-15 defect-remediation design (T-themes);
  cross-repo correlation — 2026-08-08 Spec B.

## Context

- 19 DOC entries in `context.md`: 2 dogfooding observation logs and 17 historical
  implementation plans, grouped by workstream with parent-spec pointers.

## Conflicts

- 0 blockers, 0 competing variants, 1 warning, 7 info (auto-resolved / notes).
- The single WARNING: the 2026-08-11 kb-redesign design references a 2026-08-09 spec
  that is not in the ingest set.
- Detail: `.planning/INGEST-CONFLICTS.md`.

## Files

- `.planning/intel/decisions.md`
- `.planning/intel/requirements.md`
- `.planning/intel/constraints.md`
- `.planning/intel/context.md`
- `.planning/INGEST-CONFLICTS.md`
