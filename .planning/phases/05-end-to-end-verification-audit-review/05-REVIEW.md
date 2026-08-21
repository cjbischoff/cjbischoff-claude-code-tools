---
phase: 05-end-to-end-verification-audit-review
reviewed: 2026-08-20T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - .gitignore
  - CHANGELOG.md
  - README.md
  - plugins/sec-overlay/.claude-plugin/plugin.json
  - plugins/sec-overlay/CHANGELOG.md
  - plugins/sec-overlay/skills/sec-overlay/helpers/README.md
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_live.py
findings:
  critical: 0
  warning: 2
  info: 0
  total: 2
status: issues_found
---

# Phase 05: Code Review Report

**Reviewed:** 2026-08-20T00:00:00Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Phase 05's substantive change is a 3-line fix in `cli.py:337` (`run_review`'s production
git runner now binds `cwd=root`) plus one new regression test in `test_review_live.py`.
I verified the fix against `diffscope.py` (`resolve_ref_sha`, `changed_file_records`,
`file_diff_line_count`, `binary_paths`, `file_diff_text`, `file_text_at_ref` — none pass
`-C <path>` of their own) and confirmed the previous unscoped runner really did depend on
the caller's process cwd matching `--root`, so the fix is correct and addresses a real bug.
`repo_slug` (called via the same `r`) is unaffected because it already passes `-C str(target)`
explicitly, so the new `cwd=root` binding is redundant-but-harmless there. The new test
exercises the real, uninjected `subprocess.run` path against a throwaway git repo distinct
from pytest's own cwd, which is the correct way to catch this specific class of bug (every
other test in the file monkeypatches `subprocess.run` with a fake that ignores `cwd`, so none
of them would have caught a cwd-scoping regression either before or after this fix).

Two issues found, both WARNING-tier — no BLOCKER. The fix's correctness is not in question;
the findings are a new failure mode it introduces for an invalid `--root`, and a factual
inaccuracy in the accompanying maintainer documentation.

## Warnings

### WR-01: Nonexistent `--root` now crashes with an unhandled `FileNotFoundError` instead of a clean `error:` exit

**File:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py:337`
**Issue:** The new `partial(subprocess.run, timeout=timeout, cwd=root)` runs `cwd=root` on
every git subprocess call made through `r`, including the very first one
(`RepoMemory.for_target(root, runner=r)` → `repo_slug` → `runner(["git", "-C", str(target), ...])`
at `repo_memory.py:86`, reached at `cli.py:339` before `memory.ensure()` has a chance to create
anything under `root`). Confirmed experimentally: `subprocess.run(cmd, cwd="/nonexistent/path")`
raises `FileNotFoundError: [Errno 2] No such file or directory: ...` before the child process
is even spawned — this is not caught anywhere in `run_review` (only `ValueError` and the
module's own exception types are caught around this region, `cli.py:345-373`), so it propagates
all the way to `main()` and crashes the CLI with a raw Python traceback and exit code 1.

Before this fix, a mistyped or missing `--root` would still misbehave (the exact silent-wrong-
result bug this patch fixes — git calls would run against the process's actual cwd rather than
erroring), but it would not crash: `git -C <bad-path> ...` is a normal git invocation that git
itself reports as a clean non-zero exit, handled gracefully by every caller (`repo_slug` checks
`res.returncode == 0`, `resolve_ref_sha` checks `completed.returncode != 0` and raises a caught
`ValueError`). The fix trades a silently-wrong result for a hard, unhandled crash on this specific
input — an improvement in correctness, but a regression in the CLI's own error-handling
convention, which elsewhere in this same function validates inputs up front and exits 2 with a
clear `error: ...` message (`_bounded_int`, `resolve_ref_sha`'s `ValueError`, `RuleSafetyError`,
`ResumeIdentityError`). No test in `test_review_live.py` or `test_review_tracer.py` exercises a
nonexistent `--root`.
**Fix:** Validate `root` is an existing directory before constructing `r`, and fail with the
same `error: ...` / exit-2 convention used for every other invalid input in this function:

```python
if not Path(root).is_dir():
    print(f"error: --root is not a directory: {root!r}", file=sys.stderr)
    return 2
```

### WR-02: `tests/README.md`'s explanation of why prior tests missed this bug is factually wrong

**File:** `plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md` (new paragraph, end of file)
**Issue:** The added paragraph states: "every other `run_review` test in this file injects
its own `runner`, which bypasses the bug entirely." This is not what the other tests in
`test_review_live.py` do. Grepping the file for `runner=` shows no call to `run_review(...)` or
`main([...])` anywhere in it passes a `runner=` keyword argument — every other test instead does
`monkeypatch.setattr(subprocess, "run", _fake_run_for(...))`, patching the stdlib function that
`run_review`'s own default (`r = runner or partial(subprocess.run, timeout=timeout, cwd=root)`)
still wraps. Because `partial(subprocess.run, ...)` resolves `subprocess.run` at call time (after
the monkeypatch is installed), those other tests *do* go through the exact same `cwd=root`-bound
code path as the new regression test — they just don't notice a wrong `cwd`, because their fake
(`_fake_run_for`'s `fake(cmd, capture_output, text, check, **kwargs)`) reads only `cmd` and
ignores every keyword argument, including `cwd`. The reason those tests never caught this bug is
that their fake doesn't consult `cwd` at all, not that they "inject a runner" that "bypasses" the
`r` construction — no test in this file uses the `runner=` parameter of `run_review` itself. This
matters because the sibling paragraph in `sec_overlay/README.md` gets the underlying mechanism
right ("`test_diffscope.py` and `test_review_live.py` fully mock the runner") while this
`tests/README.md` paragraph asserts a specific, different, and incorrect mechanism for one of
the two files it's talking about. Per this plugin's own `CLAUDE.md` ("Hard rule — docs track
code in the same commit"), the README is meant to be a precise technical reference, not
approximate prose.
**Fix:** Correct the claim to describe monkeypatching, not `runner=` injection, e.g.:

```
...every other `run_review` test in this file instead monkeypatches the stdlib
`subprocess.run` with a fake that reads only `cmd` and ignores every keyword
argument (including `cwd`), so a wrong `cwd` binding would not have made any of
them fail either before or after this fix.
```

---

_Reviewed: 2026-08-20T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
