---
phase: 04-scale-resume-diff-output
verified: 2026-08-20T21:15:00Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 2/5
  gaps_closed:
    - "OUT-01: review_comments.json carries the coverage manifest alongside the comment payload so a consumer can tell whether the run producing it was complete or partial, without inferring it from the file's presence"
    - "SCALE-03: Resume validates identity before any agent spawn — an implicit model or profile change is rejected with nothing persisted"
    - "SCALE-02: --concurrency, per-bundle --timeout, and --max-git-procs bound execution; a timed-out bundle marks its files failed and the run terminal state becomes partial"
  gaps_remaining: []
  regressions: []
deferred: []
---

# Phase 4: Scale, Resume & Diff Output Verification Report

**Phase Goal:** Large changesets stay bounded and resumable, and every shipped finding carries a diff-anchored, positioning-confirmed location.
**Verified:** 2026-08-20T21:15:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure (04-04-PLAN.md / 04-04-SUMMARY.md)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SCALE-01: `bundle.py` groups locale/config siblings and impl/test pairs into review units, one file per unit as fallback, documented as beyond OCR | ✓ VERIFIED | Regression-checked: `bundle.py` unchanged since prior verification; `uv run pytest tests/test_bundle.py tests/test_review_agent.py -q` → 41 passed (`plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_bundle.py`, `tests/test_review_agent.py`) |
| 2 | SCALE-02: `--concurrency`/`--timeout`/`--max-git-procs` bound execution; a timed-out bundle marks its files failed and the run seals `partial` | ✓ VERIFIED | Gap closed. `cli.py:426-442`: unit-fetch executor is now an explicit instance wrapped in `try`/`finally` calling `ex.shutdown(wait=False)` (was a `with`-block that blocked on exit). `cli.py:335`: production runner default is `partial(subprocess.run, timeout=timeout)`, so every real git call carries a kill deadline. Independently re-ran the previously-failing behavior: `test_review_returns_before_hung_unit_fetch_completes` now measures `elapsed < 2.0s` (was 4.20s pre-fix) and passed; `test_review_abandoned_unit_fetch_stops_at_the_unit_deadline` confirms the abandoned worker stops fetching past its deadline; `test_review_production_git_calls_carry_subprocess_timeout` confirms every real `subprocess.run` call receives `timeout=42` when declared. All three ran green (`uv run pytest tests/test_cli.py -k "hung_unit or abandoned_unit or production_git_calls" -q` → 3 passed) |
| 3 | SCALE-03: Resume validates identity (model or profile) before any write, rejecting a mismatch with nothing persisted; reads pin to sealed SHAs | ✓ VERIFIED | Gap closed. `cli.py:646-651`: `review` subparser now declares `--model` (default `None`); `cli.py:722`: `main()` forwards `model=args.model` to `run_review()`. `check_resume_identity()` still runs (`cli.py:346`) before `CoverageManifest` construction (`cli.py:412`) and before any write, for both `model` and `profile`. Re-ran: `uv run python -m sec_overlay.cli review --help` now lists `--model`; a real invocation with `--model opus` no longer raises `unrecognized arguments` (previously reproduced failure). `test_review_accepts_model_flag_and_forwards_it_to_run_review` and `test_review_resume_with_changed_model_exits_2_via_main_entrypoint` both pass, the latter driving two full `cli.main()` calls and asserting exit code 2 with stderr naming both the old and new model values |
| 4 | OUT-01: A diff-anchored comment payload `{path, line, side, existing_code, content}` is written alongside SARIF/markdown/per-finding files, with the coverage manifest included so completeness is legible without inferring it from the file's presence | ✓ VERIFIED | Gap closed. `cli.py:560-561`: `seal = manifest.seal()` now runs *before* `write_review_comments(ws, comments, manifest.to_dict())` (previously reversed). Re-ran the two new tests that read both artifacts and assert equality end-to-end through a real `run_review()` call: `test_review_comments_embedded_manifest_seal_matches_on_disk_after_complete_run` (embedded seal == on-disk seal == `"complete"`) and `test_review_comments_embedded_manifest_seal_is_partial_after_partial_run` (both == `"partial"`). Both pass |
| 5 | OUT-02: SARIF fingerprints key on `Path|Category|ExistingCode`, excluding message text | ✓ VERIFIED | Regression-checked: `sarif.py` unchanged since prior verification; `uv run pytest tests/test_sarif.py -q` → included in the 41-pass regression run above |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `sec_overlay/bundle.py` | `group_bundles()` real grouping semantics | ✓ VERIFIED | Unchanged, regression-passed |
| `sec_overlay/review_agent.py` | `bundle_paths` focus-widening in `parse_review_response` | ✓ VERIFIED | Unchanged, regression-passed |
| `sec_overlay/cli.py` | Three bounded flags, pooled git fetch, per-unit timeout, resume-identity gate, `--model` surface, seal-before-write ordering | ✓ VERIFIED | All three 04-04 fixes confirmed present and behaviorally exercised (see truths 2-4 above) |
| `sec_overlay/review_coverage.py` | `MANIFEST_VERSION` 2, `model`/`profile` fields, `check_resume_identity`, `ResumeIdentityError` | ✓ VERIFIED | Unchanged, still correctly ordered relative to manifest construction |
| `sec_overlay/review_comments.py` | 5-key comment payload + embedded coverage manifest | ✓ VERIFIED | Shape unchanged; embedded manifest's `seal` field now matches on-disk seal for both complete and partial runs |
| `sec_overlay/sarif.py` | `partialFingerprints` on `Path|Category|ExistingCode` | ✓ VERIFIED | Unchanged, regression-passed |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `cli.run_review` | `bundle.group_bundles` | builds `bundle_paths_by_path`, threads into `recorded_return_source` | ✓ WIRED | Unchanged from prior verification |
| `review_agent.parse_review_response` | unit membership | `bundle_paths` param, `entry_path in members` check | ✓ WIRED | Unchanged from prior verification |
| `cli.main` | `run_review` model param | `args.model` from `--model` argparse arg → `model=args.model` kwarg | ✓ WIRED | `cli.py:647-651` (argparse) → `cli.py:722` (call site); confirmed by `test_review_accepts_model_flag_and_forwards_it_to_run_review` |
| `cli.run_review` | `CoverageManifest`/`check_resume_identity` | identity check before manifest construction, now reachable for both `model` and `profile` via the CLI | ✓ WIRED | `cli.py:322-346` before `cli.py:412`; confirmed end-to-end via `cli.main()` in `test_review_resume_with_changed_model_exits_2_via_main_entrypoint` |
| `cli.run_review` | `write_review_comments` | `manifest.seal()` result embedded via `manifest.to_dict()` at write time | ✓ WIRED (correct order) | `cli.py:560` (`seal = manifest.seal()`) precedes `cli.py:561` (`write_review_comments(...)`); confirmed by direct on-disk/embedded seal equality tests |
| `cli.run_review` unit-fetch | `ThreadPoolExecutor` lifetime | explicit instance + `try`/`finally` `shutdown(wait=False)`, plus per-call `subprocess.run(timeout=...)` | ✓ WIRED | `cli.py:426-442` (executor lifetime), `cli.py:335` (subprocess-level kill); confirmed by wall-clock timing test (1.01s vs pre-fix 4.20s) |
| `cli.run_review` | `to_sarif` | via `report.write_report` | ✓ WIRED | Unchanged from prior verification |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `--timeout` now bounds wall-clock execution on a hung unit | `uv run pytest tests/test_cli.py -k "embedded_manifest_seal or model or hung_unit or abandoned_unit or production_git_calls" -q --durations=10` | `7 passed in 3.02s`; `test_review_returns_before_hung_unit_fetch_completes` took 1.01s (was 4.20s pre-fix) | ✓ PASS |
| `--model` reaches the CLI | `uv run python -m sec_overlay.cli review --help \| grep -- "--model"` | `--model MODEL` listed with help text | ✓ PASS |
| `--model` no longer rejected by argparse | `uv run python -m sec_overlay.cli review --model opus --base HEAD~1 --head HEAD --root /tmp` | exit 0, no `unrecognized arguments` error (previously reproduced failure) | ✓ PASS |
| Embedded manifest ordering | `grep -n "seal = manifest.seal()\|write_review_comments(ws, comments, manifest.to_dict())" cli.py` | `seal = manifest.seal()` at line 560, `write_review_comments(...)` at line 561 (seal precedes write) | ✓ PASS |
| Full suite regression (run once) | `uv run pytest -q` | `2 failed, 1249 passed` — both failures are the documented pre-existing environmental baseline (`test_bench.py::test_seed_corpus_is_valid`, `test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd`) | ✓ PASS — zero new regressions |
| Type cleanliness | `uv run ty check` | "All checks passed!" | ✓ PASS |
| Lint cleanliness | `uv run ruff check sec_overlay/ bench/ tests/` | 1 error: `I001` unsorted import block in `tests/test_cli.py:778` (inside `test_review_resume_with_changed_model_exits_2_via_main_entrypoint`, one of the 7 new tests) | ⚠️ WARNING — see Anti-Patterns |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SCALE-01 | 04-01-PLAN.md | Bundle grouping + focus rule | ✓ SATISFIED | Unchanged, regression-passed |
| SCALE-02 | 04-02-PLAN.md, 04-04-PLAN.md (gap closure) | Bounded flags + timeout actually bounds wall clock | ✓ SATISFIED | Executor lifetime + subprocess-level kill fix confirmed behaviorally |
| SCALE-03 | 04-03-PLAN.md, 04-04-PLAN.md (gap closure) | Resume identity (model + profile) + SHA pinning | ✓ SATISFIED | `--model` CLI surface wired and enforced through `main()` |
| OUT-01 | 04-01-PLAN.md, 04-04-PLAN.md (gap closure) | Diff-anchored comment payload + manifest | ✓ SATISFIED | Embedded manifest's `seal` now matches on-disk seal for complete and partial runs |
| OUT-02 | 04-01-PLAN.md | SARIF fingerprint contract | ✓ SATISFIED | Unchanged, regression-passed |

