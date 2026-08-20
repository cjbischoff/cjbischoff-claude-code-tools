---
phase: 04-scale-resume-diff-output
verified: 2026-08-20T19:06:21Z
status: gaps_found
score: 2/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "OUT-01: review_comments.json carries the coverage manifest alongside the comment payload so a consumer can tell whether the run producing it was complete or partial, without inferring it from the file's presence"
    status: failed
    reason: >
      cli.py calls write_review_comments(ws, comments, manifest.to_dict()) before
      manifest.seal() runs, so the embedded coverage_manifest.seal is always null in
      every real run, regardless of whether the run actually completed or partial-sealed.
      This falsifies the module's own docstring promise and the plan's T-04-04 threat
      mitigation claim. No test at any level (unit or integration) exercises the real
      cli.py call ordering — the one existing test
      (test_write_review_comments_empty_list_still_has_manifest) calls
      write_review_comments() directly with a hand-built fixture manifest, never
      through run_review()'s real sequence.
    artifacts:
      - path: "plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py"
        issue: "Lines ~523-530: write_review_comments(ws, comments, manifest.to_dict()) runs before manifest.seal(); the embedded manifest is always pre-seal state"
    missing:
      - "Reorder cli.py so manifest.seal() runs before write_review_comments(), or write the comments file a second time with a post-seal manifest snapshot"
      - "An integration test asserting review_comments.json's embedded coverage_manifest['seal'] is non-null and matches the on-disk coverage_manifest.json's seal after a real run_review() call (not a direct write_review_comments() call)"
  - truth: "SCALE-03: Resume validates identity before any agent spawn — an implicit model or profile change is rejected with nothing persisted"
    status: failed
    reason: >
      The profile half of this gate is fully wired end to end (check_resume_identity
      runs before CoverageManifest construction and before any write, confirmed by a
      byte-hash-unchanged test). The model half is unreachable in production: the
      `review` argparse subparser declares no --model argument, and main()'s dispatch
      to run_review() never passes model=, so model is always None through any real
      CLI invocation. check_resume_identity's model-mismatch branch is dead code
      outside of direct Python-level test calls that bypass main(). Confirmed by
      `python -m sec_overlay.cli review --model opus ...` failing with
      "error: unrecognized arguments: --model opus", and zero occurrences of "--model"
      across cli.py, every test file, and SKILL.md.
    artifacts:
      - path: "plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py"
        issue: "review subparser (~lines 576-611) has no --model argument; main()'s dispatch (~lines 670-682) never passes model=args.model to run_review()"
    missing:
      - "Add review.add_argument(\"--model\", default=None) to the review subparser"
      - "Pass model=args.model at the run_review() call site in main()"
      - "A CLI-level (argparse-through-main) test asserting a resumed run with a changed --model value exits non-zero naming the model field, not just a direct check_resume_identity() unit test"
  - truth: "SCALE-02: --concurrency, per-bundle --timeout, and --max-git-procs bound execution; a timed-out bundle marks its files failed and the run terminal state becomes partial"
    status: failed
    reason: >
      The three flags exist with correct defaults/ceilings/rejection behavior, and a
      timed-out unit correctly marks every member file failed via CoverageManifest.fail()
      (seal() then correctly returns "partial", exit 3 — confirmed by a passing test
      that asserts manifest_json["seal"] == "partial"). But --timeout does not bound
      wall-clock execution: `with ThreadPoolExecutor(...) as ex:` wraps the entire
      submit-and-wait loop, so a `TimeoutError` from future.result(timeout=...) is
      caught and handled correctly, but the `with` block's __exit__ still calls
      ex.shutdown(wait=True) on exit, blocking the whole process until the abandoned
      thread finishes its work regardless of the declared timeout. Independently
      reproduced by timing the shipped test: declared timeout=1 in the test's own
      setup, measured wall time 4.20s (uv run pytest tests/test_cli.py::test_review_unit_timeout_fails_every_member_with_timeout_note
      -q → "1 passed in 4.20s"). This falsifies the literal roadmap wording "bound
      execution." 04-02-SUMMARY.md's own "Decisions Made" section documents the team
      recognized this exact tension at implementation time and left it unresolved
      ("closing it after only submitting would make __exit__'s shutdown(wait=True)
      block until every future finishes anyway, silently defeating the timeout's
      early-return purpose") without applying the actual fix (shutdown(wait=False) in
      a finally block, or a subprocess-level timeout that actually kills the hung
      process).
    artifacts:
      - path: "plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py"
        issue: "Lines ~397-411: with ThreadPoolExecutor(...) as ex: wraps the entire fetch-and-wait loop; __exit__'s implicit shutdown(wait=True) blocks past the declared --timeout on any abandoned/hung thread"
    missing:
      - "Replace the with-statement with an explicit try/finally that calls ex.shutdown(wait=False) after the result-collection loop, so a timed-out future's thread is abandoned rather than awaited"
      - "For a complete fix, also thread a real subprocess-level timeout/kill into the git fetch call itself, since abandoning the Python thread still leaves the underlying git subprocess running"
      - "A wall-clock timing test proving --timeout actually bounds the CLI's total runtime for a hung unit, not just that the manifest ends up marked failed"
