---
phase: 04-scale-resume-diff-output
reviewed: 2026-08-20T18:00:00Z
depth: standard
files_reviewed: 24
files_reviewed_list:
  - CHANGELOG.md
  - README.md
  - plugins/sec-overlay/.claude-plugin/plugin.json
  - plugins/sec-overlay/CHANGELOG.md
  - plugins/sec-overlay/skills/sec-overlay/README.md
  - plugins/sec-overlay/skills/sec-overlay/SKILL.md
  - plugins/sec-overlay/skills/sec-overlay/helpers/README.md
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/bundle.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_agent.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_comments.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_coverage.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/sarif.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_bundle.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_cli.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_agent.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_comments.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_coverage.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_live.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_tracer.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_rule_glob.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_sarif.py
findings:
  critical: 3
  warning: 3
  info: 1
  total: 7
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-08-20T18:00:00Z
**Depth:** standard
**Files Reviewed:** 24
**Status:** issues_found

## Summary

Phase 04 shipped three plans against `sec-overlay`'s diff-scoped `review` CLI: bundle grouping
+ diff-anchored comments (04-01), bounded concurrency/timeout flags (04-02), and a resume-identity
+ SHA-pinning gate (04-03). The review scoped to the `git diff 6b671d2^..HEAD` delta for the six
core implementation files (`bundle.py`, `cli.py`, `review_agent.py`, `review_comments.py`,
`review_coverage.py`, `sarif.py`) and cross-checked every claim against the shipped tests, then
against a live run of `run_review`/the CLI entry point where a claim looked exploitable.

All 121 tests in the six touched test modules pass (`uv run pytest -q tests/test_review_coverage.py
tests/test_cli.py tests/test_bundle.py tests/test_sarif.py tests/test_review_agent.py
tests/test_review_comments.py`), but passing tests here mask three real defects: none of them
exercise the specific call-site ordering, CLI wiring, or wall-clock behavior each bug lives in.
Two are proven with a live repro below (not just static reading), and the third is proven by timing
an existing test.

