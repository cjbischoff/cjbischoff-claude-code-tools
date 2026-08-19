---
phase: 03-rule-matching-review-modes
verified: 2026-08-18T22:00:00Z
status: gaps_found
score: 4/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "The reflection filter runs once per file after positioning and the hunk gate, retracts findings only, fails open on LLM error, and cannot itself produce a `confirmed` disposition; a general-defect finding without a Tier-1 mechanical receipt ships as `unconfirmed`/`needs-deployment-testing`, never `confirmed` (Roadmap SC #5; REV-02, REV-03)"
    status: failed
    reason: >
      Two independent, mechanically-confirmed defects inside this one success criterion.
      (1) Reflection's retract-only verdict never reaches the findings the pipeline reports:
      `cli.py`'s `run_review` calls `apply_verdict(kept_for_file, {}, path=record.path)` per
      file, but discards the returned `_kept_for_file` list entirely — only the `retractions`
      half is kept (`reflection_retractions.extend(retractions)`). The `review_findings` value
      passed to `write_report` is `apply_profile`'s pre-reflection kept output, never
      reflection's post-retraction list. `report.py`'s own docstring confirms this:
      `review_findings: :func:`review_findings.apply_profile`'s kept output (REV-01)` — reflection
      is not in that chain. Proven behaviorally, not just by static reading: the existing test
      `tests/test_review_live.py::test_reflection_retraction_removes_a_live_finding` (passing,
      re-run in this verification) fakes a retraction and then asserts
      `ledger["review_findings"][0]["id"]` is truthy — i.e. the "retracted" finding is still
      present in the reported ledger. The test's own inline comment concedes this: "review_findings
      still lists it (profile output), reflection removes it downstream of that ledger key —
      proven by the retraction entry itself, not an absent finding." A retraction is recorded
      as having happened while the finding it names ships anyway — the opposite of "retracts
      findings only."
      (2) The receipt-gate disposition ladder (`findings_gate.disposition_without_receipt`,
      which correctly implements the static-checkable vs runtime-dependent split) is never
      invoked from the production path. `grep -rn "disposition_without_receipt"` across every
      `.py` file shows it referenced only in its own test file
      (`tests/test_findings_gate.py`). `review_findings.apply_profile` hardcodes
      `disposition=UNCONFIRMED_DISPOSITION` unconditionally (`review_findings.py:146`) for every
      kept finding regardless of `defect_class`, confirmed by the passing test
      `test_apply_profile_never_assigns_a_confirmed_disposition`, which locks in the (incorrect)
      universal `unconfirmed` behavior as expected rather than asserting the required
      `needs-deployment-testing` split for `thread-safety`. A general-defect finding whose class
      is runtime-dependent (e.g. thread-safety) ships as `unconfirmed`, never
      `needs-deployment-testing`, when it has no Tier-1 receipt.
    artifacts:
      - path: "plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py"
        issue: "run_review's reflection loop discards apply_verdict's kept-findings half (`_kept_for_file`); write_report receives apply_profile's pre-reflection review_findings, so a retraction never removes the finding from the reported/ledgered output"
      - path: "plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_findings.py"
        issue: "apply_profile (line ~146) hardcodes disposition=UNCONFIRMED_DISPOSITION for every kept finding; never calls findings_gate.disposition_without_receipt, so the required unconfirmed/needs-deployment-testing split by defect_class never happens"
      - path: "plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/findings_gate.py"
        issue: "disposition_without_receipt is correctly implemented (static-checkable vs runtime-dependent partition of GENERAL_DEFECT_CLASSES) but is dead code — zero production call sites"
    missing:
      - "Wire cli.run_review so the per-file result of apply_verdict (the retained/kept list, not just the retraction records) becomes the review_findings passed to write_report — a retracted finding must not appear in the reported/ledgered kept-findings list"
      - "Call findings_gate.disposition_without_receipt from review_findings.apply_profile (or an equivalent call site before write_report) so a general-defect finding without a Tier-1 receipt gets unconfirmed for static-checkable classes and needs-deployment-testing for runtime-dependent classes, instead of always unconfirmed"
      - "Update test_apply_profile_never_assigns_a_confirmed_disposition (or add a sibling test) to assert the needs-deployment-testing disposition for a thread-safety finding once the ladder is wired, and add/adjust a live-CLI test asserting a reflection-retracted finding is absent from ledger[\"review_findings\"]"