deferred: []
---

# Phase 4: Scale, Resume & Diff Output Verification Report

**Phase Goal:** Large changesets stay bounded and resumable, and every shipped finding carries a diff-anchored, positioning-confirmed location.
**Verified:** 2026-08-20T19:06:21Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SCALE-01: `bundle.py` groups locale/config siblings and impl/test pairs into review units, one file per unit as fallback, documented as beyond OCR | ✓ VERIFIED | `bundle.py` module docstring states "This is a sec-overlay addition beyond OCR"; `group_bundles()` pure/total (no fs/subprocess/Workspace imports); `review_agent.py:187` sets `Finding.file=entry_path` (entry's own path, not the outer file under review); 14 `test_bundle.py` tests + 3 `test_review_agent.py` tests pass |
| 2 | SCALE-02: `--concurrency`/`--timeout`/`--max-git-procs` bound execution; a timed-out bundle marks its files failed and the run seals `partial` | ✗ FAILED | Flags exist, validated, correctly bounded (`_bounded_int`, `MAX_WORKERS=128`, `MAX_TIMEOUT_SECONDS=3600`); timeout handling correctly marks files failed (`cli.py:405-409`) and `seal()` returns `"partial"` (test-confirmed). But `with ThreadPoolExecutor(...) as ex:` (`cli.py:397`) blocks on `shutdown(wait=True)` past the declared timeout — independently reproduced (declared `timeout=1`, measured wall time 4.20s) |
| 3 | SCALE-03: Resume validates identity (model or profile) before any write, rejecting a mismatch with nothing persisted; reads pin to sealed SHAs | ✗ FAILED | `check_resume_identity()` runs before `CoverageManifest` construction (`cli.py:322-328`), confirmed byte-hash-unchanged on rejection; SHA-pinning-on-resume confirmed (`resolve_ref_sha` round-trip). But the `review` argparse subparser declares no `--model` flag and `main()` never passes `model=` to `run_review()` — the model half of the identity gate is unreachable through any real CLI invocation (confirmed: `--model opus` → `error: unrecognized arguments`) |
| 4 | OUT-01: A diff-anchored comment payload `{path, line, side, existing_code, content}` is written alongside SARIF/markdown/per-finding files, with the coverage manifest included so completeness is legible without inferring it from the file's presence | ✗ FAILED | 5-key `DiffComment` payload confirmed (`review_comments.py`); atomic write confirmed; a manifest dict IS embedded — but `cli.py` calls `write_review_comments(ws, comments, manifest.to_dict())` *before* `manifest.seal()` runs (`cli.py:523` vs `526`), so the embedded `coverage_manifest.seal` is always `null`, falsifying the documented completeness signal |
| 5 | OUT-02: SARIF fingerprints key on `Path|Category|ExistingCode`, excluding message text | ✓ VERIFIED | `sarif.py`'s `_sarif_fingerprint()`: `f"{finding.file}|{finding.cls}|{finding.evidence.strip()}"`, sha256-truncated, no Unicode normalization (deliberate, documented); message excluded; `to_sarif([])` yields zero `partialFingerprints` occurrences; 8 dedicated tests pass |

**Score:** 2/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `sec_overlay/bundle.py` | `group_bundles()` real grouping semantics | ✓ VERIFIED | Pure, total, documented, 14 tests pass |
| `sec_overlay/review_agent.py` | `bundle_paths` focus-widening in `parse_review_response` | ✓ VERIFIED | `entry_path not in members` check + `file=entry_path` attribution confirmed |
| `sec_overlay/cli.py` | Three bounded flags, pooled git fetch, per-unit timeout, resume-identity gate | ⚠️ PARTIAL | Flags/pooling/timeout-marking exist and are wired, but two specific behaviors (wall-clock timeout enforcement, model identity) are not reachable/correct in production — see gaps |
| `sec_overlay/review_coverage.py` | `MANIFEST_VERSION` 2, `model`/`profile` fields, `check_resume_identity`, `ResumeIdentityError` | ✓ VERIFIED | Present, correctly ordered relative to manifest construction |
| `sec_overlay/review_comments.py` | 5-key comment payload + embedded coverage manifest | ⚠️ HOLLOW | Shape correct; embedded manifest's `seal` field is always stale (pre-seal) in every real run |
| `sec_overlay/sarif.py` | `partialFingerprints` on `Path|Category|ExistingCode` | ✓ VERIFIED | Confirmed by direct code read and passing tests |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `cli.run_review` | `bundle.group_bundles` | builds `bundle_paths_by_path`, threads into `recorded_return_source` | ✓ WIRED | Confirmed at `cli.py` review_source construction |
| `review_agent.parse_review_response` | unit membership | `bundle_paths` param, `entry_path in members` check | ✓ WIRED | Confirmed line-level |
| `cli.run_review` | `CoverageManifest`/`check_resume_identity` | identity check before manifest construction | ✓ WIRED (profile only) | `model` param exists on the function but has no CLI argument feeding it — NOT_WIRED at the CLI surface |
| `cli.run_review` | `write_review_comments` | `manifest.to_dict()` passed at write time | ⚠️ WIRED BUT WRONG ORDER | Write happens before `seal()`, so the link delivers stale data |
| `cli.run_review` | `to_sarif` | via `report.write_report` | ✓ WIRED | Confirmed |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `--timeout` bounds wall-clock execution on a hung unit | `uv run pytest tests/test_cli.py::test_review_unit_timeout_fails_every_member_with_timeout_note -q` | `1 passed in 4.20s` against a declared `timeout=1` in the test's own setup | ✗ FAIL — confirms CR-03 independently |
| `--model` reaches the CLI | `uv run python -m sec_overlay.cli review --model opus --base HEAD --root /tmp` | `error: unrecognized arguments: --model opus` | ✗ FAIL — confirms CR-02 independently |
| Embedded manifest ordering | `grep -n "write_review_comments\|manifest.seal()" cli.py` | `write_review_comments(...)` at line ~523, `manifest.seal()` at line ~526 (write precedes seal) | ✗ FAIL — confirms CR-01 independently |
| Full suite regression | `uv run pytest -q` (run once) | `1242 passed, 2 failed` — both failures are the documented pre-existing environmental baseline (`test_bench.py::test_seed_corpus_is_valid`, `test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd`) | ✓ PASS — zero new regressions |
| Lint/type cleanliness | `uv run ruff check sec_overlay/ bench/ tests/`, `uv run ty check` | Both "All checks passed!" | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SCALE-01 | 04-01-PLAN.md | Bundle grouping + focus rule | ✓ SATISFIED | `bundle.py`, `review_agent.py`, 14+3 tests |
| SCALE-02 | 04-02-PLAN.md | Bounded flags + timeout | ✗ BLOCKED | `--timeout` does not bound wall-clock execution (CR-03) |
| SCALE-03 | 04-03-PLAN.md | Resume identity + SHA pinning | ✗ BLOCKED | Model half of identity gate has no CLI surface (CR-02) |
| OUT-01 | 04-01-PLAN.md | Diff-anchored comment payload + manifest | ✗ BLOCKED | Embedded manifest's `seal` always `null` (CR-01) |
| OUT-02 | 04-01-PLAN.md | SARIF fingerprint contract | ✓ SATISFIED | `sarif.py`, 8 tests |

No orphaned requirements — all five phase-declared IDs (SCALE-01, SCALE-02, SCALE-03, OUT-01, OUT-02) appear in a plan's `requirements` frontmatter and are traced above. REQUIREMENTS.md marks all five `[x]` Complete; this verification disagrees with three of those five markings for the reasons above.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `sec_overlay/cli.py` | ~523-530 | `write_review_comments()` called before `manifest.seal()` | 🛑 Blocker | OUT-01's completeness signal is always false (`seal: null`) |
| `sec_overlay/cli.py` | ~576-611, ~670-682 | `review` subparser has no `--model` arg; `main()` never passes `model=` | 🛑 Blocker | SCALE-03's model-identity gate is dead code in production |
| `sec_overlay/cli.py` | ~397-411 | `with ThreadPoolExecutor(...) as ex:` implicit `shutdown(wait=True)` on exit | 🛑 Blocker | SCALE-02's `--timeout` does not bound wall-clock execution on a hung unit |
| `sec_overlay/bundle.py` | 30 | `_LOCALE_STEM` regex misses lowercase-region (`pt-br`), underscore (`pt_BR`), 3-letter (`fil`/`haw`) codes | ⚠️ Warning | Fails safe (single-file fallback) but under-delivers grouping for these formats; non-blocking against literal SC1 wording |
| `sec_overlay/sarif.py` | ~71 | Fingerprint key omits `line`; same file/cls/evidence at different lines collide | ⚠️ Warning | Non-blocking against literal SC5 wording (no line-disambiguation requirement) |
| `sec_overlay/cli.py` | ~353-357 | Diff-line-count prefetch's `_bounded_map` uses plain `ex.map()` with no timeout | ⚠️ Warning | Unprotected phase distinct from the per-unit fetch loop; not the literal SC2 fetch-loop scope |
| `sec_overlay/cli.py` / `SKILL.md` | — | `--concurrency` validated in Python core, enforced only by `SKILL.md`'s dispatch loop | ℹ️ Info | Explicit, documented design decision (T-04-09 in 04-02-PLAN.md); not a defect |

No unreferenced `TBD`/`FIXME`/`XXX` markers found in phase-modified files.

### Deferred Items

None. All three blockers were considered against Step 9b's later-phase matching: Phase 5 (AUD-01..06) and Phase 6 (REL-01..03, "every defect observed in the verification runs is fixed or given a written disposition") were checked. REL-01's wording is a milestone-wide catch-all with no phase-4-specific evidence, and the methodology requires conservative matching — a vague catch-all does not defer a direct contradiction of this phase's own literal Success Criteria. These three gaps are native to Phase 4 and are reported as gaps here, not deferred.

### Human Verification Required

None. All three gaps were independently confirmed by direct code reading and reproducible commands (grep evidence, a real CLI invocation, and a timed test run) — no item requires subjective human judgment to resolve.

### Gaps Summary

Phase 4's own prior code-review artifact (`04-REVIEW.md`, dated the same day as phase completion) already identified these three defects (there labeled CR-01/CR-02/CR-03) with concrete fix snippets. Git history (`6b671d2` through `84aa291`) shows zero remediation commits after the review was written — the defects are still live in the current working tree, independently re-confirmed here by direct code inspection, a real CLI invocation, and a timed test run rather than by trusting the review's narrative.

All three break the literal wording of a ROADMAP.md Success Criterion for this phase, not merely a nice-to-have:

1. **OUT-01** — "with the coverage manifest included" is satisfied structurally (a manifest dict is present) but not functionally: the manifest is captured *before* `seal()` runs, so its `seal` field is always `null`, meaning a consumer reading `review_comments.json` can never actually tell a complete run from a partial one — the exact case the manifest was embedded to solve (module docstring; plan's T-04-04 threat mitigation).
2. **SCALE-03** — "an implicit model or profile change is rejected" is only half-true: `--profile`'s mismatch path works end to end, but no `--model` CLI flag exists, so the model-mismatch branch of `check_resume_identity` can never fire outside of a unit test that calls the function directly, bypassing `main()`.
3. **SCALE-02** — "`--timeout`... bound execution" is falsified for the case that matters most: a genuinely hung git subprocess. The per-unit timeout correctly marks the manifest `partial`, but the enclosing `with ThreadPoolExecutor(...) as ex:` block's `shutdown(wait=True)` on exit still blocks the whole CLI process until the abandoned thread finishes, independently confirmed by timing (declared `timeout=1`, measured 4.20s).

Two of the three plans' own SUMMARY.md files show the team came close to catching these: 04-01-SUMMARY.md's Task 3 explicitly checked `sarif.py`/`review_comments.py` for an implementation gap and (correctly, at the unit level) found none — the defect lives one layer up, in `cli.py`'s call ordering, which no test exercises. 04-02-SUMMARY.md's "Decisions Made" section explicitly names the `shutdown(wait=True)` tension and reasons through it without resolving it. Neither SUMMARY's "verified manually" or "full suite green" claims constitute evidence against these three gaps — the manual SCALE-03 check in 04-03-SUMMARY.md only exercised `--profile`'s path, never `--model`'s, which is exactly consistent with `--model` having no real CLI surface to exercise.

**Fix guidance** (already drafted with more detail in `04-REVIEW.md`):
- Reorder `cli.py` to call `manifest.seal()` before `write_review_comments()`, or re-write the comments file after sealing.
- Add `review.add_argument("--model", default=None)` to the `review` subparser and pass `model=args.model` at the `run_review()` call site.
- Replace `with ThreadPoolExecutor(...) as ex:` with an explicit `try/finally` calling `ex.shutdown(wait=False)`, and consider a subprocess-level kill for a complete fix.

---

_Verified: 2026-08-20T19:06:21Z_
_Verifier: Claude (gsd-verifier)_
