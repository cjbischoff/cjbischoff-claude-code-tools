# Phase 16: Dependency-Sink Catalog & CWE Mapping — Context

**Gathered:** 2026-09-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix the three data/logic defects that cause the sec-overlay harness to miss
code-injection findings at the earliest stage:

- **CATALOG-01 (D-3):** Add npm ecosystem coverage to the dependency-sink
  catalog using an abstract category-based approach (not per-library entries).
- **CWE-01 (D-1):** Add CWE-94 (Code Injection) and CWE-95 (Eval Injection)
  to `clsmap.py` `CWE_CLS`, routing them to the `injection` class.
- **CWE-02 (D-2):** Fix `security_only` filter to never drop semgrep results
  that declare `category: security` or any `cwe` field. Route unmapped-but-
  security-declared hits to `security-other`.

</domain>

<decisions>
## Implementation Decisions

### CWE-94/95 → Class Mapping (D-1)

- **D-01:** CWE-94 (Code Injection) and CWE-95 (Eval Injection) route to the
  `injection` class in `clsmap.py` `CWE_CLS`. This is consistent with MITRE
  CWE-74 (Injection parent), OWASP A03:2021, and the existing `injection`
  class at `agents/classes/injection.md`. — **Reversibility:** reversible —
  changing class routing later only affects future runs, not persisted data.
