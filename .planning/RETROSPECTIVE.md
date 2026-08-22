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

## Milestone: v5.1 — Tech-Debt Cleanup

**Shipped:** 2026-08-22
**Phases:** 2 | **Plans:** 0 (user-directed direct execution)

### What Was Built

- Phase 7 (PR #32): the CLI-forwarding test asserts `--workspace` reaches `run_review`; all three WR-01 guard tests prove exit 2 fires before any git call via a `subprocess.run` recording spy; the ruff `I001` in `test_cli.py` is fixed and a full-repo `ruff check` runs clean.
- Phase 8 (PR #33): the sec-overlay CLI legend is audited against `PHASE_TABLE`, the helpers pipeline diagram carries `selfscore`/`artifact-gate`/`artifact-review` nodes, the skill CLAUDE.md carries a numbered `14.2 Selfscore` entry (test-enforced), and the ingest WARNING is closed with the kb-redesign design doc affirmed as authority.

### What Worked

- Direct execution fit a cleanup milestone: seven small, pre-scoped requirements closed in one day across two PRs without plan/summary overhead.
- Test-first held even at small scale: the `Selfscore` doc invariant was proven red before the doc edit, and the WR-01 spy was proven to intercept git on a valid root before trusting its empty-list assertion.
- The ING-01 decision was settled by evidence, not judgment: the "missing" spec was found named in the design doc's own Out-of-scope section as upstream-internal.

### What Was Inefficient

- Skipping GSD plan/summary artifacts forced an override closeout: `milestone.complete` saw Phase 8 as unstarted and needed `--force`, and the MILESTONES.md entry had to be hand-written.
- CodeRabbit review was skipped on both PRs at the user's direction, so no independent review pass exists for this milestone.

### Patterns Established

1. Cleanup milestones may run phases as direct execution when each requirement carries its own mechanical verification (test, lint, validate); record the choice as a decision and expect an override closeout.
2. A "referenced doc missing" ingest warning can close by locating the reference *inside* the citing doc's scope boundaries before searching the tree.

### Key Lessons

1. Spy-based ordering proofs need a positive control: prove the spy fires on the good path before trusting an empty call list on the bad path.
2. When docs and a mechanical table (`PHASE_TABLE`) disagree, audit the docs against the table and extend the invariant test so the drift cannot recur.

### Cost Observations

- Sessions: 1
- Notable: entire milestone (context, execution, close) completed in a single session on 2026-08-22.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v5.0 | 7 | 30 | First milestone with tracer plans, code-derived doc guards, and an inserted gap-closure phase |
| v5.1 | 2 | 0 | First direct-execution milestone: no plans, verification by tests/lint/PRs, override closeout |

### Top Lessons (Verified Across Milestones)

1. Write the failing test before correcting docs (v5.0 doc guards; v5.1 `Selfscore` invariant) — RED proof keeps doc guards from being self-satisfying.