No orphaned requirements — all five phase-declared IDs (SCALE-01, SCALE-02, SCALE-03, OUT-01, OUT-02) appear in a plan's `requirements` frontmatter (04-01, 04-02, 04-03, and gap-closure 04-04) and are traced above. REQUIREMENTS.md marks all five `[x]` Complete; this verification agrees with all five markings.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `tests/test_cli.py` | 778 | `I001` unsorted/unformatted import block inside `test_review_resume_with_changed_model_exits_2_via_main_entrypoint` (one of the 04-04 gap-closure tests) | ⚠️ Warning | Cosmetic lint regression against the project's Zero Warnings Policy; does not affect test correctness or any phase truth. `ty check` is still clean. Fixable with `ruff check --fix` |
| `sec_overlay/cli.py` | 310-319, 556-558 | `run_review`'s zero-reviewable-files early return never calls `.seal()` (deliberate, per T-02-05: `seal()` raises on an empty manifest) and never persists `coverage_manifest.json` at all; the embedded `coverage_manifest.seal` stays `null` for this input shape, contradicting the module's own docstring ("0 when the coverage manifest seals `complete` (including a diff with no reviewable files)"). Freshly identified as WR-01 in the 04-04 code review (`04-REVIEW.md`) | ⚠️ Warning | Pre-existing since 04-01 (not introduced or touched by 04-04). Explicitly out of scope for 04-04's `must_haves.truths`, which scope OUT-01 to "after any run_review() call that reaches a seal" — the zero-reviewable path never reaches a seal by design. Does not affect the phase's Success Criterion #4 wording ("with the coverage manifest included") for the common case (≥1 reviewable file). Low practical impact (nothing to resume when zero files were reviewed) but leaves a resumed run against a zero-file diff unrecognized as a resume |
| `sec_overlay/bundle.py` | 30, 65-66 | `_LOCALE_STEM` regex can group two unrelated non-locale source files (e.g. `id.py`/`ok.py`) sharing a two-letter stem in the same directory into one `ReviewUnit`, sharing failure/timeout blast radius. Freshly identified as WR-02 in the 04-04 code review | ⚠️ Warning | Pre-existing since 04-01. Non-blocking against literal SC1 wording (fails toward over-grouping, not under-grouping or a crash); explicitly listed as a non-goal in 04-04-PLAN.md's scope ("WR-01 (`_LOCALE_STEM` misses `pt-br`/`pt_BR`/`fil`)... Do not touch") |
| `sec_overlay/cli.py` | 443-444 | Direct `fetch_by_path[record.path]` dict index relies on an unstated cross-function invariant (`group_bundles` totality over `selection.reviewable`) with no local comment | ℹ️ Info | Invariant holds today and is well-tested (`test_bundle.py::test_group_bundles_every_path_appears_in_exactly_one_unit`); a future refactor of `units` construction could silently break it with no local signal |