- **D-02:** The `injection` class already exists at
  `agents/classes/injection.md` with boundary documentation at
  `agents/classes/ssti.md:26` ("Raw eval/exec on attacker text with no
  template engine → cls: injection"). The class is defined but was
  unreachable because no CWE and no rule-id entry routes anything to it.
  This decision makes it reachable.
- **D-03:** The semgrep rules `detect-eval-with-expression` and
  `code-string-concat` (both CWE-95) must resolve to the `injection` class
  deterministically via `cls_from_semgrep_meta` — currently they fall to
  `unknown` because CWE-95 is absent from the map and their rule IDs don't
  match `_RULE_ID_CLS`. Both the CWE map entry AND a `_RULE_ID_CLS` entry
  for rule-id substrings like `eval`/`code-string-concat` should be added.

### Dependency-Sink Catalog — Abstract Approach (D-3)

- **D-04:** The catalog should use an abstract category-based strategy rather
  than per-library entries. For each ecosystem (npm, go, python, etc.),
  define sink categories (template-engine, expression-evaluator,
  code-evaluation, etc.) that match when ANY dependency is present in the
  manifest. — **Reversibility:** reversible — catalog entries are data, not
  contract.
- **D-05:** The npm ecosystem entry uses `"strategy": "match-any"` — when
  `package.json` or `package-lock.json` is detected AND any dependency is
  present, the catalog routes to `ssti` / `injection` based on the
  category. The per-package granularity is delegated to the investigate
  agent (guided by prompts), not the catalog.
- **D-06:** Define two npm categories initially:
  - `npm-template-injection` → `cls: ssti` — covers template engines that
    compile from strings (dot, ejs, pug, handlebars with noEscape,
    lodash.template)
  - `npm-code-evaluation` → `cls: injection` — covers eval-based libraries
    (vm2, serialize-javascript, eval, safe-eval, and bare `new Function`
    usage)
- **D-07:** The match-any strategy fires when ANY dependency in `package.json`
  exists. The indicator list guides the investigate agent but does not gate
  routing. Preflight should report "npm detected, template/eval coverage:
  <category-list>" as a coverage metric.

### security_only Filter Policy (D-2)

- **D-08:** The `security_only` filter must never drop a semgrep result that
  declares `category: security` or any `cwe` field. Check is OR — either
  condition keeps the finding. — **Reversibility:** reversible — filter
  logic, not contract.
- **D-09:** Results that declare neither `category: security` nor any `cwe`
  may still be dropped, BUT only from rulesets that are not under
  `lang/security/`. Results from `lang/security/` rulesets always survive
  regardless of metadata. — **Reversibility:** reversible.
- **D-10:** Unmapped-but-security-declared semgrep findings (those whose
  CWE resolves to nothing in CWE_CLS) route to `security-other` class
  instead of being dropped. The general-triage lane already handles
  `security-other` and ran in the audited Comply run.

### Drop Ledger

- **D-11:** A persistent drop ledger at `kb/drop-ledger.json` records every
  semgrep finding that `security_only` drops, with fields: `rule_id`,
  `file`, `line`, `cwe` (if any), `metadata.category`, and `reason`.
  This makes the integer `dropped_nonsecurity` into actionable data.
  — **Reversibility:** reversible — additive, no existing code depends on it.

</decisions>

<canonical_refs>
## Canonical References

### Defect report
- `.planning/reports/2026-09-02-sec-overlay-missed-rce-coverage-defect-report.md` — Full defect report with D-1, D-2, D-3 details
- `.planning/REQUIREMENTS.md` — Requirements CATALOG-01, CWE-01, CWE-02

### Existing taxonomy and code
- `plugins/sec-overlay/skills/sec-overlay/agents/classes/injection.md` — Existing injection class definition
- `plugins/sec-overlay/skills/sec-overlay/agents/classes/ssti.md:26-30` — Boundary between ssti and injection
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/clsmap.py:17-30` — CWE_CLS map, needs CWE-94/95
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/prefilter.py:289-296` — security_only filter
- `plugins/sec-overlay/skills/sec-overlay/references/dependency-sinks.json` — Current catalog (6 entries, npm absent)
- `plugins/sec-overlay/skills/sec-overlay/references/attack-classes.md` — Canonical class list

### External references (taxonomy)
- MITRE CWE-94 / CWE-95 — Code Injection / Eval Injection (parent CWE-74 Injection)
- OWASP Top 10 2021 A03:2021 — Injection
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `dependency_sinks.py` — `match_manifests` and `indicator_classes` already work generically; need npm manifest support (`package.json`/`package-lock.json`) and match-any strategy
- `partition.reconcile_plan` — Already merges `matched_classes + indicator_classes`; match-any entries feed into matched_classes when any dependency present

### Established Patterns
- CWE_CLS map in `clsmap.py` — One CWE → one class; CWE-94 and CWE-95 each need entries
- `_RULE_ID_CLS` in `clsmap.py` — Substring match on semgrep rule IDs; evalu/eval pattern would catch `detect-eval-with-expression`
- `security_only` in `prefilter.py` — Currently drops `cls == "unknown"` semgrep findings unconditionally; need to check metadata.cwe and metadata.category before dropping

### Integration Points
- `clsmap.py` — Add CWE-94/95 to CWE_CLS, add eval-related patterns to _RULE_ID_CLS
- `prefilter.py` — Modify security_only filter to preserve CWE-declaring results
- `dependency-sinks.json` — Add npm categories with match-any strategy
- `dependency_sinks.py` — Add npm manifest support, add match-any strategy logic

</code_context>

<specifics>
## Specific Ideas

- The `dot.template → new Function` finding from the Comply audit is the reference case. Any fix must be verified against that exact dataflow: `package.json` declares `"dot": "1.1.3"`, first-party code calls `dot.template(template)`, the sink is inside the dependency. The acceptance tests from the defect report are the verification baseline.
- All three sub-defects (D-1, D-2, D-3) are independent in terms of code paths but all three are needed for a semgrep CWE-95 finding to surface. They can be implemented in any order.

</specifics>

<deferred>
## Deferred Ideas

- D-4 (RECEIPT-01, dependency-catalog receipt kind) — belongs in Phase 17
- D-5 (FLOOR-01, mandatory class floor) — belongs in Phase 17

</deferred>

---

*Phase: 16-Dependency-Sink Catalog & CWE Mapping*
*Context gathered: 2026-09-06*
