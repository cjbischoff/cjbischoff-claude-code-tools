---
phase: 03-rule-matching-review-modes
reviewed: 2026-08-18T00:00:00Z
depth: standard
files_reviewed: 29
files_reviewed_list:
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/diffscope.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/findings_gate.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/reflection.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_agent.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_findings.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/rule_glob.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_tracer.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_rule_glob.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_rule_docs.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_profiles.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_reflection.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_findings_gate.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_agent.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_live.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_cli.py
  - plugins/sec-overlay/skills/sec-overlay/agents/review-file.md
  - plugins/sec-overlay/skills/sec-overlay/agents/review-filter.md
  - plugins/sec-overlay/skills/sec-overlay/references/prompt-constants.md
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
  critical: 1
  warning: 3
  info: 1
  total: 5
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-08-18T00:00:00Z
**Depth:** standard
**Files Reviewed:** 29
**Status:** issues_found

## Summary

Reviewed the phase-03 rule-matching-review-modes surface: `rule_glob.py`'s four-layer rule-doc
resolver and RULE-03 file-safety gate, `reflection.py`'s retract-only protected-subject filter,
`review_findings.py`'s REV-01 profile gating, the D-12 disposition ladder added to
`findings_gate.py`, and the `review_agent.py`/`cli.py` review-mode wiring, plus their tests and
the nine built-in rule docs. `models.py`/`evidence.py` (frozen contract) were not read or flagged,
per scope. The two named environmental test failures were not exercised or flagged.

`rule_glob.py`, `reflection.py`, and `review_agent.py` hold up well in isolation — their own unit
tests exercise the documented edge cases (symlink escape, byte-cap boundary, protected-subject
veto, idempotent re-parse) and match their docstrings.

The one confirmed **Critical** finding is a wiring gap between `cli.py`'s reflection loop and its
own output: a reflection retraction is recorded in the ledger but never actually removed from the
`review_findings` list `report.md` renders as "kept". This is masked today because `cli.py` always
calls `apply_verdict` with a hardcoded empty verdict (a documented, deferred gap — see IN-01), but
`test_review_live.py::test_reflection_retraction_removes_a_live_finding` proves the gap directly,
by monkeypatching a non-empty verdict in: the finding still ships in `review_findings` even though
a retraction was recorded. The test's own inline comment acknowledges this ("review_findings still
lists it ... proven by the retraction entry itself, not an absent finding"), so the gap is known to
whoever wrote the test but is not disclosed anywhere a report reader would see it, and the test's
name overstates what it proves.

Two further **Warning**-level cross-module inconsistencies were confirmed: `apply_profile` never
consults `findings_gate.disposition_without_receipt`, so a `thread-safety` finding kept through
review-mode's `general` profile ships with `disposition: "unconfirmed"` instead of the
`needs-deployment-testing` the same class gets through the full audit pipeline; and
`findings_gate.validate_findings` silently rewrites `receipt_tier` into finding JSON files on disk,
an undisclosed side effect of a function shaped like a pure validator.

## Critical Issues

### CR-01: Reflection retraction is recorded but never removes the finding from what ships

**File:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py:301-310`
**Issue:**
`run_review`'s reflection loop has two compounding defects that together mean a retraction never
reaches the reported output, even once a real verdict source is wired:

```python
reflection_retractions: list = []
reflection_skips: list[ReflectionSkip] = []
for record in selection.reviewable:
    kept_for_file = [f for f in _kept if f.file == record.path]
    try:
        _kept_for_file, retractions = apply_verdict(kept_for_file, {}, path=record.path)
        reflection_retractions.extend(retractions)
    except Exception as exc:  # noqa: BLE001 - reflection fails open, never aborts the run
        reflection_skips.append(ReflectionSkip(record.path, SKIPPED_REASON, str(exc)))
```

1. It filters from `_kept` (`phase_gate.review_position_gate`'s output, *before* `apply_profile`
   runs), not from `review_findings` (`apply_profile`'s kept output, the thing `write_report`
   actually renders as "kept" — `cli.py:311-320`). Reflection is fact-checking a different set of
   findings than the one the reader sees.
2. `apply_verdict`'s first return value — the findings that survive retraction — is assigned to
   `_kept_for_file` and never used again. Only `retractions` (the ledger annotation) is kept.
   `review_findings` (built earlier, at `cli.py:292-295`) is passed to `write_report` unchanged, so
   a finding a retraction names still ships in the "kept" list.

`test_review_live.py:159-180` (`test_reflection_retraction_removes_a_live_finding`) proves this
today by monkeypatching `cli.apply_verdict` to return a non-empty retraction: the ledger gets a
`reflection_retractions` entry, but the test's own comment concedes the finding is not removed from
`review_findings` ("review_findings still lists it ... proven by the retraction entry itself, not
an absent finding"). The test's name claims the finding is removed; it is not. This is currently
inert only because `cli.py` always calls `apply_verdict` with a hardcoded `{}` verdict (a
separately-disclosed gap, see IN-01) — but that disclosure never mentions that even a real
retraction wouldn't reach the report. A reader who trusts the "Reflection retractions" section to
mean "removed from the findings above" is misled.

**Fix:** Filter `review_findings` (unwrapping `.finding` for the `_ReflectableFinding` Protocol),
not `_kept`, and use `apply_verdict`'s returned kept-list to actually narrow what's reported:

```python
review_findings_by_file: dict[str, list[ReviewFinding]] = {}
for rf in review_findings:
    review_findings_by_file.setdefault(rf.finding.file, []).append(rf)

