---
phase: 03-rule-matching-review-modes
verified: 2026-08-19T00:00:00Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 4/5
  gaps_closed:
    - "The reflection filter runs once per file after positioning and the hunk gate, retracts findings only, fails open on LLM error, and cannot itself produce a `confirmed` disposition; a general-defect finding without a Tier-1 mechanical receipt ships as `unconfirmed`/`needs-deployment-testing`, never `confirmed` (Roadmap SC #5; REV-02, REV-03)"
  gaps_remaining: []
  regressions: []
---

# Phase 3: Rule Matching & Review Modes Verification Report

**Phase Goal:** The review verb selects the right per-language checklist for every file, runs in security or general-defect scope on command, and never lets an LLM judgment override the mechanical receipt gate.
**Verified:** 2026-08-19T00:00:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure (03-07-PLAN.md / 03-07-SUMMARY.md, commits `fb5aca7`, `45dafc1`, `5cf439e`)

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `rule_glob.py` resolves a file's rule via ordered, brace-expanded, `**`-aware PathRules, four-layer resolution, `--exclude` append, `merge_system_rule` fixed-header concatenation | VERIFIED (regression) | Unchanged since prior verification. `tests/test_rule_docs.py` — 36 passed in this re-run. |
| 2 | Rule-file reads resolve symlinks, require resolved path under repo root, restrict extensions to `.md`/`.txt`/`.markdown`, reject files over 512 KB | VERIFIED (regression) | Unchanged since prior verification; `read_rule_file_safe` untouched by 03-07. |
| 3 | Per-language rule docs exist for go, java, python, php, rust, ts/js/tsx/jsx, kotlin, swift, and default, each naming NPE/thread-safety/injection/resource-leak/error-swallowing with exclusions | VERIFIED (regression) | `ls plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/` — all 9 files present, unchanged by 03-07; conformance test passes. |
| 4 | `review --profile security` reproduces existing gate A-E behavior exactly; `--profile general` additionally surfaces NPE/thread-safety/XSS/SQLi findings gates A/B would drop, gates C/D/E still enforced | VERIFIED (regression) | `tests/test_review_profiles.py` full run: 22 tests passed including the committed-baseline no-regression test and the new disposition-ladder tests added by 03-07 (which sit alongside, not instead of, the profile-split assertions). |
| 5 | Reflection filter runs once per file after positioning/hunk gate, retracts findings only, fails open, cannot produce `confirmed`; a general-defect finding without a Tier-1 receipt ships `unconfirmed`/`needs-deployment-testing`, never `confirmed` | **VERIFIED** (gap closed) | Both previously-confirmed sub-failures (CR-01, WR-01) are fixed and proven by new/rewritten tests, re-run fresh in this verification — see Gap Closure Evidence below. |

**Score:** 5/5 truths verified.

### Gap Closure Evidence (Success Criterion #5)

**CR-01 — reflection retractions now reach the reported findings.**

`sec_overlay/cli.py:306-316` (`run_review`):

```python
reflection_retractions: list = []
reflection_skips: list[ReflectionSkip] = []
retracted_ids: set[str] = set()
for record in selection.reviewable:
    kept_for_file = [rf.finding for rf in review_findings if rf.finding.file == record.path]
    try:
        surviving, retractions = apply_verdict(kept_for_file, {}, path=record.path)
        reflection_retractions.extend(retractions)
        surviving_ids = {f.id for f in surviving}
        retracted_ids.update(f.id for f in kept_for_file if f.id not in surviving_ids)
    except Exception as exc:  # noqa: BLE001 - reflection fails open, never aborts the run
        reflection_skips.append(ReflectionSkip(record.path, SKIPPED_REASON, str(exc)))

review_findings = [rf for rf in review_findings if rf.finding.id not in retracted_ids]
```

