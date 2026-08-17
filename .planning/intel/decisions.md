# Decisions (from ADR-classified docs)

One ADR-classified document exists in this ingest set. No decision is locked.
All source paths are relative to the repository root.

## ADR-2026-08-04: Adopt select aghast/OpenAnt capabilities natively; reject SDK dependency
- source: plugins/sec-overlay/skills/sec-overlay/docs/plans/2026-08-04-aghast-openant-adoption-design.md
- status: proposed (doc status: "approved (design), pending implementation plan" — not Accepted, not locked)
- decision: Re-implement four capabilities natively inside sec-overlay: (A) custom check
  bundles under `.sec-overlay/checks/`, (B) structured-output hardening via
  `finding.schema.json` validation in `findings_gate.py`, (C) a cross-target
  anti-hallucination guard in `investigate.md`, (D) deterministic entry-point detection in
  `graph.py` Tier-1. Neither external tool is adopted as a dependency; sec-overlay stays
  stdlib-only.
- explicitly rejected: Anthropic SDK / direct API dependency; external multi-repo check
  registry (deferred; in-repo bundles only); OpenAnt's LLM-enhanced dataset and
  attacker-simulation stages; any change to Task-tool subagent dispatch.
- scope: sec-overlay skill (`skills/sec-overlay/` only)
