# Phase 18: Route Census & Proof Lane — Context

**Gathered:** 2026-09-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix the two medium-severity harness defects (D-6, D-9) that block route discovery
and automated confirmation for template-injection/code-evaluation findings.

- **CENSUS-01 (D-6):** Add OpenAPI-first strategy to route census, exclude test
  paths, validate path shapes. Framework regexes remain as fallback.
- **PROVE-01 (D-9):** Add `ssti` and `injection` to `prove.AUTO_CONFIRMABLE`.

</domain>

<decisions>
## Implementation Decisions

### Route Census — OpenAPI-First Strategy (D-6)

- **D-01:** Use a two-strategy approach, ordered: OpenAPI first, framework regex
  fallback second. Look for `openapi.yaml`, `openapi.yml`, or `openapi.json` at
  common locations (repo root, `docs/`, `spec/`, `.`). Parse with stdlib `json`
  or simple YAML header parsing (no new runtime dependency).
- **D-02:** OpenAPI extraction: extract `paths` → method → `operationId`. The
  handler file is resolved by matching `operationId` against known conventions
  (e.g., `kebab-case-id` → `src/handlers/kebab-case-id.ts`) or by recording the
  operationId as the identifier and leaving handler resolution to investigate.
- **D-03:** Test-file exclusion: filter entries whose file path matches
  `*test*`, `*.spec.*`, `__mocks__`, `__fixtures__`, `e2e/`, `.stories.`.
  Tag excluded entries `origin: test` rather than silently dropping them, so
  coverage reports can show filtered counts.
- **D-04:** Path shape validation: reject paths matching SQL keywords
  (`SELECT`, `INSERT`, `FROM`), dotted identifiers (like `HeapProfiler.take`),
  or bare numbers. Rejected entries count as extraction-quality metric.
- **D-05:** The existing 7 framework regex patterns remain as fallback when no
  OpenAPI spec is found. No new framework-specific patterns should be added —
  future frameworks should publish OpenAPI specs.

### Proof Lane — Class Coverage (D-9)

- **D-06:** Add `"ssti"` and `"injection"` to `prove.AUTO_CONFIRMABLE`. These
  classes' oracle is wrapper-decidable: compile attacker-supplied text through
  the real engine in a sandboxed child process; oracle = observable side effect.
- **D-07:** A finding whose only missing receipt is a dependency-internal sink
  is the strongest candidate for proof-by-execution. If the finding's class is
  in AUTO_CONFIRMABLE AND the only missing Tier-1 receipt is dependency-internal
  (no first-party sink line), the proof lane should default to enabled for that
  finding even when `prove_findings` is not explicitly `true`.

</decisions>

<canonical_refs>
## Canonical References

- `.planning/reports/2026-09-02-sec-overlay-missed-rce-coverage-defect-report.md` — D-6, D-9 details
- `plugins/sec-overlay/skills/sec-overlay/references/route-frameworks.json` — Current 7 framework patterns
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/prove.py:27-43` — AUTO_CONFIRMABLE, HARNESS_ONLY
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/route_census.py` — Current census implementation
</canonical_refs>

<code_context>
## Existing Code Insights

### Route Census
- `route_census.py` already has `_SKIP` dirs and regex-based extraction
- `route-frameworks.json` has 7 framework entries — these stay as fallback
- No YAML parsing dependency exists; route_census uses stdlib only
- OpenAPI spec is JSON-compatible (OpenAPI 3.0 can be parsed with json module;
  OpenAPI 3.1 uses YAML but common formats like Swagger 2.0 ship openapi.json)

### Proof Lane
- `prove.py` has `AUTO_CONFIRMABLE` frozenset with 5 classes
- `prove_enabled()` checks `scan_options.prove_findings`
- `PROVE_TOOLCHAINS` already includes `node` which covers JS template engines

</code_context>

<deferred>
## Deferred Ideas

- Framework-agnostic route discovery beyond OpenAPI (e.g., AST-based endpoint
  extraction for frameworks without OpenAPI specs) — future work.

</deferred>

---

*Phase: 18-Route Census & Proof Lane*
*Context gathered: 2026-09-06*
