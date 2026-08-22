# Phase 7: Test & Lint Debt Cleanup - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-22
**Phase:** 7-Test & Lint Debt Cleanup
**Areas discussed:** TEST-01 test shape, TEST-02 proof method, LINT-01 fix depth, Delivery & versioning

---

## TEST-01 test shape

| Option | Description | Selected |
|--------|-------------|----------|
| Extend existing test | Add `--workspace` to the existing CLI invocation and assert it in the fake `run_review` | ✓ |
| New dedicated test | Add a separate `test_review_cli_forwards_workspace_to_run_review` | |
| You decide | Claude picks at plan time | |

**User's choice:** Extend existing test; assert only `workspace`, not other kwargs.
**Notes:** None.

---

## TEST-02 proof method

| Option | Description | Selected |
|--------|-------------|----------|
| Zero-git-calls spy | Recording spy on `subprocess.run`; assert exit 2 and empty call list | ✓ |
| Ordered call log | Record guard and git events in one sequence and assert order | |
| Exploding git mock | `subprocess.run` raises; pass only if guard exits first | |

**User's choice:** Zero-git-calls spy, applied to all three WR-01 tests.
**Notes:** None.

---

## LINT-01 fix depth

| Option | Description | Selected |
|--------|-------------|----------|
| Autofix + full-repo check | `ruff check --fix` on the file, then `ruff check .` as the gate | ✓ |
| Manual edit + file check | Hand-swap imports, verify one file only | |

**User's choice:** Autofix + full-repo check. Other pre-existing findings are reported, not fixed.
**Notes:** None.

---

## Delivery & versioning

| Option | Description | Selected |
|--------|-------------|----------|
| One branch, one PR, one commit, one patch bump | Recommended default | ✓ |

**User's choice:** Auto-selected at the user's request ("do all the recommended fixes").
**Notes:** The user asked to accept all recommended options and proceed to implementation.

## Claude's Discretion

- Spy helper naming and placement in `test_review_live.py`.
- The `--workspace` argument value used in the TEST-01 invocation.

## Deferred Ideas

None.
