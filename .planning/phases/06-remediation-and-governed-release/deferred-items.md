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

## 06-02

- **`skills/sec-overlay/README.md`'s CLI-legend block already documented
  `selfscore` in the wrong position** (after `postflight`, no phase number)
  before this plan touched it. Task 3 moved the line to its correct spot
  (right after `report`, before `redteam`) as a one-line adjacent fix while
  already editing that block, but did not otherwise audit the file for
  further pre-existing misorderings.
- **`skills/sec-overlay/helpers/README.md`'s deterministic-pipeline mermaid
  diagram never had nodes for `selfscore`, `artifact-gate`, or
  `artifact-review`** — it jumps from `findings_gate.py` (post-verify) to
  `report.py` and then (pre-06-02) straight to `postflight.py`. Task 3
  fixed the `redteam`/`report`/`postflight` ordering it changed, but did not
  add the three missing nodes — that is a pre-existing simplification of
  the diagram, not something D-01 caused.
- **`skills/sec-overlay/CLAUDE.md`'s numbered "Phase order (one pass)" list
  never had a numbered `selfscore` entry**, before or after this plan
  (confirmed via `git diff 9e3892e -- .../CLAUDE.md`). `selfscore` runs
  between `report` and `redteam` per `PHASE_TABLE`, so the list is missing a
  step, not misordered. Pre-existing gap; out of scope for D-01.