No unreferenced `TBD`/`FIXME`/`XXX` markers found in phase-modified files.

### Deferred Items

None. All warnings above were checked against later-phase matching (Phase 5: AUD-01..06; Phase 6: REL-01..03). None are addressed by a later phase's stated goal or success criteria with specific, concrete evidence — they are recorded as open warnings here, consistent with 04-04-PLAN.md's own explicit non-goals list (WR-01/WR-02/IN-01, using that plan's own numbering, are declared out of scope and left open by design).

### Human Verification Required

None. All three previously-failed truths were independently re-confirmed by direct code reading, wall-clock timing measurement, and real CLI invocation — no item requires subjective human judgment to resolve.

### Gaps Summary

None. This is a re-verification after `04-04-PLAN.md` (gap closure, 6 commits: `70aaf9d`, `728ff73`, `36b08d0`, `7b72c75`, `80074fd`, `e6dcddc`) closed all three gaps recorded in the prior `04-VERIFICATION.md` (score 2/5, `status: gaps_found`):

1. **OUT-01** — `cli.py` now computes `seal = manifest.seal()` before calling `write_review_comments(ws, comments, manifest.to_dict())` (previously reversed), so the embedded `coverage_manifest.seal` in `review_comments.json` always matches the on-disk `coverage_manifest.json`'s seal for both complete and partial runs. Independently confirmed by direct code read (`cli.py:560-561`) and by running the two new tests, which drive a real `run_review()` call and assert equality against the on-disk artifact rather than a hand-built fixture.
2. **SCALE-03** — the `review` argparse subparser now declares `--model` (default `None`), and `main()` forwards `model=args.model` to `run_review()`. Independently confirmed by `uv run python -m sec_overlay.cli review --help` listing `--model` (the previously recorded `unrecognized arguments: --model opus` failure no longer reproduces), and by a test that drives two full `cli.main()` invocations and asserts exit code 2 with stderr naming both model values.
3. **SCALE-02** — the unit-fetch `ThreadPoolExecutor` is now an explicit instance wrapped in `try`/`finally` calling `ex.shutdown(wait=False)` (replacing the `with`-block whose implicit `shutdown(wait=True)` blocked past `--timeout`), and the production runner default became `partial(subprocess.run, timeout=timeout)` so every real git subprocess call carries a kill deadline equal to the declared `--timeout`. Independently re-measured: the previously-failing wall-clock reproduction (declared `timeout=1`, measured 4.20s) is now bounded — the equivalent test measures 1.01s.

All 5/5 phase-goal truths are verified with direct evidence (code reads, independently re-run tests, a real CLI invocation, and a wall-clock timing measurement), not by trusting SUMMARY.md's narrative. Three pre-existing, non-blocking warnings remain open by explicit design decision in `04-04-PLAN.md`'s own non-goals list and this verification's regression check, plus one new cosmetic lint warning (`ruff` `I001` in one of the seven new tests) that does not affect correctness or any phase truth.

---

_Verified: 2026-08-20T21:15:00Z_
_Verifier: Claude (gsd-verifier)_