human_verification:
  - test: "Trigger an exception in reflection's per-file loop for one file among several reviewed files in the same run (e.g. monkeypatch apply_verdict to raise for file B only) and confirm files A and C still get their normal review_findings/retractions while B records a reflection-skipped marker."
    expected: "Only the failing file's reflection pass is skipped; every other file's reflection result (retractions, kept findings) is unaffected — the per-file loop isolates the failure."
    why_human: "03-05-PLAN.md's must_haves marks this truth verification: backstop (non-inferable from presence/wiring alone) and no test in the suite (tests/test_review_live.py, tests/test_reflection.py) exercises multi-file failure isolation — only single-file scenarios are covered. Per the honest-verifier discipline, a backstop truth abstains without explicit test evidence rather than being inferred from cli.py's per-record try/except shape."
---

# Phase 3: Rule Matching & Review Modes Verification Report

**Phase Goal:** The review verb selects the right per-language checklist for every file, runs in security or general-defect scope on command, and never lets an LLM judgment override the mechanical receipt gate.
**Verified:** 2026-08-18T22:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `rule_glob.py` resolves a file's rule via ordered, brace-expanded, `**`-aware PathRules, four-layer resolution, `--exclude` append, `merge_system_rule` fixed-header concatenation | VERIFIED | `rule_glob.py` (524 lines, read in full): `expand_braces`, `glob_match` (lower-cased, `**`-aware, `fnmatch.fnmatchcase` per segment), `build_resolution` (4-layer), `merge_with_system_rule` (`SYSTEM_RULE_HEADER`/`USER_RULE_HEADER`). `tests/test_rule_docs.py` — 36 passed. |
| 2 | Rule-file reads resolve symlinks, require resolved path under repo root, restrict extensions to `.md`/`.txt`/`.markdown`, reject files over 512 KB | VERIFIED | `read_rule_file_safe` in `rule_glob.py`: strict symlink resolve, extension allowlist, `is_relative_to` repo-root containment, capped read at `MAX_RULE_FILE_BYTES + 1 = 524289` bytes. WR-03 (TOCTOU between resolve and read) noted as a non-blocking warning — see Anti-Patterns. |
| 3 | Per-language rule docs exist for go, java, python, php, rust, ts/js/tsx/jsx, kotlin, swift, and default, each naming NPE/thread-safety/injection/resource-leak/error-swallowing with exclusions | VERIFIED | `ls plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/` — all 9 files present (`default.md`, `go.md`, `java.md`, `kotlin.md`, `php.md`, `python.md`, `rust.md`, `swift.md`, `ts_js_tsx_jsx.md`) plus `README.md`. Conformance asserted by `tests/test_rule_docs.py` (36 passed). |
| 4 | `review --profile security` reproduces existing gate A-E behavior exactly; `--profile general` additionally surfaces NPE/thread-safety/XSS/SQLi findings gates A/B would drop, gates C/D/E still enforced | VERIFIED | `tests/test_review_profiles.py`: `test_dual_run_security_profile_matches_committed_baseline_no_regression` (against committed `review_profiles_security_baseline.json`, captured at `245d9e7`), `test_dual_run_general_profile_is_a_strict_superset_of_the_security_baseline`, `test_general_profile_drops_gates_c_d_e_unconditionally_even_for_allowlisted_class`. All passing (targeted run: 89 passed across the review-profile/live/reflection/gate/agent test files). |
| 5 | Reflection filter runs once per file after positioning/hunk gate, retracts findings only, fails open, cannot produce `confirmed`; a general-defect finding without a Tier-1 receipt ships `unconfirmed`/`needs-deployment-testing`, never `confirmed` | ✗ FAILED | Two confirmed sub-failures — see Gaps Summary and frontmatter `gaps`. `apply_verdict` itself (unit-level) is correctly retract-only with the protected-subject veto and fail-open behavior, but (a) its retraction never reaches the reported `review_findings` list (`cli.py`'s per-file loop discards the kept half), proven by the existing passing test `test_reflection_retraction_removes_a_live_finding`'s own assertion and inline comment; (b) the required `unconfirmed`/`needs-deployment-testing` disposition split (`findings_gate.disposition_without_receipt`) is dead code, never called from `apply_profile`, which hardcodes `unconfirmed` unconditionally. |

**Score:** 4/5 truths verified.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| RULE-01 | 03-01 | Ordered, brace-expanded, `**`-aware path matching, first-match-wins else default | VERIFIED | `rule_glob.glob_match`/`build_file_filter`; tests pass |
| RULE-02 | 03-02 | Four-layer rule resolution + `--exclude` append | VERIFIED | `rule_glob.build_resolution`; tests pass |
| RULE-03 | 03-02 | Rule-file read safety gate (symlink/root/ext/size) | VERIFIED | `read_rule_file_safe`; WR-03 TOCTOU is non-blocking |
| RULE-04 | 03-02 | `merge_system_rule` fixed-header concatenation | VERIFIED | `merge_with_system_rule` |
| RULE-05 | 03-03 | 9 per-language rule docs, 5 defect classes, exclusions | VERIFIED | All 9 files present; conformance tests pass |
| REV-01 | 03-04 | Security profile exact reproduction; general profile superset | VERIFIED | Committed-baseline no-regression + superset tests pass |
| REV-02 | 03-05 | Reflection: per-file, after position/hunk gate, retract-only, protected-subject veto, fails open | ✗ BLOCKED | `apply_verdict` itself correct at unit level, but its retraction is discarded by `cli.run_review` before `write_report` — the pipeline-level "retracts findings" guarantee is broken (CR-01) |
| REV-03 | 03-05 | Receipt gate sole authority on `confirmed`; unconfirmed/needs-deployment-testing split for no-receipt general-defect findings | ✗ BLOCKED | The "never produces `confirmed`" half holds (no code path in `reflection.py`/`review_findings.py` assigns `confirmed`). The disposition-split half fails: `disposition_without_receipt` is dead code (WR-01) |

**Orphaned requirements check:** `.planning/REQUIREMENTS.md`'s Phase 3 section (RULE-01–05, REV-01–03) is bounded above by the Phase 2 `POS-*` requirements and below by the Phase 4 `SCALE-*` requirements — no additional Phase-3-mapped requirement ID exists outside the 8 already covered above. No orphans found.

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `sec_overlay/rule_glob.py` | 4-layer rule resolution, safe rule-file read, brace/glob matching, merge headers | VERIFIED | Substantive, wired into `review_agent.py` (`resolve_rule_doc` → `render_review_prompt` → `{{system_rule}}`) |
| `rules/rule_docs/*.md` (9 files) | Per-language checklists | VERIFIED | All present, conformance-tested |
| `sec_overlay/review_findings.py` | `apply_profile`, `classify`, `GENERAL_DEFECT_CLASSES` | ⚠ PARTIAL | Profile gating (REV-01) fully correct and wired; disposition assignment (REV-03) is a stub — always `UNCONFIRMED_DISPOSITION`, never calls the ladder function |
| `sec_overlay/reflection.py` | `apply_verdict`, `PROTECTED_SUBJECT_CLASSES`, retract-only contract | VERIFIED (unit) / ✗ NOT WIRED (pipeline) | Module itself is correct and well-tested in isolation; its output is discarded by its sole caller (`cli.py`) before reaching the report |
| `sec_overlay/findings_gate.py` | `disposition_without_receipt` | ✗ ORPHANED | Correctly implemented, tested directly in `test_findings_gate.py`, but zero production call sites |
| `sec_overlay/cli.py` (`run_review`) | Live pipeline wiring: position gate → apply_profile → apply_verdict → receipt gate, in that order, feeding a coherent `review_findings` | ✗ HOLLOW | Calls all four in sequence, but the `apply_verdict` step's kept-findings output is thrown away; `review_findings` downstream is the pre-reflection value |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `rule_glob.resolve_rule_doc` | `review_agent.render_review_prompt` | `{{system_rule}}` substitution | VERIFIED | Confirmed via `review_agent.py` read; resolved text reaches the rendered prompt, not merely attached to a record |
| SKILL.md → subagent → `review_agent.recorded_return_source` | `cli.run_review` | disk-persisted agent returns | VERIFIED | `tests/test_review_live.py` exercises this path with recorded returns |
| `review_agent.parse_review_response` | `review_position_gate` | parsed findings list | VERIFIED | Live findings replace the hardcoded `[]`; confirmed by `test_profile_split_null_dereference_security_excludes_general_includes` |
| `cli.run_review` composition | position gate → `apply_profile` → `apply_verdict` → `findings_gate` | sequential calls in `cli.py` | ✗ NOT WIRED | Calls occur in this order, but `apply_verdict`'s kept-findings return value is discarded (`_kept_for_file` unused); `review_findings` passed onward is `apply_profile`'s pre-reflection output, so a retraction never removes a finding from what the receipt gate/report actually sees — directly contradicting 03-06-PLAN.md's own key_link claim ("so the live findings traverse every gate the phase built") and 03-06-SUMMARY.md's identical claim |
| `findings_gate.validate_findings` | `review_findings.GENERAL_DEFECT_CLASSES` | single-owner class list | VERIFIED (class list) / ✗ NOT WIRED (disposition ladder) | The class-list ownership claim holds; the disposition-ladder half of this key_link (`disposition_without_receipt` being consulted) does not — it is never called |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `sec_overlay/cli.py` (run_review) | ~301-310 | Reflection's kept-findings return value discarded; only retractions extracted | Blocker | CR-01 — see Gaps |
| `sec_overlay/review_findings.py` | ~146 | `disposition=UNCONFIRMED_DISPOSITION` hardcoded regardless of `defect_class` | Blocker | WR-01 — see Gaps |
| `sec_overlay/findings_gate.py` | 45-67 | `validate_findings` silently rewrites `receipt_tier` on disk as an undisclosed side effect | Warning | Non-blocking per 03-REVIEW.md (WR-02); does not affect the gate's confirm/deny correctness, only an unannounced mutation. Not treated as a phase-goal blocker. |
| `sec_overlay/rule_glob.py` | `read_rule_file_safe` | TOCTOU window between symlink-resolve and read | Warning | Non-blocking per 03-REVIEW.md (WR-03); low practical severity (local rule-file source, not attacker-supplied over a network boundary in the reviewed threat model) |
| `sec_overlay/cli.py` (`run_review` docstring) | — | Reflection wiring undocumented in the function's own docstring | Info | Non-blocking (IN-01); documentation completeness only |

No `TBD`/`FIXME`/`XXX` debt markers found in any of the 7 core files scanned (`rule_glob.py`, `reflection.py`, `review_findings.py`, `findings_gate.py`, `review_agent.py`, `cli.py`, `report.py`).

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Full targeted test suite (rule/review/reflection/gate modules) | `uv run pytest tests/test_review_profiles.py tests/test_review_live.py tests/test_reflection.py tests/test_findings_gate.py tests/test_review_agent.py -q` | 89 passed | PASS |
| Rule-doc conformance | `uv run pytest tests/test_rule_docs.py -q` | 36 passed | PASS |
| CR-01 reproduction (existing test) | `uv run pytest tests/test_review_live.py::test_reflection_retraction_removes_a_live_finding -q` | 1 passed — and the assertion it passes on (`ledger["review_findings"][0]["id"]` truthy after a fake retraction) empirically proves the retracted finding remains in the reported ledger | FAIL (behavior confirms the defect, not the goal) |
| Full-suite baseline | `uv run pytest -q` (from `helpers/`) | 1161 passed, 2 failed (`test_bench.py::test_seed_corpus_is_valid`, `test_preflight.py::...vendored_rules`) | PASS — matches the documented, pre-existing environmental baseline; not counted as a gap |
| Frozen contract check | `git log --oneline -1 -- .../models.py .../evidence.py` | `b70beb1` (pre-Phase-3 commit); no Phase-3 commit touches either file | PASS |

### Gaps Summary

Phase 3 delivers RULE-01 through RULE-05 and REV-01 cleanly — rule matching, four-layer resolution,
the safety gate, the nine per-language rule docs, and the security/general profile split are all
substantively implemented, wired end to end, and covered by passing tests including a
committed-baseline no-regression proof.

Success Criterion #5 (REV-02 + REV-03) fails on two independent, mechanically confirmed points,
both inside the same reflection/disposition wiring that Wave 5 (03-05) and Wave 6 (03-06) were
responsible for connecting:

1. **CR-01 — reflection retractions never reach the reported findings.** `reflection.apply_verdict`
   is implemented correctly (retract-only, protected-subject veto, fails open) and is unit-tested
   correctly in isolation. But `cli.run_review`'s per-file loop discards the function's kept-findings
   return value and only keeps the retraction *records* — the `review_findings` list that actually
   reaches `write_report` (and `review_ledger.json`) is `apply_profile`'s pre-reflection output. A
   file's existing, passing test (`test_reflection_retraction_removes_a_live_finding`) proves this
   directly: after faking a retraction, it asserts the "retracted" finding's id is still present in
   `ledger["review_findings"]`, and its own inline comment concedes as much. This directly
   contradicts 03-05-PLAN.md's must-have ("Every retraction lands in the dropped-findings ledger...")
   in its practical effect and 03-06-PLAN.md's key_link claim that the live findings "traverse every
   gate the phase built" — 03-06-SUMMARY.md repeats this same incorrect claim about the pipeline's
   fixed call order actually removing retracted findings.

2. **WR-01 — the no-receipt disposition ladder is dead code.** `findings_gate.disposition_without_receipt`
   correctly partitions `GENERAL_DEFECT_CLASSES` into static-checkable (→ `unconfirmed`) and
   runtime-dependent (→ `needs-deployment-testing`) classes, and is directly unit-tested. But it has
   zero production call sites — `review_findings.apply_profile` hardcodes `UNCONFIRMED_DISPOSITION`
   for every kept finding regardless of class, and the existing test
   `test_apply_profile_never_assigns_a_confirmed_disposition` locks in this incorrect universal
   behavior rather than asserting the required split for a runtime-dependent class like
   `thread-safety`.

Neither gap is a judgment call or a matter of interpretation — both are demonstrated by reading the
production call graph (`grep` confirms zero non-test callers of `disposition_without_receipt`; direct
read of `cli.py` confirms the discarded return value) and, for CR-01, by the project's own passing
test asserting the buggy behavior as expected. Both sit squarely inside "never lets an LLM judgment
override the mechanical receipt gate" — not because an LLM verdict is overriding the gate today (it
isn't; `verdict={}` always in the current review-agent wiring, so CR-01 is currently latent/invisible
in real output), but because the retraction mechanism that is supposed to let the mechanical receipt
gate remain sole authority over `confirmed` has no observable effect once real reflection dispatch is
wired in a later phase, and the disposition split the receipt gate is supposed to enforce for
general-defect findings never executes.

WR-02 (silent `receipt_tier` rewrite) and WR-03 (rule-file read TOCTOU) are non-blocking per
03-REVIEW.md's own severity assessment, which this verification concurs with — neither affects the
phase goal's core guarantee.

One `must_haves` truth in 03-05-PLAN.md is explicitly `verification: backstop` (per-file reflection
failure isolation across multiple files in one run) and is not confirmed by any test in the suite —
routed to human verification rather than inferred from the code's per-record try/except shape alone.

---

_Verified: 2026-08-18T22:00:00Z_
_Verifier: Claude (gsd-verifier)_
