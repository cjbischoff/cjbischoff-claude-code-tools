---
phase: 03-rule-matching-review-modes
plan: 05
subsystem: sec-overlay diff-review reflection filter and receipt-gate disposition ladder
tags: [reflection, retract-only, protected-subject-veto, never-silent-ledger, disposition-ladder, D-12, D-14, D-15, D-16, REV-02, REV-03]

dependency graph:
  requires: [03-04]
  provides:
    - "sec_overlay.reflection: render_reflection_prompt, validate_verdict, apply_verdict, ReflectionResponseError, ReflectionSkip, ReflectionRetraction, PROTECTED_SUBJECT_CLASSES"
    - "sec_overlay.report: render_reflection_skipped_section, REFLECTION_SKIPPED_HEADING, to_markdown(reflection_skips=)"
    - "sec_overlay.findings_gate: STATIC_CHECKABLE_CLASSES, RUNTIME_DEPENDENT_CLASSES, disposition_without_receipt"
    - "agents/review-filter.md prompt"
  affects:
    - "SKILL.md diff-scoped review dispatch"
    - "cli.py run_review (already wired to apply_verdict from a prior plan; this plan completes the filter it calls)"

tech-stack:
  added: []
  patterns:
    - "Retract-only LLM-verdict filter: parsing enforces the contract, not a request in the prompt alone (D-16)"
    - "Mechanical protected-subject veto backstops the same veto stated in the prompt"
    - "Never-silent ledger: every retraction, refusal, and skip produces an entry; both zero cases render an explicit sentence (D-14/D-15)"
    - "Receipt-gate disposition ladder: a general-defect finding without a Tier-1 receipt ships as unconfirmed or needs-deployment-testing per class, never confirmed (D-12)"

key-files:
  created:
    - plugins/sec-overlay/skills/sec-overlay/agents/review-filter.md
  modified:
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/reflection.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/findings_gate.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_reflection.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_findings_gate.py
    - plugins/sec-overlay/skills/sec-overlay/SKILL.md
    - plugins/sec-overlay/skills/sec-overlay/README.md
    - plugins/sec-overlay/skills/sec-overlay/agents/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md
    - plugins/sec-overlay/CHANGELOG.md
    - plugins/sec-overlay/.claude-plugin/plugin.json

decisions:
  - "Injection is assigned to STATIC_CHECKABLE_CLASSES (ships unconfirmed) explicitly, not by falling through a default — its sink is the same reachability target semgrep/codeql already check, unlike a thread-safety race that only manifests under real concurrent load."
  - "disposition_without_receipt raises ValueError on an unknown class rather than defaulting, so a sixth general-defect class added later cannot silently acquire a disposition nobody chose."
  - "Task 2's report.py/reflection.py ledger-writing plumbing (write_review_ledger's reflection_retractions/reflection_skipped keys, apply_verdict's refused-retraction recording) was already implemented by plan 03-01/03-04; this plan's Task 2 closed only the missing markdown-rendering half (render_reflection_skipped_section, to_markdown's reflection_skips param)."
  - "Each task's shipping-file changes got their own version bump (1.56.0 -> 1.57.0 -> 1.58.0) and CHANGELOG entry per repo governance, rather than one bump for the whole plan."

metrics:
  duration: "~2.5 hours across two sessions (session boundary mid-Task-2)"
  completed: 2026-08-18

status: complete

actuals:
  tokens: 68000
  tasks: 3
  commits: 3
---

# Phase 3 Plan 05: Reflection Filter and Receipt-Gate Disposition Ladder Summary

Completed the retract-only reflection filter (prompt, response validation, mechanical
protected-subject veto, never-silent ledger) and attached the D-12 receipt-gate disposition
ladder that keeps `confirmed` mechanical for general-defect findings shipped without a
Tier-1 receipt.

## What was built

**Task 1 — Reflection prompt, response validation, and the mechanical protected-subject veto**
(`ff9293f`). `agents/review-filter.md` ports OCR's retract-only fact-checking prompt: the
five-step ordered method (protected-subject veto first, then Ground A, then Ground B, then
"when in doubt"), all five protected subjects (memory safety, concurrency, linkage/declaration
consistency, behavioral/compatibility change, unused parameter), and the two exclusive output
tools (`approve_all_comments` / `report_incorrect_comments`). `reflection.py` gained
`render_reflection_prompt` (substitutes `{{PATH}}`/`{{DIFF}}`/`{{COMMENTS}}` only, so the
filter has nothing to rank or rewrite), `validate_verdict` (parses the raw JSON response
before any finding sees it, reading only the named tool, the id list, and the analysis text —
any other field is silently ignored), and an extended `apply_verdict` that refuses a
protected-class retraction in code and records the refusal (`REFUSED_REASON`) rather than
dropping it. 16 tests, one per protected subject plus prompt-rendering, verdict-validation,
and mutation-safety cases.

