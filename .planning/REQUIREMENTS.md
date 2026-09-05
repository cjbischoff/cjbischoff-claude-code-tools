# Milestone v5.2 Requirements: sec-overlay Defect Remediation

## Source

Defect report from the 2026-09-01 sec-overlay audit run on `ufe`:
`.planning/reports/2026-09-01-sec-overlay-audit-defects.md`

26 defects identified (D1-D26), grouped by component. All fixes verified against
plugin design contracts. Frozen JSON contract (models.py / evidence.py) unchanged.
Zero new runtime dependencies.

---

## CodeQL Guard

- [ ] **CODEQL-01**: Fix D2 — substring `"setup" in text` matches `**/jest.setup.*` glob.
      Replace unanchored substring match with YAML-key-anchored regex pattern.
      `re` already imported at `codeql.py:11`. Test both directions: benign
      `paths-ignore` glob must pass; `setup:` key must reject.

## Prompt-Contract Consistency

- [ ] **CONTRACT-01**: Fix D1 — add `dependency_sinks: list[dict]` field to `ScanProfile`
      dataclass and `scan-profile.schema.json`. Add unknown-key check to
      `validate_profile` so future contract drift produces a validation error,
      not a `TypeError`.
- [ ] **CONTRACT-02**: Fix D9, D11, D12, D23 — create a single consistency test that
      asserts every field name mentioned as an output in `agents/recon.md`,
      `agents/investigate.md`, and `agents/artifact-review.md` exists in the
      corresponding dataclass or schema. Model after `tests/test_references_caps.py`.
      Canonical class list: add `logic-chain` (fix D11). Add `impact` to producer
      prompts (fix D23). Add `attacker`, `privilege`, `exact_request`,
      `exfil_channels` to `Finding` (fix D12).

## Report Renderer

- [ ] **REPORT-01**: Fix D14 — render `patch_diff` for finding with one. Add
      `FindingStatus.FIXED` branch with next-action "fix verified — review and
      merge". Make "(§ below)" link conditional on section existence.
- [ ] **REPORT-02**: Fix D15 — filter route-census output against non-shipping path
      set (test/mock/fixture). Anchor route-extraction patterns to avoid
      non-route false positives. Cap and summarise: top N uncovered routes +
      count dropped.
- [ ] **REPORT-03**: Fix D16 — join coverage-completeness attack-surface table against
      shipping findings by `cls` before rendering "no terminal finding" text.
- [ ] **REPORT-04**: Fix D17 — apply repo-relative path normalisation to coverage
      renderer, matching SARIF writer's existing behaviour.
- [ ] **REPORT-05**: Fix D18 — render `kb/investigate-coverage-notes.md` caveats
      into a prominent Limitations section. Surface `sast_plan.codeql.reason`.
- [ ] **REPORT-06**: Fix D19 — make Triage `Status` column render finding `status`,
      surface `runtime_disposition` as its own column or note.
- [ ] **REPORT-07**: Fix D24 — truncate message on word boundary at higher cap
      (or no cap). Prefer `impact` over `message` for summary cell.

## Vendored Semgrep Rules

- [ ] **SEMGREP-01**: Fix D3 — ship vendored semgrep rules with the plugin, OR make
      preflight's missing-rules state a hard failure the driver refuses to run
      past. Emit `_VENDOR_CMD` as absolute path. Verify exit code propagates.
      Add prefilter warning when a target's language has no matching vendored
      dir and plan silently falls back to `smoke.yaml`.

## Model-Family Independence

