---
phase: 03-rule-matching-review-modes
reviewed: 2026-08-19T00:00:00Z
depth: standard
files_reviewed: 39
files_reviewed_list:
  - plugins/sec-overlay/skills/sec-overlay/SKILL.md
  - plugins/sec-overlay/skills/sec-overlay/CLAUDE.md
  - plugins/sec-overlay/CLAUDE.md
  - plugins/sec-overlay/CHANGELOG.md
  - plugins/sec-overlay/.claude-plugin/plugin.json
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_findings.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_agent.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/reflection.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/rule_glob.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phase_gate.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/findings_gate.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/diffscope.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/models.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/positioning.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_cli.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_live.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_profiles.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_reflection.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_agent.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_tracer.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_findings_gate.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_rule_docs.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_rule_glob.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/fixtures/review_profiles_security_baseline.json
  - plugins/sec-overlay/skills/sec-overlay/references/README.md
  - plugins/sec-overlay/skills/sec-overlay/references/prompt-constants.md
  - plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/README.md
  - plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/default.md
  - plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/python.md
  - plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/go.md
  - plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/java.md
  - plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/kotlin.md
  - plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/php.md
  - plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/rust.md
  - plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/swift.md
  - plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/ts_js_tsx_jsx.md
findings:
  critical: 0
  warning: 2
  info: 1
  total: 3
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-08-19T00:00:00Z
**Depth:** standard
**Files Reviewed:** 39
**Status:** issues_found

## Summary

Regenerated review of phase 03 (rule matching + review modes) covering the gap-closure commits
(`fb5aca7`, `45dafc1`, `5cf439e`, landed on top of `9f86ddc`/`8a982ce`) plus the full set of 39
files listed for this phase.

**Prior findings verified resolved.** CR-01 (reflection loop rebinding `review_findings` from
`apply_profile`'s kept output) and WR-01 (D-12 disposition ladder assigning
`needs-deployment-testing` vs `unconfirmed` per defect class) are both correctly implemented
(`review_findings.py:107-177`, `findings_gate.disposition_without_receipt`) and genuinely
test-covered (`test_review_profiles.py`, `test_findings_gate.py` parametrize every general-defect
class individually, plus a committed no-regression baseline fixture). No regression found in
either fix.

**Rule resolution, rule docs, position gate, diff-scoping, and report rendering are solid.**
`rule_glob.read_rule_file_safe` correctly chains symlink-resolution, extension allowlisting,
containment checks, and a TOCTOU-safe byte-cap read, with exhaustive adversarial test coverage.
The nine per-language rule docs (`default`, `python`, `go`, `java`, `kotlin`, `php`, `rust`,
`swift`, `ts_js_tsx_jsx`) are structurally consistent (five `####` sections, each with an
explicit exclusion block) and conformance-tested from constants, not hardcoded filenames.
`diffscope.py`'s ref validation correctly rejects leading-dash argument-injection attempts.
`report.py` renders every review-mode ledger section unconditionally, even when empty, matching
the stated "never silent" design.

**New finding.** Tracing the reflection pass (D-16) all the way through `cli.py`'s live
`run_review` found that the review-filter agent is never actually consulted in production: the
verdict passed to `reflection.apply_verdict` is a hardcoded literal `{}`, for every file, on
every run (`cli.py:309`). Since `apply_verdict` only retracts a finding whose id is a key in the
verdict dict, an empty dict makes every kept finding "survive" unconditionally — the retraction
machinery is fully implemented and unit-tested in isolation but is a no-op in the live pipeline.
This fails safe (no finding is ever wrongly suppressed) rather than unsafe, so it is classified
as a Warning, not a Critical. A second, related Warning: `SKILL.md`'s own account of this gap
(lines 105-106) is now stale — it attributes the empty verdict to "no finding source is wired
into review mode yet," but the 03-06 gap-closure commit already wired a live finding source
(`review_agent.recorded_return_source`) into `run_review`; only the reflection verdict itself
remains unwired. The docs no longer describe the actual remaining gap.

**Test suite.** `uv run pytest -q` in `skills/sec-overlay/helpers/` passes 1169/1171; the two
failures (`test_bench.py::test_seed_corpus_is_valid`, `test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd`)
are the environmental failures the task specified as pre-existing and not attributable to phase
03 — confirmed by rerunning against the current tree, no new failures beyond that allowlist.
`uv run ruff check sec_overlay/ tests/` is clean.

## Warnings

### WR-01: Reflection/review-filter agent is never consulted in the live review pipeline