reflection_retractions: list = []
reflection_skips: list[ReflectionSkip] = []
kept_review_findings: list[ReviewFinding] = []
for record in selection.reviewable:
    rfs_for_file = review_findings_by_file.get(record.path, [])
    try:
        kept_findings, retractions = apply_verdict(
            [rf.finding for rf in rfs_for_file], {}, path=record.path
        )
        kept_ids = {f.id for f in kept_findings}
        kept_review_findings.extend(rf for rf in rfs_for_file if rf.finding.id in kept_ids)
        reflection_retractions.extend(retractions)
    except Exception as exc:  # noqa: BLE001 - reflection fails open, never aborts the run
        kept_review_findings.extend(rfs_for_file)
        reflection_skips.append(ReflectionSkip(record.path, SKIPPED_REASON, str(exc)))
...
write_report(..., review_findings=kept_review_findings, ...)
```

Also update `test_reflection_retraction_removes_a_live_finding`'s assertions and name once fixed —
it should assert the retracted finding is absent from `ledger["review_findings"]`.

## Warnings

### WR-01: `apply_profile` never differentiates disposition by defect class, diverging from `findings_gate`'s D-12 ladder

**File:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_findings.py:139-149`
**Issue:** `apply_profile` hardcodes `disposition=UNCONFIRMED_DISPOSITION` for every kept finding
regardless of `defect_class`:

```python
defect_class = classify(finding)
bypassed = profile == "general" and gate in _RELAXABLE_GATES and defect_class is not None
if gate is None or bypassed:
    kept.append(
        ReviewFinding(finding=finding, defect_class=defect_class,
                      disposition=UNCONFIRMED_DISPOSITION, profile=profile)
    )
```

`findings_gate.disposition_without_receipt` (added the same phase, D-12) puts `thread-safety` in
`RUNTIME_DEPENDENT_CLASSES` and returns `NEEDS_DEPLOYMENT_TESTING_DISPOSITION` for it — proven by
`test_findings_gate.py:278-279` (`test_general_defect_thread_safety_ships_needs_deployment_testing`).
Since `cli.py:293` assigns `gate="B"` to every `GENERAL_DEFECT_CLASSES` member including
`thread-safety`, a live `thread-safety` finding kept under review-mode's `general` profile ships
with `disposition: "unconfirmed"` — the wrong bucket per the very ladder this phase introduced.
The module's own docstring (`review_findings.py:48-50`) discloses this as deferred ("D-12's
static-checkable/runtime-dependent split is a later plan's job"), so it is a known simplification,
not a hidden defect, but it is a real, currently-shipping inconsistency between two disposition
vocabularies for the same class name.

**Fix:**

```python
from sec_overlay.findings_gate import disposition_without_receipt

disposition = (
    disposition_without_receipt(defect_class) if defect_class is not None
    else UNCONFIRMED_DISPOSITION
)
```

### WR-02: `validate_findings` silently rewrites finding files on disk — undisclosed side effect of a "validator"

**File:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/findings_gate.py` (`validate_findings`)
**Issue:** `validate_findings(ws) -> list[str]` reads every `findings/*.json`, computes
`receipt_tier`, and writes it back to disk when it differs from the stored value —
`test_findings_gate.py:164-169` (`test_receipt_tier_is_stamped`) confirms this is intentional and
tested. But the function's name and return type (`list[str]`, an error list) signal a pure,
read-only check. A caller invoking this in a dry-run/lint/CI context expecting no filesystem writes
would be surprised to find `findings/*.json` mutated as a side effect.
**Fix:** Either document the mutation explicitly in the docstring ("Returns: ... Side effects:
rewrites `receipt_tier` on disk when it drifts from the stored value"), or rename to signal the
write (e.g. `validate_and_stamp_findings`), or split the `receipt_tier` stamping into its own
explicitly-named function called by the CLI wrapper, leaving `validate_findings` read-only.

### WR-03: `read_rule_file_safe` has a symlink-resolve/read TOCTOU window

**File:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/rule_glob.py` (`read_rule_file_safe`)
**Issue:** The RULE-03 safety gate resolves symlinks once (`Path.resolve(strict=True)`), checks the
extension and repo-root containment against that resolved path, then opens and reads the file
separately. Between the `resolve()` call and the read, the filesystem entry could be swapped
(e.g. a concurrently-running process repoints a symlink after the containment check passes but
before the read), letting a read outside the repo root slip through. This requires local,
concurrent filesystem write access to the same path during the narrow window of one CLI
invocation, so the practical exploitability is low, but it is a real gap in an otherwise carefully
specified safety gate (byte cap, extension allowlist, containment check are all present and
correctly ordered otherwise).
**Fix:** Open the file first (or via the resolved path with `O_NOFOLLOW`-equivalent handling) and
re-verify the opened file descriptor's real path matches the pre-checked resolved path before
trusting its contents, or accept and document the TOCTOU window as an out-of-scope local-trust
assumption (the harness already assumes the operator controls the reviewed repo's filesystem).

## Info

### IN-01: `run_review`'s reflection wiring is undocumented in its own docstring

**File:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py` (`run_review`)
**Issue:** `SKILL.md` (~lines 91-106) explicitly discloses that `cli.py review`'s reflection call
always uses an empty verdict because no finding source is wired into review mode yet ("live
reflection dispatch is a later plan"). `run_review`'s own docstring and inline comments do not
carry the same caveat, so a reader of just the code (without also reading `SKILL.md`) would not
know the reflection loop is currently a no-op by design.
**Fix:** Add a one-line comment at `cli.py`'s reflection loop cross-referencing the SKILL.md
disclosure, e.g. `# Empty verdict: no live reflection source wired yet (see SKILL.md's Reflection
pass section) — this loop never retracts today.`

---

_Reviewed: 2026-08-18T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
