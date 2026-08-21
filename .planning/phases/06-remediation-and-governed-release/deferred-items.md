# Deferred Items — Phase 06

Out-of-scope discoveries logged per the executor's scope-boundary rule. Not
fixed here; recorded for a later pass.

## 06-01

- **Pre-existing ruff `I001` (unsorted import block) in
  `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_cli.py:778`** —
  found while running `uv run ruff check sec_overlay/ tests/` during Task 1
  verification. Not touched by 06-01 (confirmed via `git diff --stat` showing
  no changes to `test_cli.py`). Pre-dates this plan; leave for whichever plan
  next modifies that file.
- **CodeRabbit nitpick — `test_rule_glob.py:231` doesn't assert `--workspace`
  forwarding.** The spy accepts `workspace=None` but the test never passes
  `--workspace` through `main()` or asserts the captured value, so the
  parser-to-`run_review` contract for this one flag is unverified. From
  PR #23 review.
- **CodeRabbit nitpick — WR-01 tests don't prove the guard runs before
  git.** `test_run_review_rejects_a_nonexistent_root_with_exit_2` and its two
  siblings (`test_review_live.py:403-432`) assert exit 2 and the stderr
  message, but use a normal runner — a later git failure converted to exit 2
  would also pass. A runner stub that fails if invoked would pin the
  "before any git call" ordering claim. From PR #23 review.