- `kept_for_file` is now drawn from `review_findings` (`apply_profile`'s post-gate output, line 294-297), not the position gate's pre-profile `_kept` list — closes the "wrong input" half of CR-01.
- The rebind at line 316 filters the **same** `review_findings` list by `retracted_ids` before it is passed to `write_report(review_findings=review_findings, ...)` at line 318-327 — a retraction now actually removes the finding from what the ledger reports, closing the "discarded kept-half" half of CR-01.
- A per-file exception during `apply_verdict` appends a `ReflectionSkip` and contributes zero ids to `retracted_ids` for that file — fail-open, and every other file's loop iteration is unaffected (plain sequential `for` loop, no threading/async imports in `cli.py`).
- Confirmed behaviorally: `tests/test_review_live.py::test_reflection_retraction_removes_a_live_finding` was rewritten to assert `ledger["review_findings"] == []` (previously it asserted the opposite — the finding's id was still present, with an inline comment conceding the defect). Re-run in this verification: **PASS**.
- `tests/test_review_live.py::test_reflection_failure_for_one_file_leaves_other_files_unaffected` (new) asserts a raising file's finding and the other file's finding are both retained, with exactly one `reflection_skipped` entry naming the raising path. Re-run: **PASS**. This also closes the prior verification's `human_verification` backstop item — multi-file failure isolation is now an automated assertion, not an inferred property.
- `tests/test_review_live.py::test_finding_on_an_unreflected_path_survives` (new) proves a finding on a path outside `selection.reviewable` is never silently dropped (D-14). Re-run: **PASS**.

**WR-01 — the no-receipt disposition ladder is now live code.**

`sec_overlay/review_findings.py:146-166` (`apply_profile`):

```python
defect_class = classify(finding)
bypassed = profile == "general" and gate in _RELAXABLE_GATES and defect_class is not None
if gate is None or bypassed:
    from sec_overlay.findings_gate import disposition_without_receipt  # deferred: avoids a module cycle

    disposition = (
        disposition_without_receipt(defect_class)
        if defect_class is not None
        else UNCONFIRMED_DISPOSITION
    )
    kept.append(ReviewFinding(finding=finding, defect_class=defect_class, disposition=disposition, profile=profile))
```

- `findings_gate.disposition_without_receipt` (`findings_gate.py:45-67`) is now called from production code (`review_findings.apply_profile`), not only from its own test file. `rg -c "disposition_without_receipt" sec_overlay/review_findings.py` → `2` (import + call).
- The function-local import is deliberate and documented inline: `findings_gate` imports `GENERAL_DEFECT_CLASSES`/both disposition constants from `review_findings` at module level, so a module-level reverse import would be a cycle. Confirmed no cycle: `uv run python -c "import sec_overlay.review_findings, sec_overlay.findings_gate"` succeeds (implicit — full test suite imports both modules together without error).
- Confirmed behaviorally: `tests/test_review_profiles.py::test_apply_profile_assigns_needs_deployment_testing_for_thread_safety` (new) — a general-profile thread-safety finding ships `needs-deployment-testing`. `test_apply_profile_assigns_unconfirmed_for_each_static_checkable_class` (new, parametrized over null-dereference/error-swallowing/resource-leak/injection) — each ships `unconfirmed`. `test_apply_profile_never_assigns_a_confirmed_disposition` (extended to include a kept thread-safety finding) — asserts every kept disposition is one of the two allowed values. Re-run in this verification: all **PASS**.
- Composed end-to-end proof through the real CLI path (not just unit level): `tests/test_review_live.py::test_thread_safety_finding_ships_needs_deployment_testing_end_to_end` — a general-profile run over a recorded thread-safety finding produces a ledger entry with `"disposition": "needs-deployment-testing"` and `"defect_class": "thread-safety"`. Re-run: **PASS**.
- No code path in `reflection.py`, `review_findings.py`, or `cli.py` assigns `"confirmed"` (`rg -rn "\"confirmed\"|'confirmed'|FindingStatus.CONFIRMED"` over the three files returns nothing) — the "never produces `confirmed`" half of REV-03, already true before 03-07, still holds unmodified.
- `reflection.py`, `models.py`, and `evidence.py` are byte-identical to before this gap-closure plan (`git diff <pre-03-07>..<post-03-07> -- reflection.py models.py evidence.py` is empty) — the frozen contract (D-11) and `apply_verdict`'s already-correct unit-level behavior (retract-only, protected-subject veto, fail-open) are untouched; only the wiring around them was fixed.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| RULE-01 | 03-01, 03-06 | Ordered, brace-expanded, `**`-aware path matching, first-match-wins else default | VERIFIED | `rule_glob.glob_match`/`build_file_filter`; unchanged, tests pass |
| RULE-02 | 03-02 | Four-layer rule resolution + `--exclude` append | VERIFIED | `rule_glob.build_resolution`; unchanged, tests pass |
| RULE-03 | 03-02 | Rule-file read safety gate (symlink/root/ext/size) | VERIFIED | `read_rule_file_safe`; unchanged (WR-03 TOCTOU remains non-blocking) |
| RULE-04 | 03-02 | `merge_system_rule` fixed-header concatenation | VERIFIED | `merge_with_system_rule`; unchanged |
| RULE-05 | 03-03 | 9 per-language rule docs, 5 defect classes, exclusions | VERIFIED | All 9 files present; unchanged; conformance tests pass |
| REV-01 | 03-04, 03-06 | Security profile exact reproduction; general profile superset | VERIFIED | Committed-baseline no-regression + superset tests pass, unaffected by 03-07's ladder addition |
| REV-02 | 03-05, 03-06, **03-07** | Reflection: per-file, after position/hunk gate, retract-only, protected-subject veto, fails open, and the retraction actually reaches the reported findings | **VERIFIED** | `cli.run_review`'s reflection loop now consumes `apply_profile`'s output and rebinds `review_findings` on the retracted-id set before `write_report`; proven by `test_reflection_retraction_removes_a_live_finding` (rewritten), `test_reflection_failure_for_one_file_leaves_other_files_unaffected` (new), `test_finding_on_an_unreflected_path_survives` (new) |
| REV-03 | 03-05, **03-07** | Receipt gate sole authority on `confirmed`; unconfirmed/needs-deployment-testing split for no-receipt general-defect findings | **VERIFIED** | `apply_profile` now calls `findings_gate.disposition_without_receipt` for every classified kept finding; proven by `test_apply_profile_assigns_needs_deployment_testing_for_thread_safety`, `test_apply_profile_assigns_unconfirmed_for_each_static_checkable_class`, extended `test_apply_profile_never_assigns_a_confirmed_disposition`, and the composed `test_thread_safety_finding_ships_needs_deployment_testing_end_to_end` |

**Orphaned requirements check:** `.planning/REQUIREMENTS.md`'s Phase 3 section (RULE-01–05, REV-01–03) is bounded above by Phase 2's `POS-*` requirements and below by Phase 4's `SCALE-*` requirements. All 8 requirement IDs declared across 03-01..03-07's PLAN frontmatter (`RULE-01, RULE-02, RULE-03, RULE-04, RULE-05, REV-01, REV-02, REV-03`) match the roadmap's declared set exactly. No orphans found.

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `sec_overlay/rule_glob.py` | 4-layer rule resolution, safe rule-file read, brace/glob matching, merge headers | VERIFIED | Unchanged by 03-07; substantive, wired into `review_agent.py` |
| `rules/rule_docs/*.md` (9 files) | Per-language checklists | VERIFIED | Unchanged by 03-07; all present, conformance-tested |
| `sec_overlay/review_findings.py` | `apply_profile`, `classify`, `GENERAL_DEFECT_CLASSES`, disposition ladder | **VERIFIED** | Profile gating (REV-01) unchanged and correct; disposition assignment (REV-03) now calls `findings_gate.disposition_without_receipt` instead of hardcoding `unconfirmed` |
| `sec_overlay/reflection.py` | `apply_verdict`, `PROTECTED_SUBJECT_CLASSES`, retract-only contract | VERIFIED | Byte-unchanged by 03-07; correct at unit level (as before) and now correctly wired at pipeline level |
| `sec_overlay/findings_gate.py` | `disposition_without_receipt` | **VERIFIED** | Byte-unchanged implementation, but now has a live production call site (`review_findings.apply_profile`) — no longer dead code |
| `sec_overlay/cli.py` (`run_review`) | Live pipeline wiring: position gate → apply_profile → apply_verdict → receipt gate, feeding a coherent `review_findings` | **VERIFIED** | Reflection now consumes `apply_profile`'s kept output per file and the survivors (post-retraction) are what `write_report` receives; docstring corrected to match |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `rule_glob.resolve_rule_doc` | `review_agent.render_review_prompt` | `{{system_rule}}` substitution | VERIFIED | Unchanged by 03-07 |
| SKILL.md → subagent → `review_agent.recorded_return_source` | `cli.run_review` | disk-persisted agent returns | VERIFIED | Unchanged by 03-07 |
| `review_agent.parse_review_response` | `review_position_gate` | parsed findings list | VERIFIED | Unchanged by 03-07 |
| `review_position_gate` output (`_kept`) | `review_findings.apply_profile` | `GatedFinding` list at `cli.py:294-297` | VERIFIED | Unchanged; position-gate output still feeds `apply_profile` |
| `review_findings.apply_profile` output | `reflection.apply_verdict` input | `cli.py:307`: `kept_for_file` drawn from `review_findings` (post-profile), not `_kept` | **VERIFIED (fixed)** | Previously drew from the pre-profile list; now correctly drawn from `apply_profile`'s kept output per must_haves.key_links in 03-07-PLAN.md |
| `apply_verdict` survivors | `write_report(review_findings=...)` | id-set rebind at `cli.py:316` | **VERIFIED (fixed)** | Previously the retraction record was kept but the finding itself was not removed; now the rebound, post-retraction list is what reaches `write_report` and the ledger |
| `review_findings.apply_profile` | `findings_gate.disposition_without_receipt` | function-local import inside `apply_profile` (`review_findings.py:152`) | **VERIFIED (fixed)** | Previously never called; now called for every kept finding with a classified `defect_class`, avoiding the module-level import cycle with `findings_gate` |
| `findings_gate.validate_findings` | `review_findings.GENERAL_DEFECT_CLASSES` | single-owner class list | VERIFIED | Unchanged |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `sec_overlay/findings_gate.py` | 45-67 | `validate_findings` silently rewrites `receipt_tier` on disk as an undisclosed side effect | Warning | Carried forward from prior verification (WR-02); non-blocking per 03-REVIEW.md; out of scope for this gap-closure plan; does not affect confirm/deny correctness |
| `sec_overlay/rule_glob.py` | `read_rule_file_safe` | TOCTOU window between symlink-resolve and read | Warning | Carried forward from prior verification (WR-03); non-blocking; low practical severity (local rule-file source) |
| `tests/test_review_tracer.py` | 67-73 | `uv run ty check` reports 9 `unresolved-attribute` diagnostics on a local `class R` fake-runner's `.stdout` attribute | Info | Pre-existing since `03-05` (`git log` shows this file's last edit at `ff9293f`, before the 03-07 gap-closure commits); not touched by 03-07; not a production-code issue (test-only helper class); zero new diagnostics from this phase's changes |

No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` debt markers found in any file this gap-closure plan modified (`cli.py`, `review_findings.py`).

The prior verification's IN-01 (stale `run_review` docstring describing the wrong gate order) is closed: the docstring at `cli.py:117-167` now accurately states that `apply_profile`'s kept output feeds `apply_verdict` per reviewable file and that the surviving list is what `review_findings` reports.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Targeted rule/review/reflection/gate/agent test suite | `uv run pytest tests/test_review_live.py tests/test_review_profiles.py tests/test_findings_gate.py tests/test_reflection.py tests/test_rule_docs.py tests/test_review_agent.py -q` | 133 passed | PASS |
| CR-01 fix (rewritten test) | `tests/test_review_live.py::test_reflection_retraction_removes_a_live_finding` | `ledger["review_findings"] == []` after a faked retraction — the retracted finding is now absent | PASS |
| Multi-file isolation (new test; closes prior `human_verification` item) | `tests/test_review_live.py::test_reflection_failure_for_one_file_leaves_other_files_unaffected` | One `reflection_skipped` entry for the raising file; both files' findings retained | PASS |
| WR-01 fix, unit level (new tests) | `tests/test_review_profiles.py::test_apply_profile_assigns_needs_deployment_testing_for_thread_safety`, `test_apply_profile_assigns_unconfirmed_for_each_static_checkable_class` | Correct disposition per class | PASS |
| WR-01 + CR-01 fix, composed end-to-end (new test) | `tests/test_review_live.py::test_thread_safety_finding_ships_needs_deployment_testing_end_to_end` | Ledger entry: `disposition="needs-deployment-testing"`, `defect_class="thread-safety"` | PASS |
| Full-suite regression check | `uv run pytest -q` (from `helpers/`) | 1169 passed, 2 failed (`test_bench.py::test_seed_corpus_is_valid`, `test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd`) | PASS — exactly the documented pre-existing environmental baseline (1161 + 8 tests this plan added); zero new regressions |
| Lint gate | `uv run ruff check .` | All checks passed! | PASS |
| Type gate | `uv run ty check` | 9 diagnostics, all pre-existing in `test_review_tracer.py` (unmodified by this phase's gap closure) | PASS (no new diagnostics) |
| Frozen contract check | `git diff <pre-03-07>..<post-03-07> -- reflection.py models.py evidence.py` | Empty diff | PASS |
| Function-local import / no cycle | Full test suite imports both `sec_overlay.review_findings` and `sec_overlay.findings_gate` without `ImportError` | 1169 passed | PASS |

### Gaps Summary

None. Both gaps from the prior verification (CR-01: reflection retractions discarded before reaching the report; WR-01: the receipt-gate disposition ladder was dead code) are closed by 03-07's three commits (`fb5aca7`, `45dafc1`, `5cf439e`), each proven by a rewritten or new behavioral test that was re-run fresh in this verification rather than trusted from the SUMMARY. The one prior `human_verification` backstop item (multi-file reflection failure isolation) is now an automated, passing assertion rather than an inferred property.

All 5 roadmap Success Criteria for Phase 3 are verified. All 8 requirement IDs (RULE-01 through RULE-05, REV-01 through REV-03) are satisfied with test evidence. No regressions in the full test suite beyond the two documented, pre-existing environmental failures. No debt markers. Governance (branch, Conventional Commits, README/CHANGELOG updates, semver bumps to 1.61.1 → 1.61.3) confirmed present in each of the three gap-closure commits. The frozen `models.py`/`evidence.py` contract (D-11) is untouched.

Two non-blocking warnings (WR-02, WR-03) and one info-level pre-existing type-check note (`test_review_tracer.py`) are carried forward for visibility; none affects the phase goal's core guarantee and none is in scope for this phase.

---

_Verified: 2026-08-19T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
