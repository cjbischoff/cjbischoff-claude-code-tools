---
phase: 02-diff-pipeline-positioning
reviewed: 2026-08-17T20:07:31Z
depth: standard
files_reviewed: 26
files_reviewed_list:
  - CHANGELOG.md
  - README.md
  - plugins/sec-overlay/.claude-plugin/plugin.json
  - plugins/sec-overlay/CHANGELOG.md
  - plugins/sec-overlay/skills/sec-overlay/helpers/README.md
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/diffhunks.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/file_select.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/positioning.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_coverage.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/workspace.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/diffscope.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phase_gate.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_cli.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_tracer.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_diffscope.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_phase_gate.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_diffhunks.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_file_select.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_positioning.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_coverage.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_workspace.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report.py
findings:
  critical: 3
  warning: 2
  info: 0
  total: 5
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-08-17T20:07:31Z
**Depth:** standard
**Files Reviewed:** 26
**Status:** issues_found

## Summary

Reviewed the Phase 2 "Diff Pipeline & Positioning" implementation: `diffhunks.py`,
`diffscope.py`, `file_select.py`, `positioning.py`, `phase_gate.py`, `review_coverage.py`,
`workspace.py`, `report.py`, and `cli.py`, plus their full test suites and folder READMEs/
CHANGELOGs.

Each module is internally well-built: `positioning.py`'s four-rung ladder, `review_coverage.py`'s
state machine, and `workspace.py`'s atomic-write/tolerant-read helpers all hold up to direct
inspection and their unit tests. The defects are at the **seams between modules** — three
integration points where one module's contract is violated by its only caller, and none of these
seams is currently exercised by an integration test:

1. `phase_gate.review_position_gate`'s `declines` output is typed as `Finding` objects, but
   `report.py`'s `position_reviews` consumers require `PositionResult` objects — a straight
   `AttributeError` waiting to happen the moment `review_position_gate`'s output is wired into
   `write_report` (CR-01).
2. `diffscope.resolve_ref_sha` never checks the subprocess return code, so a nonexistent-but-
   syntactically-valid ref resolves to an empty string instead of raising — silently defeating the
   documented "exit 2 on invalid ref" contract for `run_review` (CR-02).
3. `cli.run_review` calls `file_select.partition(records)` without the `diff_line_counts=`/
   `binary_paths=` keyword arguments that `diffscope.py` was built specifically to supply — the
   5000-line diff cap and binary-file exclusion can never trigger in the real CLI (CR-03).

Two further items are dead/stale documentation rather than runtime bugs (WR-01, WR-02).

## Critical Issues

### CR-01: `review_position_gate` returns raw `Finding` objects where `report.py` requires `PositionResult`

**File:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phase_gate.py:437-462`
**Issue:** `review_position_gate` appends the raw `finding` to `declines` whenever
`resolve_position` returns `decision == "needs-position-review"`:

```python
if result.decision == "needs-position-review":
    declines.append(finding)   # raw Finding, not the PositionResult
    continue
```

`report.py`'s `position_reviews` parameter is explicitly typed `list[PositionResult]` and every
consumer of it dereferences `PositionResult`-only fields that `Finding` does not have:
`render_position_review_section` (`report.py:677-678`) and `write_review_ledger`
(`report.py:703-709`) both access `r.claimed_path`, `r.claimed_line`, `r.snippet`, and `r.reason`.
`Finding` has none of these attributes (confirmed against `models.py`'s `Finding` dataclass). The
moment `run_review`'s `declines` list is passed to `write_report(..., position_reviews=declines)`
— the integration this milestone explicitly sets up for a later plan — it raises `AttributeError`
on the first declined finding.

This is untested today: `test_phase_gate.py:393-398`
(`test_needs_position_review_is_a_decline_not_a_drop_or_keep`) asserts `declines == [finding]`,
locking in the current (incompatible) shape, and `test_report.py`'s `position_reviews=` tests
always construct their own independent `PositionResult` via a local `_declined()` helper
(`test_report.py:897`) — the two are never composed together anywhere in the suite.

**Fix:** Append `result` (the `PositionResult`), not `finding`, to `declines`:

```python
if result.decision == "needs-position-review":
    declines.append(result)
    continue
```

Update `test_needs_position_review_is_a_decline_not_a_drop_or_keep` to assert against the
`PositionResult` shape, and add one integration test that pipes `review_position_gate`'s
`declines` output directly into `report.write_report(..., position_reviews=...)`.

### CR-02: `resolve_ref_sha` ignores the subprocess return code — invalid refs silently resolve to `""`

**File:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/diffscope.py:35-49`
**Issue:**

```python
def resolve_ref_sha(ref: str, *, runner=subprocess.run) -> str:
    validate_ref(ref)
    completed = runner(
        ["git", "rev-parse", "--verify", ref], capture_output=True, text=True, check=False
    )
    return completed.stdout.strip()
```

