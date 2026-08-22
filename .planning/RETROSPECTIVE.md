# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v5.0 — Hybrid Diff-Review Architecture

**Shipped:** 2026-08-22
**Phases:** 7 | **Plans:** 30 | **Tasks:** 116

### What Was Built

- A `review` verb on sec-overlay with `security` and `general` profiles: diff acquisition, file selection, a sealed coverage manifest, hunk positioning, and a phase gate — stdlib-only.
- Per-language rule resolution: 8 rule docs, four-layer per-path resolution, and a hard-reject rule-file safety gate.
- A retract-only, fail-open LLM reflection filter with a hardcoded protected-subject veto.
- Scale features: bounded concurrency, per-unit timeouts, identity-checked SHA-pinned resume, and diff-anchored SARIF output.
- End-to-end verification of both the audit and the review pipeline on real targets, with receipts.

### What Worked

- Receipt-backed baseline verification (Phase 1) surfaced 165 real diagnostics before any new code, so later phases built on a green base.
- The tracer-plan pattern (one thin end-to-end slice first, in Phases 2 and 6) exposed integration defects early: a hunk-parser bug and a `review_position_gate` signature mismatch.
- Code-derived doc guards (regex tests pinned to the code) stopped doc drift twice and caught a third stale claim during CodeRabbit review.
- The frozen-contract constraint held for the whole milestone: an empty `models.py`/`evidence.py` diff at every gate, later pinned by `test_frozen_contract.py` sha256 digests.

### What Was Inefficient

- Phase 5's AUD-06 profile-superset check passed vacuously (0 findings on both sides), which forced a substantive re-check (E-12) in Phase 6 with a real 14-file dispatch.
- The `gh pr merge`/`gh pr view` classifier denials in Phase 6 required the owner to merge PR #29 manually; no workaround existed in-session.
- DIFF-04 (review sidecar isolation) was missed in Phase 4 planning and needed an inserted gap-closure phase (04.1).
- CodeRabbit's open-source rate limit paused incremental reviews after 2 commits; 3 of 4 Phase 6 shipping PRs merged under a disclosed waiver.

### Patterns Established

- Every gate result gets a receipt; a red result is recorded honestly with a disposition instead of forced green.
- New review artifacts live in the git-ignored per-repo sidecar (`RepoMemory.for_target`), never in the reviewed repo's tracked tree.
- Doc claims about CLI behavior get a code-derived guard test in the same change.
- Per-commit governance: version bump plus CHANGELOG in the same commit as any shipping-file change, verified across 9 consecutive fix commits in Phase 1 alone.

### Key Lessons

1. Prove a subset/superset contract on non-empty data; a vacuous pass defers the real verification and costs a second phase.
2. Insert a decimal phase for a missed requirement instead of stretching an in-flight plan; 04.1 closed DIFF-04 in one plan without disturbing Phase 4.
3. Write the failing doc-guard test before correcting the docs; RED proof against stale text prevents the guard from being self-satisfying.

### Cost Observations

- Sessions: not tracked per-session this milestone
- Notable: plan durations ranged 14 minutes to ~2.5 hours; verification and UAT plans were the fastest, integration tracers the slowest.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v5.0 | 7 | 30 | First milestone with tracer plans, code-derived doc guards, and an inserted gap-closure phase |

### Top Lessons (Verified Across Milestones)

1. (Single milestone so far — lessons above await cross-validation.)