- [ ] **MODEL-01**: Fix D21 — rewrite `trace.md:7` and `artifact-review.md:5-7` to
      express model-family diversity relatively ("a DIFFERENT model family than
      the phase that produced these findings"), matching `validate.md:8-10`.

## Driver & Prefilter

- [ ] **DRIVER-01**: Fix D5 — catch `RuntimeError` in `run_deterministic_phase` and
      render as bordered operator message with remediation options. Deduplicate
      backend prefix in joined reason string. Print offending config line.
- [ ] **DRIVER-02**: Fix D22 — emit `{"phase": ..., "skipped": true, "reason": "..."}`
      for phases that don't execute. Have `postflight` surface skipped phases.
      Label cost estimate "deterministic phases only".
- [ ] **DRIVER-03**: Fix D26 — wire `context-ingest` (C1) ahead of `recon` in
      `PHASE_TABLE`. Wire `bugchain` after `trace`. Add startup assertion that
      every prompt in `agents/` is in a phase table or on an explicit
      `_UNWIRED_BY_DESIGN` allowlist.

## Githist Precision

- [ ] **GITHIST-01**: Fix D4 — anchor short acronyms with `\b` in `_SECURITY_GREP`.
      Prefer commits whose subject starts with a `fix`-class conventional-commit
      type when the repo uses them.

## Severity Methodology

- [ ] **SEVERITY-01**: Fix D13 — change precondition counting to use minimum
      conjunctive set across routes (cheapest path's preconditions). State in
      prompt that alternative routes must NOT be concatenated into one list.
      Exclude unverified-from-repo preconditions from tally.

## Artifact-Review Remedy Escalation

- [ ] **REVIEW-01**: Fix D20 — add a `renderer_defect` verdict to `artifact-review.md`
      that fails the phase loudly (or writes a gate file `postflight` treats as
      hard error), so renderer bugs surface as run failures rather than ignored
      re-render requests.

## TOOL_TRUST Absence Clause

- [ ] **TRUST-01**: Fix D25 — add explicit clause to `prompt-constants.md` § TOOL_TRUST:
      a claim that something does NOT exist must be grounded in `ast-grep`,
      structural index, or explicitly-stated search scope; never rest on bare
      piped `rg` returning zero. Generalise the existing semgrep-absence wording.

## Friction & Hygiene

- [ ] **HYGIENE-01**: Fix D6 — wrap `advance()` call in `print(...)` in
      `commands/audit.md`, or have `advance` print one-line confirmation with
      receipt path.
- [ ] **HYGIENE-02**: Fix D7 — have the `/sec-overlay:audit` command emit the absolute
      helpers path, or document the `find`/resolution rule and canonical candidate.
- [ ] **HYGIENE-03**: Fix D8 — set `UV_PROJECT_ENVIRONMENT` to path outside plugin
      tree, or add `.venv/` to plugin ignore rules.
- [ ] **HYGIENE-04**: Fix D10 — ship a `restamp_derived(path, source)` helper in
      `diagram_gate.py`. Mention `check_diagram` in architecture and threat-model
      prompts as pre-submit self-check.

---

## Quality Gates (every phase)

- **CODE-REVIEW**: `/gsd:code-review` after each implementation phase — verify no
  regressions, no contract violations, no security issues.
- **VERIFY**: `/gsd:verify-work` after each phase — validate built features against
  the defect requirements spec.

---

## Out of Scope

- New runtime dependencies (stdlib-only core constraint)
- Changes to frozen JSON contract (`models.py`, `evidence.py`)
- GROW-01 / GROW-02 (deferred to v2)
- New features or capabilities — remediation only

---

## Traceability

| Phase | REQ-IDs | Defects |
|-------|---------|---------|
| 09 — CodeQL Guard & Driver Surface | CODEQL-01, DRIVER-01 | D2, D5 |
| 10 — Prompt-Contract Consistency | CONTRACT-01, CONTRACT-02 | D1, D9, D11, D12, D23 |
| 11 — Report Renderer Overhaul | REPORT-01 through REPORT-07 | D14-D19, D24 |
| 12 — Semgrep Rules & Model Independence | SEMGREP-01, MODEL-01 | D3, D21 |
| 13 — Orphaned Agents & Driver Integrity | DRIVER-02, DRIVER-03, REVIEW-01 | D22, D26, D20 |
| 14 — Methodology & Trust Standards | GITHIST-01, SEVERITY-01, TRUST-01 | D4, D13, D25 |
| 15 — Friction & Hygiene | HYGIENE-01 through HYGIENE-04 | D6, D7, D8, D10 |

Coverage: **22 requirements, 26 defects** across **7 phases**. All mapped.

---

*Generated 2026-09-05 from `.planning/reports/2026-09-01-sec-overlay-audit-defects.md`*