**Task 2 — Never-silent ledger and SKILL.md dispatch** (`f45f0c6`). Discovered mid-task that
`write_review_ledger`'s `reflection_retractions`/`reflection_skipped` ledger keys and
`apply_verdict`'s refused-retraction recording were already wired from a prior plan — the
actual gap was `to_markdown`'s missing `reflection_skips` param and the missing
`render_reflection_skipped_section`/`REFLECTION_SKIPPED_HEADING` markdown renderer. Closed
that gap: the new section renders "No file was skipped." when empty or a path/reason/error
table row per `ReflectionSkip`, unconditionally — so a run that never triggered reflection is
distinguishable from one that ran and skipped nothing. `write_report` now passes
`reflection_skips` through to `to_markdown` (it already reached `write_review_ledger`).
`SKILL.md` documents the reflection dispatch after the position gate: a `review-filter`
subagent per file, `validate_verdict` parsing before trust, `apply_verdict` as the sole
retraction path — grounded against `cli.py`'s actual state (an always-empty verdict in the
tracer slice; live dispatch is a later plan). 6 new tests (ledger/skip/zero cases).

**Task 3 — Receipt-gate disposition ladder for general-defect findings** (`dcab42c`).
`findings_gate.py` gained `STATIC_CHECKABLE_CLASSES` (`null-dereference`, `error-swallowing`,
`resource-leak`, `injection`) and `RUNTIME_DEPENDENT_CLASSES` (`thread-safety`) — a
module-level assert enforces their union equals `review_findings.GENERAL_DEFECT_CLASSES` with
no intersection. `disposition_without_receipt(defect_class)` maps a general-defect class with
no Tier-1 receipt to `unconfirmed` (static-checkable) or `needs-deployment-testing`
(runtime-dependent), raising `ValueError` on any other class. The existing `confirms_alone`
receipt check is untouched — it remains the sole path to `confirmed`/`fixed`. `unconfirmed`
stays a `review_findings` string, never added to the frozen `FindingStatus` enum `models.py`
byte-mirrors for the Go port. 7 new `-k general_defect` tests.

## Deviations from Plan

### Auto-fixed Issues

None beyond the discovery documented above (Task 2's ledger-writing half was already present
from a prior plan — this is a scope narrowing, not a bug fix, and required no code change,
only recognizing what was already done and completing the missing rendering half).

## Verification

- `uv run pytest -q` (full suite): 1139 passed, 2 failed — both the pre-existing, documented
  environmental failures (`test_bench.py::test_seed_corpus_is_valid`,
  `test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd`), unchanged from
  baseline.
- `uv run pytest tests/test_reflection.py tests/test_findings_gate.py tests/test_review_profiles.py tests/test_rule_glob.py tests/test_rule_docs.py -q`:
  128 passed.
- `uv run ruff check sec_overlay/ bench/ tests/`: all checks passed.
- `uv run ty check`: 9 pre-existing diagnostics in `tests/test_review_tracer.py`'s `_fake_run`
  fixture (`R.stdout` on an unrelated fixture type) — out of scope per deviation-rule
  boundary, not touched by this plan's files.
- `git diff main -- models.py evidence.py`: empty across all three task commits.
- `claude plugin validate .`: passed.

## Threat Flags

None beyond what the plan's own `<threat_model>` already registered (T-03-04, T-03-15,
T-03-16, T-03-05, T-03-08) — no new network endpoint, auth path, or schema change at a trust
boundary was introduced outside that register.

## Self-Check: PASSED

- `plugins/sec-overlay/skills/sec-overlay/agents/review-filter.md` — FOUND
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/reflection.py` — FOUND
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/findings_gate.py` — FOUND (`disposition_without_receipt` present)
- Commit `ff9293f` — FOUND in `git log --oneline`
- Commit `f45f0c6` — FOUND in `git log --oneline`
- Commit `dcab42c` — FOUND in `git log --oneline`