- `review_comments.json`'s embedded `coverage_manifest` always reports `"seal": null` — the file's
  own stated purpose (let a consumer distinguish a complete run's comments from a partial run's
  without inferring it from the file's presence) never holds, because `write_review_comments` runs
  before `manifest.seal()`.
- The SCALE-03 resume-identity gate's `model` half is unreachable from the shipped CLI — there is no
  `--model` flag on `review`, so every real invocation pins `model=None` and the mismatch check can
  never fire. `--profile`'s half of the same gate does work end to end.
  Also verified live: `unrecognized arguments: --model opus`.
- `--timeout` bounds how long `run_review`'s consuming thread *waits for a result*, not how long the
  call can actually block: the `ThreadPoolExecutor`'s `with` block still calls `shutdown(wait=True)`
  on exit, so a unit whose git fetch genuinely hangs (network stall, lock contention) blocks the
  whole `review` invocation past `--timeout`, contradicting the documented and tested guarantee.
  Timing the shipped
  `test_review_unit_timeout_fails_every_member_with_timeout_note` test (declared `timeout=1`) shows
  it actually takes ~3.9s wall time — proof the abandoned worker thread keeps the call blocked well
  past the stated bound.

## Critical Issues

### CR-01: `review_comments.json`'s embedded coverage manifest is always unsealed

**File:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py:523-530`
**Issue:** `write_review_comments(ws, comments, manifest.to_dict())` (line 524) runs before
`manifest.seal()` (line 529). `CoverageManifest.to_dict()` serializes `self._seal`, which is still
`None` at line 524 — `seal()` is the only method that ever sets it, and it runs five lines later.
Verified with a live run: after a real `run_review()` call that returns `rc == 0` and writes
`coverage_manifest.json` with `"seal": "complete"` on disk, the *embedded* manifest inside
`artifacts/review_comments.json` reads `"seal": null`. `review_comments.py`'s own module docstring
states the embedded manifest exists specifically "alongside the coverage manifest that says whether
the run producing it was complete" — that guarantee never holds for any real invocation, complete or
partial. No test in `test_cli.py` or `test_review_comments.py` reads `review_comments.json` after a
real `run_review()` call — the `test_review_comments.py` unit tests hand-construct an
already-sealed `_MANIFEST` dict directly, which is why this went uncaught.
**Fix:**
```python
# cli.py, replacing lines 523-535
comments = [comment_from_finding(rf.finding) for rf in review_findings]

if not selection.reviewable:
    write_review_comments(ws, comments, manifest.to_dict())
    return 0

seal = manifest.seal()
write_review_comments(ws, comments, manifest.to_dict())
if seal == "complete":
    return 0

for entry in manifest.entries():
    if entry.state != "done":
        print(f"unfinished file: {entry.path} (state={entry.state}, note={entry.note})")
return 3
```
Add a regression test that runs `run_review()` end to end and asserts
`review_comments.json["coverage_manifest"]["seal"]` equals the actual on-disk
`coverage_manifest.json["seal"]`, for both a complete and a partial run.

### CR-02: `--model` has no CLI flag — the resume-identity gate's model half is dead in production

**File:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py:576-611,670-682`
**Issue:** `run_review`'s `model` parameter (line 230) feeds `CoverageManifest(..., model=model, ...)`
(line 391) and `check_resume_identity(prior_manifest, model=model, profile=profile)` (line 325), and
the CHANGELOG (`plugins/sec-overlay/CHANGELOG.md:39-45`) documents this as a shipped guarantee:
"`review` rejects (exit 2) a resumed run whose `model` or `profile` differs from the prior
manifest's." But the `review` subparser (lines 576-611) defines `--base`, `--head`, `--root`,
`--profile`, `--rule`, `--exclude`, `--prepare`, `--concurrency`, `--timeout`, `--max-git-procs` —
never `--model` — and `main()`'s call site (lines 670-682) never passes `model=` to `run_review`,
so it silently takes its default of `None` on every real invocation. Verified live:
`uv run python -m sec_overlay.cli review --base HEAD --model opus --root /tmp` exits with
`sec-overlay: error: unrecognized arguments: --model opus`. Since every real run's `model` is
always `None`, and `check_resume_identity`'s model branch only raises when
`prior.model is not None and prior.model != model`, `prior.model` recorded by any real run is
also always `None` — the model mismatch it is documented to catch can never occur through the
shipped CLI. Every test that exercises `model=` (`test_review_coverage.py`'s
`test_a_rejected_resume_leaves_the_manifest_byte_identical_and_writes_no_new_file` and its
siblings) calls `cli.run_review(...)` directly as a Python function, never through
`cli.main()`/argparse, which is why this gap has no failing test today. `--profile`'s half of the
same gate is wired correctly end to end (it has a real CLI flag).
**Fix:**
```python
# cli.py, in the `review` subparser block (~line 611)
review.add_argument(
    "--model",
    default=None,
    help="This run's model identity (SCALE-03); pinned into the coverage manifest. "
    "A resumed run recording a different model is rejected before any write.",
)

# in main(), the review call site (~line 671)
return run_review(
    args.base,
    args.head,
    args.root,
    profile=args.profile,
    rule_path=args.rule,
    excludes=args.exclude,
    prepare=args.prepare,
    concurrency=args.concurrency,
    timeout=args.timeout,
    max_git_procs=args.max_git_procs,
    model=args.model,
)
```

### CR-03: `--timeout` does not bound `run_review`'s actual wall-clock time

**File:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py:397-411`
**Issue:** The per-unit fetch loop opens `with ThreadPoolExecutor(...) as ex:` (line 398), submits
one future per `ReviewUnit`, then calls `future.result(timeout=timeout)` (line 405) inside the
`with` block. When that call raises `TimeoutError`, the code correctly marks every member of that
unit as failed (lines 406-411) — but the submitted task keeps running in the pool; Python's
`ThreadPoolExecutor` has no API to cancel a task that has already started. When the `for` loop
finishes and the `with` block exits, `ThreadPoolExecutor.__exit__` calls `self.shutdown(wait=True)`,
which blocks the calling thread until every submitted future — including the one that was just
reported as "timed out" — actually finishes. A genuinely hung git subprocess (network stall on a
fetch, lock contention, a corrupted pack) therefore blocks the whole `run_review()` call, and hence
the whole `review` CLI process, indefinitely — not for `--timeout` seconds as the docstring
("timeout: Per-unit deadline in seconds (`--timeout`)... SCALE-02") and the test's own docstring
("fails every one of its member files with the timeout note, sealing the manifest partial") both
claim. Proven without fabricating a hang: the shipped
`test_review_unit_timeout_fails_every_member_with_timeout_note` test declares `timeout=1` against a
fake runner that sleeps `1.2s` per file across 3 files fetched sequentially by one worker thread
(`~3.6s` of real work); the test asserts `rc == 3` and passes, but running it in isolation
(`uv run pytest -q tests/test_cli.py::test_review_unit_timeout_fails_every_member_with_timeout_note`)
takes `~3.9s` wall time — the excess ~2.9s beyond the declared 1-second timeout is exactly the
implicit `shutdown(wait=True)` blocking on the abandoned thread. The assertions never check elapsed
time, so this went uncaught. The same defect class extends to the diff-line-count prefetch phase
(see WR-03).
**Fix:** Do not let the executor's context-manager exit block on a future the code has already
given up on:
```python
if units:
    ex = ThreadPoolExecutor(max_workers=min(max_git_procs, len(units)))
    try:
        futures = [
            ex.submit(_fetch_review_unit_files, unit.files, base_sha, head_sha, r)
            for unit in units
        ]
        for unit, future in zip(units, futures):
            try:
                fetch_by_path.update(future.result(timeout=timeout))
            except TimeoutError:
                fetch_by_path.update(
                    {path: TimeoutError(TIMEOUT_NOTE) for path in unit.files}
                )
    finally:
        ex.shutdown(wait=False)
```
This stops `run_review` itself from blocking past `--timeout`. Note the underlying thread (and the
subprocess it is waiting on) is still leaked in the background until it eventually finishes on its
own — a complete fix also needs the injected `runner`/subprocess call itself to accept a timeout
(e.g. `subprocess.run(..., timeout=...)`) so the hung process is actually killed, not just abandoned
by the consuming code. At minimum, land the `shutdown(wait=False)` change and file the subprocess-level
kill as a follow-up so the documented guarantee holds for the caller even if a leaked thread persists.

## Warnings

### WR-01: Locale-sibling regex misses lowercase-region and 3-letter locale codes

**File:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/bundle.py:30`
**Issue:** `_LOCALE_STEM = re.compile(r"^[a-z]{2}(-[A-Z]{2})?$")` only matches a bare 2-letter code or
a 2-letter code with an upper-case, hyphen-separated region (`en`, `en-US`, `pt-BR`). It silently
fails to match — and therefore never groups — the equally common lowercase-region spelling
(`pt-br`), underscore-separated locale tags (`pt_BR`), or 3-letter ISO 639-2 codes (`fil`, `haw`).
`test_bundle.py` only exercises `en.json`/`fr.json` (bare 2-letter codes), so this gap is untested.
The failure mode is safe (falls back to independent single-file units, never crashes and never
mis-groups two unrelated files), but it silently defeats the SCALE-01 grouping guarantee — and the
"one slow member's `--timeout` fails its bundle-mates together" benefit that grouping exists for —
for a class of real-world locale filenames.
**Fix:**
```python
_LOCALE_STEM = re.compile(r"^[a-z]{2,3}([-_][A-Za-z]{2,4})?$", re.IGNORECASE)
```
Add `test_bundle.py` cases for `pt-br.json`/`pt-BR.json` (lowercase region) and `pt_BR.json`
(underscore separator) alongside the existing `en`/`fr` case.

### WR-02: SARIF fingerprint can collide for two distinct findings in the same file

**File:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/sarif.py:71`
**Issue:** `key = f"{finding.file}|{finding.cls}|{finding.evidence.strip()}"` deliberately omits
`message` (documented, correct) but also omits `line`. Two distinct findings in the same file,
same defect class, whose evidence line is byte-identical text (a duplicated pattern — e.g. the same
`except Exception:` or the same inline query-construction snippet copy-pasted at two call sites in
one file) will produce the exact same `partialFingerprints` value in the same SARIF document.
`partialFingerprints` exists to let a downstream tool (GitHub code scanning, etc.) correlate *the
same* result across runs; two genuinely different results sharing one fingerprint within a single
run risks a consumer treating them as one alert and hiding one. `test_sarif.py`'s new
`partialFingerprints` tests cover file/cls/evidence/message differentiation individually but never
a same-file/same-cls/same-evidence/different-line pair, so this collision is untested.
**Fix:** Disambiguate same-evidence repeats deterministically without reintroducing full
line-number brittleness — e.g. fold in the 0-based occurrence index of this exact
`(file, cls, evidence)` triple within the finding list being serialized:
```python
def _sarif_fingerprint(finding: Finding, occurrence: int) -> str:
    key = f"{finding.file}|{finding.cls}|{finding.evidence.strip()}|{occurrence}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
```
computing `occurrence` as a running per-key counter in `to_sarif`'s loop over `findings`. Add a
test asserting two findings sharing file/cls/evidence but different `line` values still get
distinct fingerprints.

### WR-03: The diff-line-count prefetch phase has no `--timeout` protection at all

**File:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py:353-357`
**Issue:** `_bounded_map(records, max_git_procs, lambda record: file_diff_line_count(...))` (used to
size the worker pool for computing each changed file's diff-line count before file selection)
dispatches through `_bounded_map`'s plain `ex.map(fn, items)` (line 107) with no timeout argument
at all — unlike the per-unit fetch loop, which at least attempts a timeout (see CR-03). A hang in
this earlier phase (same class of failure: a stuck `git diff` subprocess) blocks `run_review`
indefinitely with no `--timeout` involved whatsoever, before the code has even reached the phase
`--timeout` is documented to bound.
**Fix:** Either document explicitly that `--timeout` only bounds the per-unit fetch phase and not
line-count prefetch (update the `timeout` docstring at `cli.py:284-285`), or thread the same
per-call bound through this phase too, e.g. by giving `_bounded_map` an optional `timeout=` that
wraps each `fn(item)` call the same way the per-unit loop does.

## Info

### IN-01: `--concurrency` is a Python-core-validated, agent-enforced-only bound

**File:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py:593-599`
**Issue:** `--concurrency`'s help text and `run_review`'s docstring (lines 280-283) are candid that
this bound is validated and recorded here but enforced only by whichever agent dispatches
`review-file` subagents per `SKILL.md`'s loop — the Python core never spawns an agent. This is
documented, not hidden, so it is not a defect on its own; noting it here because it means the
enforcement point lives entirely outside this codebase's test suite, and a dispatching agent that
ignores the documented ceiling has no code-level backstop that would catch it.
**Fix:** No change required. If a code-level backstop is ever wanted, `SKILL.md`'s dispatch loop is
the only place it could go (e.g. a lockfile-based live-subagent counter under the workspace); not
worth building speculatively.

---

_Reviewed: 2026-08-20T18:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