`check=False` means a nonexistent-but-syntactically-valid ref (e.g. `does-not-exist-branch`, which
passes `validate_ref`'s allowlist regex) makes `git rev-parse --verify` exit non-zero with empty
stdout, and this function returns `""` without ever consulting `completed.returncode`. `run_review`
calls this for both `base` and `head` (`cli.py:112-113`) and only catches `ValueError` — a bad ref
never raises one here, so `run_review` proceeds with `base_sha = ""` (or `head_sha = ""`), defeating
the function's own documented contract: `run_review`'s docstring (`cli.py:100-103`) states "2 on an
invalid `base`/`head` ref (D-06)". Instead, downstream git calls run against an empty SHA — most
likely producing an empty diff, which `run_review` currently short-circuits to a spurious **exit 0**
(`selection.reviewable` is empty → `cli.py:137-138`), reporting success on a call that named a ref
that does not exist.

No test in `test_diffscope.py`, `test_cli.py`, or `test_review_tracer.py` exercises a runner that
returns non-zero for `rev-parse --verify` — every fake runner used across the suite returns success
with a synthetic SHA.

**Fix:** Check `completed.returncode` and raise `ValueError` to reuse the exit-2 path `run_review`
already has:

```python
def resolve_ref_sha(ref: str, *, runner=subprocess.run) -> str:
    validate_ref(ref)
    completed = runner(
        ["git", "rev-parse", "--verify", ref], capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        raise ValueError(f"unresolvable ref: {ref!r}")
    return completed.stdout.strip()
```

Add a test with a fake runner returning `returncode=128` for `rev-parse --verify` and assert
`run_review` returns exit code 2.

### CR-03: `run_review` never passes the diff-size cap or binary-exclusion inputs into `partition`

**File:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py:119`
**Issue:**

```python
records = changed_file_records(base_sha, head_sha, runner=r)
selection = partition(records)
```

`file_select.partition` accepts `diff_line_counts=` and `binary_paths=` keyword arguments
specifically so the 5000-line diff cap (`DEFAULT_MAX_DIFF_LINES`) and binary-file exclusion can
apply. `diffscope.py` ships `file_diff_line_count` (`diffscope.py:90-106`) and `binary_paths`
(`diffscope.py:109-132`) precisely to produce these two inputs — both documented in
`sec_overlay/README.md` as feeding `file_select.partition`. `run_review` is the only production
caller of `partition` and calls it with neither argument, so every changed file is always treated
as zero-diff-lines and non-binary: the size cap and binary exclusion can never fire from the real
CLI, regardless of how large or binary a changed file actually is.

No test in `test_cli.py` or `test_review_tracer.py` asserts that `partition` receives these
kwargs, or that a large/binary diff is excluded via the `review` subcommand — `file_select.py`'s
own unit tests (`test_file_select.py`) verify the function works correctly in isolation, but the
wiring gap in its only caller is untested.

**Fix:** Compute and pass both inputs before partitioning:

```python
diff_line_counts = {
    r.path: file_diff_line_count(r.path, base_sha, head_sha, runner=r) for r in records
}
excluded_binary = binary_paths(base_sha, head_sha, runner=r)
selection = partition(records, diff_line_counts=diff_line_counts, binary_paths=excluded_binary)
```

Add a `test_cli.py` test with a fake runner reporting a >5000-line diff (or a binary numstat
marker) and assert the file lands in `selection.excluded`, not `selection.reviewable`.

## Warnings

### WR-01: `UNRESOLVED_POSITION_REASON` is defined and exported but never used

**File:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phase_gate.py:383-384`
**Issue:**

```python
OUTSIDE_DIFF_REASON = "outside-diff"
UNRESOLVED_POSITION_REASON = "unresolved-position"
DROP_REASONS: frozenset[str] = frozenset({OUTSIDE_DIFF_REASON, UNRESOLVED_POSITION_REASON})
```

`review_position_gate` (`phase_gate.py:437-462`) only ever constructs a `DroppedFinding` with
`reason=OUTSIDE_DIFF_REASON` (line ~455). `UNRESOLVED_POSITION_REASON` is never assigned anywhere
— confirmed by a repo-wide search of `helpers/` for the symbol, which returns only its own
definition. It exists in `DROP_REASONS` and could plausibly be relied on by a downstream consumer
(report rendering, filtering) that assumes both reasons are reachable, which they are not.
**Fix:** Either wire it in — e.g. reserve it for the case where `resolve_position` declines but
the finding is later dropped rather than surfaced for review — or remove the unused constant and
shrink `DROP_REASONS` to `frozenset({OUTSIDE_DIFF_REASON})` until an actual second drop reason
exists.

### WR-02: `run_review`'s docstring claims already-implemented behavior is future work

**File:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py:88-89`
**Issue:**

```python
"""Run one review pass end to end: resolve refs, select files, position, seal.

Wires exactly one changed file through every layer (the tracer path) —
batching over multiple files and exit codes 2/3 arrive in 02-02 and 02-05.
```

The function body directly below this docstring already batches over `selection.reviewable`
(a loop over multiple files, `cli.py:123-133`) and already implements exit codes 2 and 3
(`cli.py:114-116`, `cli.py:143-146`). The docstring is stale relative to its own implementation —
it describes the pre-02-02/02-05 tracer-only state while the code has moved on, which will mislead
the next maintainer into thinking batching/exit-code work is still pending.
**Fix:** Update the docstring to describe current behavior, e.g. drop the "arrive in 02-02 and
02-05" sentence and state plainly that batching and exit codes 2/3 are implemented; keep only the
still-accurate note that finding-source integration is future work.

---

_Reviewed: 2026-08-17T20:07:31Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