**File:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py:309`
**Issue:** `run_review`'s per-file reflection loop calls
`apply_verdict(kept_for_file, {}, path=record.path)` with a hardcoded empty-dict literal as the
verdict, for every file, on every invocation. `reflection.apply_verdict` (`reflection.py:257-259`)
only retracts a finding whose `id` is a key in `verdict`; with `verdict == {}`, `f.id not in
verdict` is always `True`, so every finding is unconditionally kept and `retractions` is always
`[]`. Neither `reflection.render_reflection_prompt` nor `reflection.validate_verdict` has any
caller in `cli.py` — confirmed by `grep`, and independently confirmed by the test suite: no test
in `test_review_live.py`, `test_cli.py`, or `test_review_tracer.py` wires a genuine, non-empty
verdict through the real `cli.run_review` → `apply_verdict` call path. The one test that exercises
a non-empty retraction, `test_review_live.py::test_reflection_retraction_removes_a_live_finding`,
does so by monkeypatching `cli.apply_verdict` itself, bypassing the `{}` literal entirely — it
proves retraction *propagation* into the ledger/report works, not that a live verdict is ever
produced. The result: the entire D-16 "fact-checking kept comments" feature that `SKILL.md` and
`reflection.py`'s own docstring describe as running before every report is written currently does
nothing in the `cli.py review` consume step — it is fully built and unit-tested in isolation, but
disconnected from production. This is a Warning rather than a Critical because the failure mode
is fail-open (no finding is wrongly suppressed) rather than fail-unsafe.
**Fix:** Wire a real verdict source analogous to `review_agent.recorded_return_source` — e.g. a
`reflection_agent.recorded_verdict_source(ws, base=base_sha, head=head_sha)` that reads a recorded
`review-filter` subagent return per file, runs it through `validate_verdict`, and passes the
result to `apply_verdict` in place of `{}`. Until that dispatch/record/consume loop exists, update
the module docstring and `SKILL.md` to state plainly that reflection is scaffolding only and not
yet exercised in `cli.py review`, so a user does not believe kept findings are being fact-checked
today.

### WR-02: SKILL.md's reflection-pass description is stale post-03-06

**File:** `plugins/sec-overlay/skills/sec-overlay/SKILL.md:105-106`
**Issue:** The text reads: `` `cli.py review`'s tracer slice calls `apply_verdict` with an
always-empty verdict — no finding source is wired into review mode yet — so live reflection
dispatch is a later plan.`` This sentence was last edited at commit `f45f0c6` (phase 03-05),
before `9f86ddc` (phase 03-06, "wire review source into run_review") shipped a live finding
source into `run_review` via `review_agent.recorded_return_source` (`cli.py:184`) — confirmed via
`git log --oneline -- .../SKILL.md`, which shows no commit touching this file since `a9b9698`
(03-06's prompt-port commit, which also predates the wiring commit `9f86ddc`). Findings themselves
are now genuinely live-sourced in `run_review` (proven by `test_review_live.py`), so the stated
reason for the empty verdict — "no finding source is wired into review mode yet" — is now false.
The narrower, still-true gap is that only the *reflection verdict* remains hardcoded, not the
finding source generally. Per this plugin's own governance rule ("docs track code in the same
commit"), the 03-06 commit that changed this behavior should have updated this sentence and did
not; a maintainer reading `SKILL.md` today would draw an incorrect conclusion about which part of
the pipeline is still unwired.
**Fix:** Replace the sentence with an accurate statement, e.g.: "`cli.py review`'s consume step
now reads a live finding source (`review_agent.recorded_return_source`), but the reflection verdict
passed to `apply_verdict` is still a hardcoded empty dict — no review-filter subagent return is
recorded or read yet, so live reflection dispatch remains a later plan (see WR-01)."

## Info

### IN-01: Stale comment in a passing test restates the same outdated claim

**File:** `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_cli.py:231-232`
**Issue:** The comment above
`test_review_writes_ledger_and_report_with_zero_drops_and_declines` reads "No finding source is
wired into review mode yet, so the real gate runs against an empty finding list..." — the same
now-outdated claim as WR-02. The test itself still passes for the correct reason: this specific
test provides no recorded agent return for its synthetic file, so `recorded_return_source`
legitimately yields zero live findings for it regardless of whether wiring exists elsewhere. The
test's assertions remain valid; only the comment's stated reasoning is stale. Not flagging as a
Warning per this review's rule against flagging test-file issues that do not affect test
reliability.
**Fix:** Reword the comment to describe why this specific test sees zero findings ("this test
records no agent return for a.py, so the live finding source yields nothing for it") rather than
implying review mode has no finding source at all.

---

_Reviewed: 2026-08-19T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
