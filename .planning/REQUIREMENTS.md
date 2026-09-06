# Milestone v5.3 Requirements: sec-overlay Harness Coverage — Missed RCE

## Source

Defect report from the 2026-09-02 sec-overlay audit run on Tanium Comply:
`.planning/reports/2026-09-02-sec-overlay-missed-rce-coverage-defect-report.md`

9 defects (D-1 through D-9) that caused the harness to miss an authenticated RCE.
The finding: uploaded OVAL XML reaches `new Function` via `dot.template`, RCE as
Comply service identity. All fixes verified against plugin design contracts.
Frozen JSON contract unchanged. Zero new runtime dependencies.

---

## Dependency-Sink Catalog & CWE Mapping

- [ ] **CATALOG-01**: Fix D-3 — add npm entries to `references/dependency-sinks.json` for
      template/eval packages: `dot`, `ejs`, `pug`, `handlebars` (compile with `noEscape`),
      `lodash.template`, `vm2`, `serialize-javascript`, `eval`, `safe-eval`. Manifest names
      include `package.json` and `package-lock.json`. Catalog coverage per ecosystem present
      in any scanned target should be a preflight-reported metric.
- [ ] **CWE-01**: Fix D-1 — add CWE-94 (Code Injection) and CWE-95 (Eval Injection) to
      `clsmap.py` `CWE_CLS`, routing them to `injection` / `ssti` / `expr-eval-rce`.
      Verify semgrep rules `detect-eval-with-expression` and `code-string-concat` resolve
      to a routable class with a class prompt. Add acceptance test: CWE-95 semgrep result
      must resolve to a class in `canonical_classes()` and appear in `agents_to_spawn`.
- [ ] **CWE-02**: Fix D-2 — `security_only` must never drop a semgrep result that declares
      `category: security` or any `cwe` field. Route unmapped-but-security-declared hits to
      `security-other`. Create a per-finding drop ledger (`kb/<drop-ledger>.json`) recording
      every dropped finding's id, file, line, rule id, and reason — not just a count.

## Receipt Kind & Class Floor

- [ ] **RECEIPT-01**: Fix D-4 — add `dependency-catalog:<entry-id>` to `evidence.py`'s
      `_MECHANICAL` receipt set, pinned to a resolved version from the lockfile. Required:
      the catalog entry must cite the sink API and the version range. Update prompt-constants.md
      to match. A finding with `dependency-catalog:npm-dot-template` + lockfile-pinned version
      must reach `confirmed`; a version outside range must be refused.
- [ ] **FLOOR-01**: Fix D-5 — implement a mandatory class floor per language/framework.
      For JS/TS targets, template-injection and dynamic-code-eval on the floor. Floor classes
      must terminate as investigated (with finding, including "no instance found") or excluded
      with cited reason. Floor class neither → force `completeness: partial` and name the class
      in the coverage ledger. Recon may add to the surface; it may not shrink below the floor.

## Route Census & Proof Lane

- [ ] **CENSUS-01**: Fix D-6 — add OpenAPI strategy to `route_frameworks.json`: parse
      `openapi*.yaml` path items + `operationId` → handler binding. Exclude test paths
      from census by default or tag `origin: test`. Validate extracted path shape (leading
      `/`, no SQL, no dotted identifier) and count rejects as extraction-quality metric.
      Where target declares routes no strategy models, surface as explicit coverage gap.
- [ ] **PROVE-01**: Fix D-9 — add `ssti` and `injection` to `prove.AUTO_CONFIRMABLE`.
      Define when the proof lane defaults on: a finding whose only missing receipt is a
      dependency-internal sink is the strongest candidate. Acceptance: with `prove_findings: true`
      and a fixture `ssti` finding on `dot.template`, the lane must reproduce, observe oracle,
      and promote.

## Correlation & Cross-Member Obligations

- [ ] **EDGE-01**: Fix D-7 — add `data-channel` edge kind to correlation: a declared/discovered
      shared channel (DB table.column, queue topic, file artifact) with producer and consumer
      members, with taint semantics. Manifest must declare channels explicitly. `evidence_chain`
      must be populated with producer/consumer `file:line` pair. A verdict with
      `evidence_chain: []` on every row is a null result.
- [ ] **OBLIGATION-01**: Fix D-8 — add cross-member obligation state. A finding whose blocker
      is `caller-out-of-scope` must not be rejectable by member-scoped validator; persist as
      open obligation carrying the out-of-scope symbol. Add `caller-out-of-scope` to
      `reachability` blocker taxonomy as first-class, non-fatal blocker. Correlation must
      attempt to discharge it against sibling members.

---

## Quality Gates (every phase)

- **CODE-REVIEW**: `/gsd:code-review` after each implementation phase
- **VERIFY**: `/gsd:verify-work` after each phase

---

## Out of Scope

- New runtime dependencies (stdlib-only core constraint)
- Changes to frozen JSON contract (`models.py`, `evidence.py`)
- GROW-01 / GROW-02 (deferred to v2)
- New features beyond the 9 defects — remediation only

---

## Traceability

| Phase | REQ-IDs | Defects |
|-------|---------|---------|
| 16 — Dependency-Sink Catalog & CWE Mapping | CATALOG-01, CWE-01, CWE-02 | D-3, D-1, D-2 |
| 17 — Receipt Kind & Class Floor | RECEIPT-01, FLOOR-01 | D-4, D-5 |
| 18 — Route Census & Proof Lane | CENSUS-01, PROVE-01 | D-6, D-9 |
| 19 — Correlation & Cross-Member Obligations | EDGE-01, OBLIGATION-01 | D-7, D-8 |

Coverage: **9 requirements, 9 defects** across **4 phases**. All mapped.

---

*Generated 2026-09-05 from `.planning/reports/2026-09-02-sec-overlay-missed-rce-coverage-defect-report.md`*
