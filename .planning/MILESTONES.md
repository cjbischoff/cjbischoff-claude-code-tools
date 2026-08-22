# Milestones

## v5.1 Tech-Debt Cleanup (Shipped: 2026-08-22)

**Phases completed:** 2 phases (7-8), direct execution — no formal plans
**Stats:** 19 files changed, +495/−186 lines, all on 2026-08-22
**Git range:** `398ed06` through `c0bda13` (PRs #32, #33)
**Closeout type:** override_closeout — phases ran as user-directed direct
execution, so no SUMMARY.md or VERIFICATION.md artifacts exist. All 7
requirements are closed and verified by tests, lint, and merged PRs.

**Key accomplishments:**

- TEST-01: the CLI-forwarding test asserts `--workspace` reaches `run_review`,
  not merely that the call occurs (Phase 7, PR #32).
- TEST-02: all three WR-01 guard tests prove exit 2 fires before any git call,
  via a recording spy over `subprocess.run` asserting an empty call list
  (Phase 7, PR #32).
- LINT-01: the pre-existing ruff `I001` in `test_cli.py` is fixed; a full-repo
  `ruff check` runs clean (Phase 7, PR #32).
- DOC-01/02/03: the sec-overlay CLI legend is audited against `PHASE_TABLE`,
  the helpers pipeline diagram carries `selfscore`/`artifact-gate`/
  `artifact-review` nodes, and the skill CLAUDE.md carries a numbered
  `14.2 Selfscore` entry — now enforced by `test_docs_invariants.py`
  (Phase 8, PR #33, sec-overlay 1.69.15).
- ING-01: the ingest WARNING is closed — the 2026-08-11 kb-redesign design doc
  is affirmed as authority; the 2026-08-09 reference is the upstream repo's
  internal spec, explicitly out of scope in the design doc itself (Phase 8).

---

## v5.0 Hybrid Diff-Review Architecture (Shipped: 2026-08-22)

**Phases completed:** 7 phases, 30 plans, 116 tasks
**Stats:** 212 files changed, +38,296/−294 lines, 2026-08-17 through 2026-08-22
**Git range:** `a4731cb` through `758fe51`
**Closeout type:** override_closeout — 6 acknowledged Phase 06 tech-debt items
**Known verification overrides:** 6 (see STATE.md Deferred Items)

**Key accomplishments:**

- Baseline health proven: 4 ruff errors and 161 `ty` diagnostics fixed with real receipts; the frozen JSON contract stayed untouched (Phase 1).
- `sec-overlay review` CLI verb shipped a full diff pipeline: diffscope, file selection, sealed coverage manifest, hunk positioning, and phase gate — stdlib-only (Phase 2).
- Per-language rule resolution shipped: 8 rule docs, four-layer per-path resolution with a hard-reject rule-file safety gate, `security` and `general` review profiles, and a retract-only LLM reflection filter (Phase 3).
- Scale and resume shipped: bounded concurrency and timeouts, resume identity verification (same model, profile, and SHAs), diff-anchored comments, and SARIF fingerprint contracts (Phase 4).
- DIFF-04 gap closed: review artifacts now route through the git-ignored per-repo sidecar instead of leaking at `--root` (Phase 4.1).
- End-to-end verification and governed release: both review profiles ran on a real diff, audit criteria AUD-04/AUD-05 proven, `redteam`/`postflight` wired into `PHASE_TABLE`, every defect dispositioned, and all PRs merged after CodeRabbit review (Phases 5-6).

---
